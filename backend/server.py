from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import base64
import time
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import httpx
from anthropic import AsyncAnthropic
from agora_token_builder import RtcTokenBuilder


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


# ──────────────────── TEST DRIVE LEADS ────────────────────
class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    car_id: str
    car_name: str
    preferred_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LeadCreate(BaseModel):
    name: str
    phone: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    car_id: str
    car_name: str
    preferred_date: Optional[str] = None
    notes: Optional[str] = None


@api_router.post("/leads", response_model=Lead)
async def create_lead(payload: LeadCreate):
    if not payload.name.strip() or not payload.phone.strip() or not payload.location.strip():
        raise HTTPException(status_code=400, detail="name, phone and location are required")

    lead = Lead(**payload.model_dump())
    doc = lead.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.leads.insert_one(doc)
    logger.info(f"New test-drive lead: {lead.name} ({lead.phone}) — {lead.car_name} @ {lead.location}")
    return lead


@api_router.get("/leads", response_model=List[Lead])
async def list_leads():
    leads = await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for l in leads:
        if isinstance(l.get('created_at'), str):
            l['created_at'] = datetime.fromisoformat(l['created_at'])
    return leads


# ──────────────────── ARIA — TEXT CHAT (Custom Anthropic Endpoint) ────────────────────
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')  # legacy, kept for compatibility
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
MODEL_ENDPOINT = os.environ.get('MODEL_ENDPOINT')
MODEL_ID = os.environ.get('MODEL_ID', 'claude-sonnet-4.6')

# Lazy-initialized Anthropic client targeting the custom endpoint
_anthropic_client: Optional[AsyncAnthropic] = None


def get_anthropic_client() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
        kwargs = {"api_key": ANTHROPIC_API_KEY}
        if MODEL_ENDPOINT:
            kwargs["base_url"] = MODEL_ENDPOINT
        _anthropic_client = AsyncAnthropic(**kwargs)
    return _anthropic_client

ARIA_SYSTEM_PROMPT_TMPL = (
    "You are Aria, a friendly and knowledgeable luxury car sales specialist. "
    "The customer is currently viewing the {car_name} ({car_tagline}). "
    "Answer their question in 2-3 short sentences with a warm, conversational tone. "
    "Be specific about the car when relevant, and gently encourage interest without being pushy. "
    "Never mention you are an AI; speak as Aria the sales specialist."
)


class ChatTextRequest(BaseModel):
    message: str
    car_id: str
    car_name: str
    car_tagline: Optional[str] = ''
    session_id: Optional[str] = None


class ChatTextResponse(BaseModel):
    text: str
    session_id: str


@api_router.post("/chat-text", response_model=ChatTextResponse)
async def chat_text(payload: ChatTextRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    session_id = payload.session_id or f"car-{payload.car_id}-{uuid.uuid4().hex[:8]}"
    system_prompt = ARIA_SYSTEM_PROMPT_TMPL.format(
        car_name=payload.car_name,
        car_tagline=payload.car_tagline or '',
    )

    # Load prior turns for this session to maintain conversational memory
    prior = await db.chat_messages.find(
        {"session_id": session_id, "mode": "text"},
        {"_id": 0, "user_message": 1, "ai_response": 1, "created_at": 1},
    ).sort("created_at", 1).to_list(20)

    messages = []
    for turn in prior:
        if turn.get("user_message"):
            messages.append({"role": "user", "content": turn["user_message"]})
        if turn.get("ai_response"):
            messages.append({"role": "assistant", "content": turn["ai_response"]})
    messages.append({"role": "user", "content": payload.message})

    try:
        client = get_anthropic_client()
        resp = await client.messages.create(
            model=MODEL_ID,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        # Concatenate text blocks from the response
        parts = []
        for block in resp.content or []:
            block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if block_type == "text":
                parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else ""))
        text = ("".join(parts)).strip()
        if not text:
            raise ValueError("Empty response from model")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)[:200]}")

    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "car_id": payload.car_id,
        "car_name": payload.car_name,
        "user_message": payload.message,
        "ai_response": text,
        "mode": "text",
        "model": MODEL_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return ChatTextResponse(text=text, session_id=session_id)


