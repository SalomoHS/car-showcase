from fastapi import APIRouter
from api.routes import status, leads, chat, agora

api_router = APIRouter()

api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(agora.router, prefix="/agora", tags=["agora"])
