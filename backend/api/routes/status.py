from fastapi import APIRouter, Depends
from typing import List
from datetime import datetime
from models.domain import StatusCheck, StatusCheckCreate
from api.deps import get_db_service, DynamoDBService
from core.config import settings

router = APIRouter()

@router.post("/", response_model=StatusCheck)
async def create_status_check(
    input: StatusCheckCreate,
    db: DynamoDBService = Depends(get_db_service)
):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.put_item(settings.T_STATUS, doc)
    return status_obj

@router.get("/", response_model=List[StatusCheck])
async def get_status_checks(
    db: DynamoDBService = Depends(get_db_service)
):
    items = await db.scan_all(settings.T_STATUS, limit=1000)
    for check in items:
        if isinstance(check.get('timestamp'), str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return items
