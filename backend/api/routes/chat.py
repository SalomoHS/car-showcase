from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import time
import json as _json

from models.domain import ChatTextRequest, ChatTextResponse, OpenAIChatRequest, OpenAIChatMessage
from api.deps import get_db_service, get_llm_service, DynamoDBService, LLMService
from core.config import settings
from core.logger import logger, get_langfuse_client

router = APIRouter()

def _chat_expires_at() -> int:
    return int(time.time()) + settings.CHAT_LOG_TTL_DAYS * 86400

@router.post("/chat-text", response_model=ChatTextResponse)
async def chat_text(
    payload: ChatTextRequest,
    db: DynamoDBService = Depends(get_db_service),
    llm: LLMService = Depends(get_llm_service)
):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    session_id = payload.session_id or str(uuid.uuid4())
    from core.logger import session_id_var
    session_id_var.set(session_id)
    logger.info(f"chat_text: started processing request for session {session_id}")
    from services.llm import ARIA_SYSTEM_PROMPT_TMPL
    base_system = ARIA_SYSTEM_PROMPT_TMPL.format(
        car_name=payload.car_name,
        car_tagline=payload.car_tagline or '',
    )

    langfuse = get_langfuse_client()
    trace = None
    generation = None
    
    from langfuse import propagate_attributes

    async def process_chat():
        nonlocal trace, generation
        
        rag_context = await llm.build_rag_context(payload.message, payload.car_name)
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

        prior = await db.query_by_session(settings.T_CHAT, session_id=session_id, ascending=True, limit=20)
        messages = []
        for turn in prior:
            if turn.get("user_message"):
                messages.append({"role": "user", "content": turn["user_message"]})
            if turn.get("ai_response"):
                messages.append({"role": "assistant", "content": turn["ai_response"]})
        messages.append({"role": "user", "content": payload.message})

        from contextlib import ExitStack
        try:
            client = llm.get_client()
            with ExitStack() as stack:
                if langfuse:
                    generation = stack.enter_context(langfuse.start_as_current_observation(
                        name="anthropic-chat",
                        as_type="generation",
                        model=settings.MODEL_ID,
                        input=messages,
                        metadata={
                            "system_prompt_preview": system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt,
                            "used_rag": used_rag,
                            "message_count": len(messages),
                        },
                    ))
                
                resp = await client.messages.create(
                    model=settings.MODEL_ID,
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
                
                if langfuse and generation:
                    usage_dict = None
                    if hasattr(resp, "usage") and resp.usage:
                        usage_dict = {
                            "input": getattr(resp.usage, "input_tokens", 0),
                            "output": getattr(resp.usage, "output_tokens", 0),
                            "total": getattr(resp.usage, "input_tokens", 0) + getattr(resp.usage, "output_tokens", 0),
                        }
                    generation.update(output=raw_text, usage_details=usage_dict)
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("LLM call failed")
            raise HTTPException(status_code=502, detail=f"LLM error: {str(e)[:200]}")

        angle, car, text = llm.parse_control_tags(raw_text)

        await db.put_item(settings.T_CHAT, {
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
            "model": settings.MODEL_ID,
            "expires_at": _chat_expires_at(),
        })
        
        if trace:
            trace.update(
                output={"text": text, "angle": angle, "recommended_car": car},
                metadata={
                    "car_id": payload.car_id,
                    "car_name": payload.car_name,
                    "mode": "text",
                    "angle": angle,
                    "recommended_car": car,
                    "used_rag": used_rag,
                },
            )

        return ChatTextResponse(text=text, session_id=session_id, angle=angle, car=car, used_rag=used_rag)

    if langfuse:
        with propagate_attributes(session_id=session_id, user_id=f"car-{payload.car_id}"):
            with langfuse.start_as_current_observation(
                name="chat-text",
                as_type="span",
                input={"message": payload.message},
                metadata={"car_id": payload.car_id, "car_name": payload.car_name, "mode": "text"}
            ) as root_span:
                trace = root_span
                response = await process_chat()
                langfuse.flush()
                return response
    else:
        return await process_chat()

def _flatten_openai_content(c) -> str:
    if c is None: return ""
    if isinstance(c, str): return c
    if isinstance(c, list):
        parts = []
        for part in c:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "".join(parts)
    return str(c)

def _openai_to_anthropic(req: OpenAIChatRequest):
    system_parts: List[str] = []
    msgs: List[dict] = []
    for m in req.messages:
        text = _flatten_openai_content(m.content)
        if m.role == "system":
            if text: system_parts.append(text)
        elif m.role in ("user", "assistant"):
            if text: msgs.append({"role": m.role, "content": text})
    if not msgs or msgs[0]["role"] != "user":
        msgs.insert(0, {"role": "user", "content": "Hello"})
    merged: List[dict] = []
    for m in msgs:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] = merged[-1]["content"] + "\n" + m["content"]
        else:
            merged.append(m)
    return ("\n\n".join(system_parts) if system_parts else None), merged

