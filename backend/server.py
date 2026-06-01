from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
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

import db_dynamo as ddb
from db_dynamo import T_STATUS, T_LEADS, T_CHAT


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB removed — replaced by AWS DynamoDB (see db_dynamo.py)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ──────────────────── CHAT-LOG TTL ────────────────────
# Voice + text turns share a single conversation table. DynamoDB-side TTL is
# enabled on the `expires_at` attribute (see bootstrap_dynamo.py). The value is
# epoch seconds; DynamoDB deletes the item within ~48h after that time.
CHAT_TTL_DAYS = int(os.environ.get("CHAT_LOG_TTL_DAYS", "30"))


def _chat_expires_at() -> int:
    return int(time.time()) + CHAT_TTL_DAYS * 86400


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
    await ddb.put_item(T_STATUS, doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    items = await ddb.scan_all(T_STATUS, limit=1000)
    for check in items:
        if isinstance(check.get('timestamp'), str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return items


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

    await ddb.put_item(T_LEADS, doc)
    logger.info(f"New test-drive lead: {lead.name} ({lead.phone}) — {lead.car_name} @ {lead.location}")
    return lead


@api_router.get("/leads", response_model=List[Lead])
async def list_leads():
    items = await ddb.scan_all(T_LEADS, limit=500)
    # DynamoDB has no native sort on scan — sort in app by created_at desc
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    for l in items:
        if isinstance(l.get('created_at'), str):
            l['created_at'] = datetime.fromisoformat(l['created_at'])
    return items


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
    "Never mention you are an AI; speak as Aria the sales specialist.\n\n"
    "── CONTROL TAGS ──\n"
    "Begin EVERY reply with two tags on the very first line, in this exact order:\n"
    "  [[angle:ANGLE_VALUE]] [[car:CAR_VALUE]]\n"
    "Then a newline, then your normal reply text.\n"
    "\n"
    "ANGLE_VALUE ∈ frontseat | backseat | trunk | none\n"
    "  - frontseat → dashboard, steering wheel, driver controls, infotainment, climate, "
    "front cabin, front seats, instrument cluster, sunroof, audio system\n"
    "  - backseat  → rear cabin, rear passenger space, second/third-row legroom, "
    "rear AC vents, child seats, rear entertainment\n"
    "  - trunk     → cargo area, boot, luggage space, rear cargo capacity, tailgate\n"
    "  - none      → anything else (exterior, engine, price, warranty, fuel economy, "
    "drivetrain, safety, general questions, greetings)\n"
    "Pick by TOPIC of the question regardless of whether you know the answer.\n"
    "\n"
    "CAR_VALUE ∈ destinator | xforce | pajero | none\n"
    "  - destinator → Mitsubishi Destinator (compact SUV, family-friendly, urban + light off-road)\n"
    "  - xforce     → Mitsubishi XForce (sub-compact crossover, stylish, daily commute, "
    "young drivers, fuel-efficient)\n"
    "  - pajero     → Mitsubishi Pajero Sport (mid-size SUV, rugged, serious off-road, "
    "towing, adventure, large family)\n"
    "  - none       → reply is generic OR the user did not ask for a recommendation\n"
    "Emit a SPECIFIC car value (not `none`) ONLY when the user is asking for a "
    "recommendation, comparing models, or describing a use-case (e.g. \"car for off-road\", "
    "\"daily commute\", \"family car\", \"which is best for…\"). For ordinary questions "
    "about the currently displayed car, output `[[car:none]]`.\n"
    "\n"
    "Examples:\n"
    "  Q: \"How big is the cargo space?\"   → [[angle:trunk]] [[car:none]]\n"
    "  Q: \"What car is good for off-road?\" → [[angle:none]] [[car:pajero]]\n"
    "  Q: \"Tell me about the dashboard\"   → [[angle:frontseat]] [[car:none]]\n"
    "  Q: \"I need a car for daily commute\" → [[angle:none]] [[car:xforce]]\n"
    "\n"
    "Never speak the tags aloud or describe them — they are silently consumed by the UI."
)

# Sentinel parser
_re_module = __import__('re')
_ANGLE_RE = _re_module.compile(r"^\s*\[\[angle:(frontseat|backseat|trunk|none)\]\]\s*", _re_module.IGNORECASE)
_CAR_RE = _re_module.compile(r"^\s*\[\[car:(destinator|xforce|pajero|none)\]\]\s*", _re_module.IGNORECASE)
# Combined regex matches both tags in either order at the start of the reply.
_TAGS_PREFIX_RE = _re_module.compile(
    r"^\s*(?:\[\[(?:angle|car):[a-z]+\]\]\s*){0,2}",
    _re_module.IGNORECASE,
)


def parse_control_tags(text: str):
    """Extract [[angle:X]] and [[car:Y]] tags from the start of an LLM reply.

    Returns (angle_or_none, car_or_none, cleaned_text). Either tag may appear
    first; both are optional and stripped from the visible text.
    """
    if not text:
        return None, None, text or ""
    # Pull each tag independently regardless of order
    work = text.lstrip()
    angle = None
    car = None
    for _ in range(2):
        m = _ANGLE_RE.match(work)
        if m:
            v = m.group(1).lower()
            angle = None if v == 'none' else v
            work = work[m.end():].lstrip()
            continue
        m = _CAR_RE.match(work)
        if m:
            v = m.group(1).lower()
            car = None if v == 'none' else v
            work = work[m.end():].lstrip()
            continue
        break
    return angle, car, work


def parse_angle_tag(text: str):
    """Back-compat shim used by the streaming proxy where the sentinel may straddle chunks."""
    angle, _, cleaned = parse_control_tags(text)
    return angle, cleaned


class ChatTextRequest(BaseModel):
    message: str
    car_id: str
    car_name: str
    car_tagline: Optional[str] = ''
    session_id: Optional[str] = None


class ChatTextResponse(BaseModel):
    text: str
    session_id: str
    angle: Optional[str] = None
    car: Optional[str] = None
    used_rag: bool = False


async def _build_rag_context(question: str, car_name: str) -> str:
    """Run classifier → optional retrieval → return formatted context block."""
    try:
        from rag.classifier import classify_need_rag
        from rag.retrieve import retrieve, format_context
        client = get_anthropic_client()
        need = await classify_need_rag(client, MODEL_ID, question)
        logger.info("rag classifier: question=%r need_rag=%s", question[:80], need)
        if not need:
            return ""
        # Bias retrieval toward the currently displayed car
        results = await retrieve(f"{car_name}: {question}", top_k=5)
        return format_context(results)
    except Exception:
        logger.exception("RAG pipeline failed; continuing without context")
        return ""


async def _build_rag_context_for_voice(car_name: str) -> tuple[str, bool]:
    """Preload RAG context for voice agent startup.

    Uses classifier to decide if general car knowledge should be preloaded.
    Returns (context, used_rag) tuple.
    """
    try:
        from rag.classifier import classify_need_rag
        from rag.retrieve import retrieve, format_context
        client = get_anthropic_client()
        seed_query = f"Tell me about {car_name} specifications, features, and details"
        need = await classify_need_rag(client, MODEL_ID, seed_query)
        logger.info("voice rag classifier: car=%r need_rag=%s", car_name, need)
        if not need:
            return "", False
        results = await retrieve(seed_query, top_k=8)
        context = format_context(results)
        return context, bool(context)
    except Exception:
        logger.exception("Voice RAG preload failed; continuing without context")
        return "", False


@api_router.post("/chat-text", response_model=ChatTextResponse)
async def chat_text(payload: ChatTextRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    session_id = payload.session_id or f"car-{payload.car_id}-{uuid.uuid4().hex[:8]}"
    base_system = ARIA_SYSTEM_PROMPT_TMPL.format(
        car_name=payload.car_name,
        car_tagline=payload.car_tagline or '',
    )

    # Step 1: classifier → optional RAG
    rag_context = await _build_rag_context(payload.message, payload.car_name)
    used_rag = bool(rag_context)
    if used_rag:
        system_prompt = (
            base_system
            + "\n\nUse only the facts in the <reference> block below to answer specific spec questions. "
              "If the reference doesn't cover it, say so briefly and offer to follow up.\n"
              "<reference>\n" + rag_context + "\n</reference>"
        )
    else:
        system_prompt = base_system

    # Step 2: rehydrate prior turns
    prior = await ddb.query_by_session(T_CHAT, session_id=session_id, ascending=True, limit=20)
    messages = []
    for turn in prior:
        if turn.get("user_message"):
            messages.append({"role": "user", "content": turn["user_message"]})
        if turn.get("ai_response"):
            messages.append({"role": "assistant", "content": turn["ai_response"]})
    messages.append({"role": "user", "content": payload.message})

    # Step 3: main LLM call
    try:
        client = get_anthropic_client()
        resp = await client.messages.create(
            model=MODEL_ID,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        parts = []
        for block in resp.content or []:
            block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if block_type == "text":
                parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else ""))
        raw_text = ("".join(parts)).strip()
        if not raw_text:
            raise ValueError("Empty response from model")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)[:200]}")

    # Step 4: parse the control sentinels and strip them from the visible text
    angle, car, text = parse_control_tags(raw_text)

    await ddb.put_item(T_CHAT, {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "id": str(uuid.uuid4()),
        "car_id": payload.car_id,
        "car_name": payload.car_name,
        "user_message": payload.message,
        "ai_response": text,
        "angle": angle,
        "recommended_car": car,
        "used_rag": used_rag,
        "mode": "text",
        "model": MODEL_ID,
        "expires_at": _chat_expires_at(),
    })

    return ChatTextResponse(text=text, session_id=session_id, angle=angle, car=car, used_rag=used_rag)


