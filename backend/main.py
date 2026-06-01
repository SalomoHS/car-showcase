from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from core.config import settings
from core.logger import logger
from api.router import api_router

app = FastAPI()

app.include_router(api_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/")
async def root():
    return {"message": "Hello World"}