def _check_proxy_auth(authorization: Optional[str]):
    if not settings.LLM_PROXY_SECRET:
        raise HTTPException(status_code=500, detail="LLM_PROXY_SECRET not configured on server")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.LLM_PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid proxy token")

def _last_user_text(messages: List[OpenAIChatMessage]) -> str:
    for m in reversed(messages):
        if m.role == "user":
            txt = _flatten_openai_content(m.content)
            if txt: return txt
    return ""

async def _persist_voice_turn(
    session_id: str,
    user_text: str,
    assistant_text: str,
    model: str,
    db: DynamoDBService,
    angle: Optional[str] = None,
    recommended_car: Optional[str] = None,
    used_rag: bool = False,
    messages: Optional[List[dict]] = None,
) -> None:
    if not session_id: return
    try:
        await db.put_item(settings.T_CHAT, {
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
        
        langfuse = get_langfuse_client()
        if langfuse:
            from langfuse import propagate_attributes
            car_id = None
            user_id = None
            if session_id and session_id.startswith("car-"):
                parts = session_id.split("-")
                if len(parts) >= 2:
                    car_id = parts[1]
                    user_id = f"car-{car_id}"

            ctx_kwargs = {"session_id": session_id}
            if user_id: ctx_kwargs["user_id"] = user_id

            metadata = {
                "mode": "voice", "model": model, "angle": angle,
                "recommended_car": recommended_car, "used_rag": used_rag,
            }
            if car_id: metadata["car_id"] = car_id

            with propagate_attributes(**ctx_kwargs):
                trace_input = {"messages": messages} if messages else {"message": user_text or ""}
                with langfuse.start_as_current_observation(
                    name="voice-chat", as_type="span", input=trace_input, metadata=metadata
                ) as root_span:
                    generation_input = messages if messages else [{"role": "user", "content": user_text or ""}]
                    with langfuse.start_as_current_observation(
                        name="voice-generation", as_type="generation", model=model,
                        input=generation_input, metadata={
                            "angle": angle, "recommended_car": recommended_car, "used_rag": used_rag,
                        },
                    ) as gen:
                        gen.update(output=assistant_text or "")
                    root_span.update(output={"response": assistant_text or ""})
            if hasattr(langfuse, 'flush'): langfuse.flush()
    except Exception:
        logger.exception("Failed to persist voice turn for session=%s", session_id)

@router.post("/llm-proxy/v1/chat/completions")
async def llm_proxy_chat_completions(
    payload: OpenAIChatRequest,
    request: Request,
    db: DynamoDBService = Depends(get_db_service),
    llm: LLMService = Depends(get_llm_service)
):
    _check_proxy_auth(request.headers.get("authorization") or request.headers.get("Authorization"))
    system_prompt, anth_messages = _openai_to_anthropic(payload)
    model = payload.model or settings.MODEL_ID
    session_id = (payload.user or "").strip() or None
    if session_id:
        from core.logger import session_id_var
        session_id_var.set(session_id)
    last_user_text = _last_user_text(payload.messages)
    full_messages = [{"role": m.role, "content": _flatten_openai_content(m.content)} for m in payload.messages]

    used_rag = False
    if last_user_text:
        rag_ctx = await llm.build_rag_context(last_user_text, car_name="")
        if rag_ctx:
            used_rag = True
            ref_block = (
                "\n\nUse only the facts in the <reference> block below to answer specific "
                "spec questions. If the reference doesn't cover it, say so briefly.\n"
                "<reference>\n" + rag_ctx + "\n</reference>"
            )
            system_prompt = (system_prompt or "") + ref_block

    if payload.stream:
        async def event_stream():
            completion_id = f"chatcmpl-{uuid.uuid4().hex}"
            created = int(time.time())
            assistant_buf: List[str] = []
            angle_value: Optional[str] = None
            car_value: Optional[str] = None
            pending = ""
            sentinel_resolved = False
            SENTINEL_PEEK = 80

            def make_chunk(text_delta: str, role_first: bool) -> dict:
                return {
                    "id": completion_id, "object": "chat.completion.chunk",
                    "created": created, "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": ({"role": "assistant", "content": text_delta} if role_first else {"content": text_delta}),
                        "finish_reason": None,
                    }],
                }

            try:
                client = llm.get_client()
                kwargs = {"model": model, "max_tokens": payload.max_tokens or 1024, "messages": anth_messages}
                if system_prompt: kwargs["system"] = system_prompt
                if payload.temperature is not None: kwargs["temperature"] = payload.temperature
                if payload.top_p is not None: kwargs["top_p"] = payload.top_p

                role_first = True
                async with client.messages.stream(**kwargs) as stream:
                    async for delta in stream.text_stream:
                        if not delta: continue
                        if not sentinel_resolved:
                            pending += delta
                            a, c, cleaned = llm.parse_control_tags(pending)
                            tags_done = (a is not None or c is not None) and bool(cleaned)
                            if tags_done:
                                angle_value = a; car_value = c; sentinel_resolved = True
                                if cleaned:
                                    assistant_buf.append(cleaned)
                                    yield f"data: {_json.dumps(make_chunk(cleaned, role_first))}\n\n"
                                    role_first = False
                                pending = ""
                                continue
                            if len(pending) >= SENTINEL_PEEK:
                                angle_value = a; car_value = c; sentinel_resolved = True
                                flush = cleaned if (a is not None or c is not None) else pending
                                if flush:
                                    assistant_buf.append(flush)
                                    yield f"data: {_json.dumps(make_chunk(flush, role_first))}\n\n"
                                    role_first = False
                                pending = ""
                            continue
                        assistant_buf.append(delta)
                        yield f"data: {_json.dumps(make_chunk(delta, role_first))}\n\n"
                        role_first = False

                if not sentinel_resolved and pending:
                    assistant_buf.append(pending)
                    yield f"data: {_json.dumps(make_chunk(pending, role_first))}\n\n"

                stop_chunk = {
                    "id": completion_id, "object": "chat.completion.chunk",
                    "created": created, "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {_json.dumps(stop_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.exception("llm-proxy stream failed")
                err = {"error": {"message": str(e)[:300], "type": "upstream_error"}}
                yield f"data: {_json.dumps(err)}\n\n"
                yield "data: [DONE]\n\n"
                if not assistant_buf:
                    assistant_buf.append("Sorry, one moment while I reconnect.")
            finally:
                await _persist_voice_turn(
                    session_id=session_id or "", user_text=last_user_text,
                    assistant_text="".join(assistant_buf), model=model, db=db,
                    angle=angle_value, recommended_car=car_value, used_rag=used_rag, messages=full_messages,
                )

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        client = llm.get_client()
        kwargs = {"model": model, "max_tokens": payload.max_tokens or 1024, "messages": anth_messages}
        if system_prompt: kwargs["system"] = system_prompt
        if payload.temperature is not None: kwargs["temperature"] = payload.temperature
        if payload.top_p is not None: kwargs["top_p"] = payload.top_p

        resp = await client.messages.create(**kwargs)
        parts = []
        for block in resp.content or []:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "text":
                parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else ""))
        raw_text = "".join(parts)
    except Exception as e:
        logger.exception("llm-proxy non-stream failed")
        await _persist_voice_turn(
            session_id=session_id or "", user_text=last_user_text,
            assistant_text="Sorry, one moment while I reconnect.", model=model, db=db,
            used_rag=used_rag, messages=full_messages,
        )
        raise HTTPException(status_code=502, detail=f"LLM proxy error: {str(e)[:200]}")

    angle_value, car_value, text = llm.parse_control_tags(raw_text)

    await _persist_voice_turn(
        session_id=session_id or "", user_text=last_user_text,
        assistant_text=text, model=model, db=db, angle=angle_value,
        recommended_car=car_value, used_rag=used_rag, messages=full_messages,
    )

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

@router.get("/chat-session/{session_id}/pending-angle")
async def get_pending_angle(
    session_id: str,
    db: DynamoDBService = Depends(get_db_service)
):
    try:
        turns = await db.query_by_session(settings.T_CHAT, session_id=session_id, ascending=False, limit=1)
    except Exception:
        logger.exception("pending-angle query failed")
        raise HTTPException(status_code=502, detail="lookup failed")
    if not turns:
        return {"angle": None, "ts": None, "mode": None, "recommended_car": None}
    t = turns[0]
    return {
        "angle": t.get("angle"), "ts": t.get("created_at"),
        "mode": t.get("mode"), "recommended_car": t.get("recommended_car"),
    }