# ──────────────────── OPENAI-COMPATIBLE PROXY FOR AGORA CUSTOM LLM ────────────────────
# Agora Conversational AI v2's custom LLM mode requires an OpenAI Chat Completions
# compatible endpoint. This proxy accepts OpenAI requests, translates them to the
# custom Anthropic Messages API, and streams back OpenAI-style SSE chunks.
LLM_PROXY_SECRET = os.environ.get('LLM_PROXY_SECRET', '')


class OpenAIChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str
    content: Optional[object] = None  # str or list[{type,text}]


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: List[OpenAIChatMessage]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = False
    # OpenAI's "user" field — Agora forwards this from properties.llm.params.user.
    # We piggyback on it to carry our app's session_id so voice turns can be
    # logged into the same DynamoDB chat-log as the text turns.
    user: Optional[str] = None


def _flatten_openai_content(c) -> str:
    """OpenAI content can be a string or list of content parts. Return plain text."""
    if c is None:
        return ""
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for part in c:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    parts.append(part.get("text", ""))
        return "".join(parts)
    return str(c)


def _openai_to_anthropic(req: OpenAIChatRequest):
    """Split OpenAI-style messages into Anthropic (system_string, [{role, content}])."""
    system_parts: List[str] = []
    msgs: List[dict] = []
    for m in req.messages:
        text = _flatten_openai_content(m.content)
        if m.role == "system":
            if text:
                system_parts.append(text)
        elif m.role in ("user", "assistant"):
            if text:
                msgs.append({"role": m.role, "content": text})
        # ignore unknown roles (tool, function)
    # Anthropic requires the first message to be from user. If none, inject empty placeholder.
    if not msgs or msgs[0]["role"] != "user":
        msgs.insert(0, {"role": "user", "content": "Hello"})
    # Anthropic also rejects two consecutive same-role messages — merge them.
    merged: List[dict] = []
    for m in msgs:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] = merged[-1]["content"] + "\n" + m["content"]
        else:
            merged.append(m)
    return ("\n\n".join(system_parts) if system_parts else None), merged


