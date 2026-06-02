from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from models.domain import Lead, LeadCreate
from api.deps import get_db_service, get_cw_metrics_service, DynamoDBService, CloudWatchMetricsService
from core.config import settings
from core.logger import logger

router = APIRouter()

@router.post("/", response_model=Lead)
async def create_lead(
    payload: LeadCreate,
    db: DynamoDBService = Depends(get_db_service),
    cw: CloudWatchMetricsService = Depends(get_cw_metrics_service)
):
    if not payload.name.strip() or not payload.phone.strip() or not payload.location.strip():
        await cw.increment_error_count()
        raise HTTPException(status_code=400, detail="name, phone and location are required")

    
    session_id = payload.session_id
    from core.logger import session_id_var
    session_id_var.set(session_id)

    lead = Lead(**payload.model_dump())
    doc = lead.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    logger.info(f"New test-drive lead: {lead.name} ({lead.phone}) — {lead.car_name} @ {lead.location}")
    await db.put_item(settings.T_LEADS, doc)
    await cw.increment_request_count()
    
    return lead

@router.get("/", response_model=List[Lead])
async def list_leads(
    db: DynamoDBService = Depends(get_db_service)
):
    items = await db.scan_all(settings.T_LEADS, limit=500)
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    for l in items:
        if isinstance(l.get('created_at'), str):
            l['created_at'] = datetime.fromisoformat(l['created_at'])
    return items
