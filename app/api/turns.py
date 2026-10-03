from fastapi import APIRouter, HTTPException

from app.models import TurnRequest
from app.services.errors import CampaignNotFound, ExternalServiceError
from app.services.turn_service import process_turn
from app.services.ux_assistant import format_long_rest_summary


router = APIRouter(prefix="/v1/campaigns", tags=["turns"])


def _long_rest_summary(facts: dict):
    action = facts.get("action")
    if not isinstance(action, str) or action.casefold() not in {"long_rest", "long rest"}:
        return None
    return format_long_rest_summary(facts.get("long_rest_summary"))


@router.post("/{campaign_id}/turn")
async def turn(campaign_id: str, body: TurnRequest):
    if body.stream:
        raise HTTPException(
            status_code=501,
            detail="stream=true is not supported by this MVP; use stream=false",
        )
    try:
        campaign, facts, narrative, resolution_status, turn_id, feedback = await process_turn(
            campaign_id, body.player_input
        )
    except CampaignNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_error", "service": exc.service, "operation": exc.operation},
        ) from exc
    return {
        "campaign": campaign,
        "turn_id": turn_id,
        "resolution_status": resolution_status,
        "rule_feedback": feedback,
        "facts_resolvidos": facts,
        "long_rest_summary": _long_rest_summary(facts),
        "narrative": narrative,
    }