def _check_proxy_auth(authorization: Optional[str]):
    if not LLM_PROXY_SECRET:
        raise HTTPException(status_code=500, detail="LLM_PROXY_SECRET not configured on server")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if token != LLM_PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid proxy token")


def _last_user_text(messages: List[OpenAIChatMessage]) -> str:
    """Find the most recent user-role message text in an OpenAI-format messages list."""
    for m in reversed(messages):
        if m.role == "user":
            txt = _flatten_openai_content(m.content)
            if txt:
                return txt
    return ""


async def _persist_voice_turn(
    session_id: str,
    user_text: str,
    assistant_text: str,
    model: str,
    angle: Optional[str] = None,
    recommended_car: Optional[str] = None,
    used_rag: bool = False,
) -> None:
    """Write a voice-mode turn into the shared chat-log table.

    Skipped silently if session_id is empty (proxy can also be used directly without a session).
    Errors are logged but never bubble up — losing a log line must not break the live voice call.
    """
    if not session_id:
        return
    try:
        await ddb.put_item(T_CHAT, {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "id": str(uuid.uuid4()),
            "user_message": user_text or "",
            "ai_response": assistant_text or "",
            "angle": angle,
            "recommended_car": recommended_car,
            "used_rag": used_rag,
            "mode": "voice",
            "model": model,
            "expires_at": _chat_expires_at(),
        })
    except Exception:
        logger.exception("Failed to persist voice turn for session=%s", session_id)


