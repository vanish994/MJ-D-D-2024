import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models import CampaignCreate
from app.services.campaign_service import get, save


router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("", status_code=201)
def create(body: CampaignCreate):
    now = _now()
    campaign = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "character": body.character,
        "scene": {},
        "npcs": [],
        "mechanical_state": {},
        "inventory": [],
        "resources": {},
        "ux_settings": {"explanation_mode": body.explanation_mode},
        "history": [],
        "created_at": now,
        "updated_at": now,
    }
    save(campaign)
    return campaign


@router.get("/{campaign_id}")
def retrieve(campaign_id: str):
    campaign = get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    return campaign
