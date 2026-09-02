from fastapi import APIRouter
from typing import Dict, Any
from . import schemas, service

router = APIRouter()

@router.post("/trigger", status_code=202)
async def trigger_workflow(payload: schemas.WebhookPayload):
    """
    Trigger an n8n workflow from our FastAPI backend.
    """
    return await service.trigger_n8n_workflow(payload.payload)

@router.post("/incoming")
async def incoming_webhook(payload: Dict[str, Any]):
    """
    Receive incoming HTTP requests from n8n.
    """
    return await service.process_n8n_callback(payload)