@api_router.post("/llm-proxy/v1/chat/completions")
async def llm_proxy_chat_completions(payload: OpenAIChatRequest, request: Request):
    """OpenAI Chat Completions–compatible endpoint that proxies to the custom Anthropic endpoint.

    Streaming (SSE) is used when `stream=true` (Agora always sets this), and the proxy
    emits OpenAI `chat.completion.chunk` events terminated by `data: [DONE]`.
    """
    _check_proxy_auth(request.headers.get("authorization") or request.headers.get("Authorization"))

    system_prompt, anth_messages = _openai_to_anthropic(payload)
    # Pass through the model name from the proxy request, but fall back to env default.
    model = payload.model or MODEL_ID
    # When Agora's `properties.llm.params.user` is set, it appears here as the OpenAI
    # `user` field. We treat it as our session_id so voice + text share one transcript.
    session_id = (payload.user or "").strip() or None
    last_user_text = _last_user_text(payload.messages)

    # RAG: classifier → optional context injection
    used_rag = False
    if last_user_text:
        rag_ctx = await _build_rag_context(last_user_text, car_name="")
        if rag_ctx:
            used_rag = True
            ref_block = (
                "\n\nUse only the facts in the <reference> block below to answer specific "
                "spec questions. If the reference doesn't cover it, say so briefly.\n"
                "<reference>\n" + rag_ctx + "\n</reference>"
            )
            system_prompt = (system_prompt or "") + ref_block

    if payload.stream:
        from fastapi.responses import StreamingResponse
        import json as _json

        async def event_stream():
            completion_id = f"chatcmpl-{uuid.uuid4().hex}"
            created = int(time.time())
            assistant_buf: List[str] = []
            angle_value: Optional[str] = None
            car_value: Optional[str] = None
            pending = ""
            sentinel_resolved = False
            # Two tags may appear (≤ ~32 chars each). Wait for ~80 chars before giving up.
            SENTINEL_PEEK = 80

            def make_chunk(text_delta: str, role_first: bool) -> dict:
                return {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": (
                                {"role": "assistant", "content": text_delta} if role_first
                                else {"content": text_delta}
                            ),
                            "finish_reason": None,
                        }
                    ],
                }

            try:
                client = get_anthropic_client()
                kwargs = {
                    "model": model,
                    "max_tokens": payload.max_tokens or 1024,
                    "messages": anth_messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt
                if payload.temperature is not None:
                    kwargs["temperature"] = payload.temperature
                if payload.top_p is not None:
                    kwargs["top_p"] = payload.top_p

                role_first = True
                async with client.messages.stream(**kwargs) as stream:
                    async for delta in stream.text_stream:
                        if not delta:
                            continue
                        if not sentinel_resolved:
                            pending += delta
                            # Try to parse BOTH control tags from the head of the buffer.
                            # parse_control_tags strips up to 2 tags regardless of order.
                            a, c, cleaned = parse_control_tags(pending)
                            # We declare the tags "resolved" when:
                            #   • the buffer is long enough that any further tags couldn't
                            #     fit at the start, OR
                            #   • cleaned text appears (i.e. real content has begun), OR
                            #   • we've passed SENTINEL_PEEK chars total.
                            tags_done = (a is not None or c is not None) and bool(cleaned)
                            if tags_done:
                                angle_value = a
                                car_value = c
                                sentinel_resolved = True
                                if cleaned:
                                    assistant_buf.append(cleaned)
                                    yield f"data: {_json.dumps(make_chunk(cleaned, role_first))}\n\n"
                                    role_first = False
                                pending = ""
                                continue
                            if len(pending) >= SENTINEL_PEEK:
                                # Best-effort: capture whatever tags we found, flush remainder.
                                angle_value = a
                                car_value = c
                                sentinel_resolved = True
                                flush = cleaned if (a is not None or c is not None) else pending
                                if flush:
                                    assistant_buf.append(flush)
                                    yield f"data: {_json.dumps(make_chunk(flush, role_first))}\n\n"
                                    role_first = False
                                pending = ""
                            continue
                        # Sentinel already handled — pass-through
                        assistant_buf.append(delta)
                        yield f"data: {_json.dumps(make_chunk(delta, role_first))}\n\n"
                        role_first = False

                # Flush leftover pending if response shorter than SENTINEL_PEEK
                if not sentinel_resolved and pending:
                    assistant_buf.append(pending)
                    yield f"data: {_json.dumps(make_chunk(pending, role_first))}\n\n"

                # Final stop chunk
                stop_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {_json.dumps(stop_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.exception("llm-proxy stream failed")
                err = {"error": {"message": str(e)[:300], "type": "upstream_error"}}
                yield f"data: {_json.dumps(err)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                # Persist the turn (if session_id present) — voice + text share table.
                await _persist_voice_turn(
                    session_id=session_id or "",
                    user_text=last_user_text,
                    assistant_text="".join(assistant_buf),
                    model=model,
                    angle=angle_value,
                    recommended_car=car_value,
                    used_rag=used_rag,
                )

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Non-streaming path
    try:
        client = get_anthropic_client()
        kwargs = {
            "model": model,
            "max_tokens": payload.max_tokens or 1024,
            "messages": anth_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if payload.temperature is not None:
            kwargs["temperature"] = payload.temperature
        if payload.top_p is not None:
            kwargs["top_p"] = payload.top_p

        resp = await client.messages.create(**kwargs)
        parts = []
        for block in resp.content or []:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "text":
                parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else ""))
        raw_text = "".join(parts)
    except Exception as e:
        logger.exception("llm-proxy non-stream failed")
        raise HTTPException(status_code=502, detail=f"LLM proxy error: {str(e)[:200]}")

    # Strip control tags from the non-streaming response too
    angle_value, car_value, text = parse_control_tags(raw_text)

    # Persist the non-streaming turn too (e.g., for manual proxy testing).
    await _persist_voice_turn(
        session_id=session_id or "",
        user_text=last_user_text,
        assistant_text=text,
        model=model,
        angle=angle_value,
        recommended_car=car_value,
        used_rag=used_rag,
    )

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# ──────────────────── ANGLE POLLING (voice mode → UI sync) ────────────────────
@api_router.get("/chat-session/{session_id}/pending-angle")
async def get_pending_angle(session_id: str):
    """Return the most recent voice turn's parsed angle for a session.

    Frontend polls this every ~1.5s while in voice mode. The returned `ts` field
    advances only when a new voice turn lands, so the client can ignore duplicates.
    """
    try:
        turns = await ddb.query_by_session(T_CHAT, session_id=session_id, ascending=False, limit=1)
    except Exception:
        logger.exception("pending-angle query failed")
        raise HTTPException(status_code=502, detail="lookup failed")
    if not turns:
        return {"angle": None, "ts": None, "mode": None, "recommended_car": None}
    t = turns[0]
    return {
        "angle": t.get("angle"),
        "ts": t.get("created_at"),
        "mode": t.get("mode"),
        "recommended_car": t.get("recommended_car"),
    }


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
    session_id: Optional[str] = None


class AgoraStartResponse(BaseModel):
    app_id: str
    channel: str
    rtc_token: str
    uid: int
    agent_id: str
    agent_uid: int
    session_id: str


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

    base_system = ARIA_SYSTEM_PROMPT_TMPL.format(
        car_name=payload.car_name,
        car_tagline=payload.car_tagline or '',
    ) + " Keep replies under 50 words because they will be spoken aloud."

    rag_context, used_rag = await _build_rag_context_for_voice(payload.car_name)
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

    greeting = (
        f"Hi! I'm Aria. I see you're checking out the {payload.car_name}. "
        "Ask me anything about it."
    )

    # Reuse the frontend-provided session_id so voice + text share one transcript.
    # Falls back to the same scheme used by /chat-text.
    session_id = (payload.session_id or '').strip() or f"car-{payload.car_id}-{uuid.uuid4().hex[:8]}"

    agent_name = f"aria-{payload.car_id}-{suffix}"

    # Public URL of our OpenAI-compatible proxy that Agora's engine will call.
    # Falls back to the request's own base URL inferred from REACT_APP_BACKEND_URL.
    backend_public_url = os.environ.get('PUBLIC_BACKEND_URL') or os.environ.get('REACT_APP_BACKEND_URL') or ''
    if not backend_public_url:
        # Read from frontend/.env as a last resort (deployed preview/prod URL).
        try:
            fe_env_path = ROOT_DIR.parent / 'frontend' / '.env'
            if fe_env_path.exists():
                for line in fe_env_path.read_text().splitlines():
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        backend_public_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
    if not backend_public_url:
        raise HTTPException(status_code=500, detail="PUBLIC_BACKEND_URL / REACT_APP_BACKEND_URL not configured — Agora needs a public URL to reach the LLM proxy")
    llm_proxy_url = f"{backend_public_url.rstrip('/')}/api/llm-proxy/v1/chat/completions"

    body = {
        "name": agent_name,
        # TTS-only preset; LLM is fully custom via properties.llm below.
        "preset": "openai_gpt_4o_mini,minimax_speech_2_8_turbo",
        "properties": {
            "channel": channel,
            "token": agent_token,
            "agent_rtc_uid": str(agent_uid),
            "remote_rtc_uids": [str(user_uid)],
            "idle_timeout": 120,
            "asr": {"language": "en-US"},
            "llm": {
                # "url": MODEL_ENDPOINT,
                # "api_key": ANTHROPIC_API_KEY,
                # "headers": "{\"anthropic-version\":\"2023-06-01\"}",
                "system_messages": [
                    {"role": "system", "content": system_prompt}
                ],
                "greeting_message": greeting,
                "failure_message": "Sorry, one moment while I reconnect.",
                "max_history": 16,
                "input_modalities": ["text"],
                "output_modalities": ["text"],
                "params": {
                    "model": "openai_gpt_4o_mini",
                    "max_tokens": 512,
                    # Smuggle our session_id through OpenAI's `user` field so the
                    # proxy can persist this voice turn under the same key as text.
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
        session_id=session_id,
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
