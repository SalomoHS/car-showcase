from services.db import DynamoDBService
from services.llm import LLMService

_db_service = DynamoDBService()
_llm_service = LLMService()

def get_db_service() -> DynamoDBService:
    return _db_service

def get_llm_service() -> LLMService:
    return _llm_service
