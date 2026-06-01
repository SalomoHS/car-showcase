from fastapi import APIRouter, Depends, HTTPException
import uuid
import time
import base64
import os
from pathlib import Path
import httpx

from models.domain import AgoraStartRequest, AgoraStartResponse, AgoraStopRequest
from api.deps import get_llm_service, LLMService
from core.config import settings
from core.logger import logger
from agora_token_builder import RtcTokenBuilder
from services.llm import ARIA_SYSTEM_PROMPT_TMPL

router = APIRouter()

ROLE_PUBLISHER = 1
TOKEN_EXPIRE_SECONDS = 60 * 60

AGORA_API_BASE = "https://api.agora.io/api/conversational-ai-agent/v2/projects"

def _agora_basic_auth_header() -> str:
    raw = f"{settings.AGORA_CUSTOMER_ID}:{settings.AGORA_CUSTOMER_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("utf-8")

def _build_rtc_token(channel: str, uid: int, expire_seconds: int = TOKEN_EXPIRE_SECONDS) -> str:
    expire_ts = int(time.time()) + expire_seconds
    return RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID, settings.AGORA_APP_CERTIFICATE, channel, uid, ROLE_PUBLISHER, expire_ts
    )

@router.post("/start", response_model=AgoraStartResponse)
async def agora_start(
    payload: AgoraStartRequest,
    llm: LLMService = Depends(get_llm_service)
):
    if not (settings.AGORA_APP_ID and settings.AGORA_APP_CERTIFICATE and settings.AGORA_CUSTOMER_ID and settings.AGORA_CUSTOMER_SECRET):
        raise HTTPException(status_code=500, detail="Agora credentials not configured")

    suffix = uuid.uuid4().hex[:8]
    channel = f"aria-{payload.car_id}-{suffix}"
    user_uid = int.from_bytes(uuid.uuid4().bytes[:3], "big") + 1000
    agent_uid = user_uid + 1

    user_token = _build_rtc_token(channel, user_uid)
    agent_token = _build_rtc_token(channel, agent_uid)

    base_system = ARIA_SYSTEM_PROMPT_TMPL.format(
        car_name=payload.car_name,
        car_tagline=payload.car_tagline or '',
    ) + " Keep replies under 50 words because they will be spoken aloud."

    rag_context, used_rag = await llm.build_rag_context_for_voice(payload.car_name)
    if used_rag and rag_context:
        system_prompt = (
            base_system
            + "\n\nUse only the facts in the <reference> block below to answer specific spec questions. "
              "If the reference doesn't cover it, say so briefly and offer to follow up.\n"
              "<reference>\n" + rag_context + "\n</reference>"
        )
        logger.info("agora start: RAG enabled for car=%r", payload.car_name)
    else:
        system_prompt = base_system
        logger.info("agora start: RAG not needed for car=%r", payload.car_name)

    greeting = f"Hi! I'm Aria. I see you're checking out the {payload.car_name}. Ask me anything about it."
    session_id = (payload.session_id or '').strip() or f"car-{payload.car_id}-{uuid.uuid4().hex[:8]}"
    agent_name = f"aria-{payload.car_id}-{suffix}"

    backend_public_url = settings.PUBLIC_BACKEND_URL or settings.REACT_APP_BACKEND_URL or ''
    if not backend_public_url:
        try:
            ROOT_DIR = Path(__file__).parent.parent.parent.parent
            fe_env_path = ROOT_DIR.parent / 'frontend' / '.env'
            if fe_env_path.exists():
                for line in fe_env_path.read_text().splitlines():
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        backend_public_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
    if not backend_public_url:
        raise HTTPException(status_code=500, detail="PUBLIC_BACKEND_URL / REACT_APP_BACKEND_URL not configured")
    
    llm_proxy_url = f"{backend_public_url.rstrip('/')}/api/llm-proxy/v1/chat/completions"

    body = {
        "name": agent_name,
        "preset": "openai_gpt_4o_mini,minimax_speech_2_8_turbo",
        "properties": {
            "channel": channel,
            "token": agent_token,
            "agent_rtc_uid": str(agent_uid),
            "remote_rtc_uids": [str(user_uid)],
            "idle_timeout": 120,
            "asr": {"language": "en-US"},
            "llm": {
                "url": llm_proxy_url,
                "api_key": settings.LLM_PROXY_SECRET,
                "system_messages": [{"role": "system", "content": system_prompt}],
                "greeting_message": greeting,
                "failure_message": "Sorry, one moment while I reconnect.",
                "max_history": 16,
                "input_modalities": ["text"],
                "output_modalities": ["text"],
                "params": {
                    "model": settings.MODEL_ID,
                    "max_tokens": 512,
                    "user": session_id,
                },
            },
            "tts": {
                "params": {
                    "voice_setting": {
                        "voice_id": "English_captivating_female1"
                    }
                }
            },
        },
    }

    url = f"{AGORA_API_BASE}/{settings.AGORA_APP_ID}/join"
    headers = {
        "Authorization": _agora_basic_auth_header(),
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as hc:
            resp = await hc.post(url, json=body, headers=headers)
    except httpx.HTTPError as e:
        logger.exception("Agora request error")
        raise HTTPException(status_code=502, detail=f"Agora request error: {e}")

    if resp.status_code >= 400:
        logger.error(f"Agora join failed: {resp.status_code} {resp.text}")
        raise HTTPException(
            status_code=502,
            detail=f"Agora join failed ({resp.status_code}): {resp.text[:240]}",
        )

    data = resp.json()
    agent_id = data.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=502, detail=f"Agora returned no agent_id: {data}")

    return AgoraStartResponse(
        app_id=settings.AGORA_APP_ID,
        channel=channel,
        rtc_token=user_token,
        uid=user_uid,
        agent_id=agent_id,
        agent_uid=agent_uid,
        session_id=session_id,
    )

@router.post("/stop")
async def agora_stop(payload: AgoraStopRequest):
    if not payload.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    url = f"{AGORA_API_BASE}/{settings.AGORA_APP_ID}/agents/{payload.agent_id}/leave"
    headers = {
        "Authorization": _agora_basic_auth_header(),
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as hc:
            resp = await hc.post(url, headers=headers)
    except httpx.HTTPError as e:
        logger.exception("Agora stop request error")
        raise HTTPException(status_code=502, detail=f"Agora stop error: {e}")

    if resp.status_code >= 400:
        logger.warning(f"Agora stop returned {resp.status_code}: {resp.text}")
        return {"ok": False, "status": resp.status_code, "detail": resp.text[:240]}

    return {"ok": True}
