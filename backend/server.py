from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi.responses import FileResponse


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
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
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


# ──────────────────── VIRTUAL SALES AVATAR (LLM + D-ID) ────────────────────
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
DID_API_KEY = os.environ.get('DID_API_KEY')
DID_PRESENTER_IMAGE = os.environ.get('DID_PRESENTER_IMAGE')
DID_VOICE_ID = os.environ.get('DID_VOICE_ID', 'en-US-AriaNeural')
DID_BASE = 'https://api.d-id.com'

# Local cache for D-ID videos (proxied to avoid CORS issues with S3 signed URLs)
VIDEO_CACHE_DIR = Path('/tmp/avatar_videos')
VIDEO_CACHE_DIR.mkdir(exist_ok=True)


class ChatRequest(BaseModel):
    message: str
    car_id: str
    car_name: str
    car_tagline: Optional[str] = ''
    session_id: Optional[str] = None
    generate_video: bool = True  # set False for text-only fast response


class ChatResponse(BaseModel):
    text: str
    video_url: Optional[str] = None
    session_id: str


async def generate_llm_response(message: str, car_name: str, car_tagline: str, session_id: str) -> str:
    system_prompt = (
        f"You are Aria, a friendly and knowledgeable luxury car sales specialist. "
        f"The customer is currently viewing the {car_name} ({car_tagline}). "
        "Answer their question in 2-3 short sentences with a warm, conversational tone. "
        "Be specific about the car when relevant, and gently encourage interest without being pushy. "
        "Never mention you are an AI; speak as Aria the sales specialist. "
        "Keep responses under 280 characters so the avatar video stays short."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model("openai", "gpt-4.1-mini")

    response = await chat.send_message(UserMessage(text=message))
    return response.strip()


async def generate_did_talk(text: str) -> Optional[str]:
    """Create a D-ID talk and poll until done. Returns the MP4 result_url, or None on failure."""
    if not DID_API_KEY or not DID_PRESENTER_IMAGE:
        return None

    headers = {
        "Authorization": f"Basic {DID_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "source_url": DID_PRESENTER_IMAGE,
        "script": {
            "type": "text",
            "input": text,
            "provider": {"type": "microsoft", "voice_id": DID_VOICE_ID},
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        create = await client.post(f"{DID_BASE}/talks", json=payload, headers=headers)
        if create.status_code >= 400:
            logger.error(f"D-ID create failed: {create.status_code} {create.text}")
            return None
        talk_id = create.json().get("id")
        if not talk_id:
            return None

        # Poll up to 30s
        for _ in range(15):
            await asyncio.sleep(2)
            poll = await client.get(f"{DID_BASE}/talks/{talk_id}", headers=headers)
            if poll.status_code >= 400:
                logger.error(f"D-ID poll failed: {poll.status_code}")
                return None
            body = poll.json()
            status = body.get("status")
            if status == "done":
                return body.get("result_url")
            if status == "error":
                logger.error(f"D-ID talk errored: {body}")
                return None
    return None


@api_router.post("/chat-with-avatar", response_model=ChatResponse)
async def chat_with_avatar(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

    session_id = payload.session_id or f"car-{payload.car_id}-{uuid.uuid4().hex[:8]}"

    try:
        text = await generate_llm_response(
            payload.message, payload.car_name, payload.car_tagline or '', session_id
        )
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)[:120]}")

    video_url = None
    if payload.generate_video:
        try:
            did_url = await generate_did_talk(text)
            if did_url:
                # Download and cache locally so the frontend can stream same-origin
                video_id = uuid.uuid4().hex
                cache_path = VIDEO_CACHE_DIR / f"{video_id}.mp4"
                async with httpx.AsyncClient(timeout=30.0) as dl:
                    async with dl.stream("GET", did_url) as r:
                        r.raise_for_status()
                        with open(cache_path, 'wb') as f:
                            async for chunk in r.aiter_bytes(chunk_size=65536):
                                f.write(chunk)
                video_url = f"/api/avatar-video/{video_id}.mp4"
        except Exception as e:
            logger.exception(f"D-ID call failed: {e}")
            video_url = None

    # Persist conversation
    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "car_id": payload.car_id,
        "car_name": payload.car_name,
        "user_message": payload.message,
        "ai_response": text,
        "video_url": video_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return ChatResponse(text=text, video_url=video_url, session_id=session_id)

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