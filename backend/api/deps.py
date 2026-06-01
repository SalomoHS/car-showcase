from services.db import DynamoDBService
from services.llm import LLMService
from services.cw import get_cw_metrics_service, CloudWatchMetricsService

_db_service = DynamoDBService()
_llm_service = LLMService()
_cw_service = get_cw_metrics_service()

def get_db_service() -> DynamoDBService:
    return _db_service

def get_llm_service() -> LLMService:
    return _llm_service

def get_cw_metrics_service() -> CloudWatchMetricsService:
    return _cw_service
