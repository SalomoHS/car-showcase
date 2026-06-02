from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union
import uuid
from datetime import datetime, timezone

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

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
    session_id: Optional[str] = ''

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

class OpenAIChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str
    content: Optional[object] = None

class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: List[OpenAIChatMessage]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = False
    user: Optional[str] = None

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
