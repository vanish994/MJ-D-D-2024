from fastapi import APIRouter, HTTPException

from app.models import CampaignUXSettingsUpdate
from app.services.campaign_service import get, save
from app.services.ux_assistant import project_combat_ux


router = APIRouter(prefix="/v1/campaigns", tags=["ux"])


def _latest_rule_engine_snapshot(campaign: dict):
    history = campaign.get("history", [])
    if not isinstance(history, list):
        return None, None
    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        status = entry.get("resolution_status")
        if status == "not_required":
            continue
        # A later unresolved mechanical attempt invalidates an older action menu.
        if status != "resolved":
            return None, None
        facts = entry.get("facts_resolvidos")
        if not isinstance(facts, dict):
            return None, None
        snapshot = facts.get("ux_snapshot")
        return (snapshot if isinstance(snapshot, dict) else None), entry.get("created_at")
    return None, None


@router.get("/{campaign_id}/assistant")
def assistant(campaign_id: str):
    campaign = get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    settings = campaign.get("ux_settings", {})
    mode = settings.get("explanation_mode", "beginner") if isinstance(settings, dict) else "beginner"
    if mode not in {"beginner", "normal", "advanced"}:
        mode = "beginner"
    snapshot, snapshot_created_at = _latest_rule_engine_snapshot(campaign)
    result = project_combat_ux(snapshot, mode)
    result["campaign_id"] = campaign_id
    result["snapshot_created_at"] = snapshot_created_at
    return result


@router.patch("/{campaign_id}/ux-settings")
def update_ux_settings(campaign_id: str, body: CampaignUXSettingsUpdate):
    campaign = get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    ux_settings = campaign.get("ux_settings")
    if not isinstance(ux_settings, dict):
        ux_settings = {}
    ux_settings["explanation_mode"] = body.explanation_mode
    campaign["ux_settings"] = ux_settings
    save(campaign)
    return {"campaign_id": campaign_id, "ux_settings": ux_settings}