# ──────────────────── ARIA — VOICE CHAT (Agora Conversational AI) ────────────────────
AGORA_APP_ID = os.environ.get('AGORA_APP_ID')
AGORA_APP_CERTIFICATE = os.environ.get('AGORA_APP_CERTIFICATE')
AGORA_CUSTOMER_ID = os.environ.get('AGORA_CUSTOMER_ID')
AGORA_CUSTOMER_SECRET = os.environ.get('AGORA_CUSTOMER_SECRET')
AGORA_API_BASE = "https://api.agora.io/api/conversational-ai-agent/v2/projects"

# RTC token role / privilege constants
ROLE_PUBLISHER = 1
TOKEN_EXPIRE_SECONDS = 60 * 60  # 1 hour


def _agora_basic_auth_header() -> str:
    raw = f"{AGORA_CUSTOMER_ID}:{AGORA_CUSTOMER_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("utf-8")


def _build_rtc_token(channel: str, uid: int, expire_seconds: int = TOKEN_EXPIRE_SECONDS) -> str:
    expire_ts = int(time.time()) + expire_seconds
    return RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID, AGORA_APP_CERTIFICATE, channel, uid, ROLE_PUBLISHER, expire_ts
    )


class AgoraStartRequest(BaseModel):
    car_id: str
    car_name: str
    car_tagline: Optional[str] = ''


class AgoraStartResponse(BaseModel):
    app_id: str
    channel: str
    rtc_token: str
    uid: int
    agent_id: str
    agent_uid: int


class AgoraStopRequest(BaseModel):
    agent_id: str


@api_router.post("/agora/start", response_model=AgoraStartResponse)
async def agora_start(payload: AgoraStartRequest):
    if not (AGORA_APP_ID and AGORA_APP_CERTIFICATE and AGORA_CUSTOMER_ID and AGORA_CUSTOMER_SECRET):
        raise HTTPException(status_code=500, detail="Agora credentials not configured")

    # Build unique channel + uids
    suffix = uuid.uuid4().hex[:8]
    channel = f"aria-{payload.car_id}-{suffix}"
    user_uid = int.from_bytes(uuid.uuid4().bytes[:3], "big") + 1000  # 24-bit safe random
    agent_uid = user_uid + 1

    # Tokens
    user_token = _build_rtc_token(channel, user_uid)
    agent_token = _build_rtc_token(channel, agent_uid)

    system_prompt = ARIA_SYSTEM_PROMPT_TMPL.format(
        car_name=payload.car_name,
        car_tagline=payload.car_tagline or '',
    ) + " Keep replies under 50 words because they will be spoken aloud."

    greeting = (
        f"Hi! I'm Aria. I see you're checking out the {payload.car_name}. "
        "Ask me anything about it."
    )

    agent_name = f"aria-{payload.car_id}-{suffix}"

    body = {
        "name": agent_name,
        "preset": "openai_gpt_4_1_mini,minimax_speech_2_8_turbo",
        "properties": {
            "channel": channel,
            "token": agent_token,
            "agent_rtc_uid": str(agent_uid),
            "remote_rtc_uids": [str(user_uid)],
            "idle_timeout": 120,
            "asr": {"language": "en-US"},
            "llm": {
                "system_messages": [
                    {"role": "system", "content": system_prompt}
                ],
                "greeting_message": greeting,
                "failure_message": "Sorry, one moment while I reconnect.",
                "max_history": 16,
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

    url = f"{AGORA_API_BASE}/{AGORA_APP_ID}/join"
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
        app_id=AGORA_APP_ID,
        channel=channel,
        rtc_token=user_token,
        uid=user_uid,
        agent_id=agent_id,
        agent_uid=agent_uid,
    )


@api_router.post("/agora/stop")
async def agora_stop(payload: AgoraStopRequest):
    if not payload.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    url = f"{AGORA_API_BASE}/{AGORA_APP_ID}/agents/{payload.agent_id}/leave"
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
        # Still return success so frontend can clean up; agent will idle-timeout anyway.
        return {"ok": False, "status": resp.status_code, "detail": resp.text[:240]}

    return {"ok": True}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
