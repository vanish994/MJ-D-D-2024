import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.campaign_service import get, save
from app.services.errors import CampaignNotFound, ExternalServiceError
from app.services.mimo_client import MimoClient
from app.services.resolution_contract import (
    ResolutionContractError,
    ValidatedResolution,
    fail_closed_resolution,
    validate_resolution_response,
)
from app.services.rule_engine_client import RuleEngineClient
from app.services.turn_contract import build_rule_state


rules = RuleEngineClient()
mimo = MimoClient()
MECHANICAL_TERMS = (
    "atacar", "ataco", "ataque", "golpe", "rola", "rolo", "rolar", "rolagem",
    "teste", "salvamento", "dano", "magia", "conjuro", "esquiva", "iniciativa",
    "pericia", "percepcao", "furtividade", "descanso", "cura", "curar", "hp",
    "pontos de vida", "condicao", "concentracao", "resistencia", "acerto critico",
    "abro", "abrir", "abri", "fecho", "fechar", "arrombo", "arrombar", "arrombei",
    "entro", "entrar", "saio", "sair", "subo", "desco", "escalo", "pulo", "pular",
    "corro", "correr", "movo", "mover", "avanco", "avancar", "atravesso", "atravessar",
    "investigo", "investigar", "examino", "examinar", "procuro", "procurar", "vasculho",
    "vasculhar", "escondo", "me escondo", "esconder", "persuadir", "persuado", "intimidar",
    "intimido", "enganar", "engano", "convencer", "convenço", "attack", "roll",
    "saving throw", "damage", "initiative", "spell", "open the door",
)
MAX_FEEDBACK_LENGTH = 500
MAX_HISTORY = 50


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def looks_mechanical(text: str) -> bool:
    """Label likely mechanical intent; the label never bypasses the Rule Engine."""
    normalized = _fold(text)
    for term in MECHANICAL_TERMS:
        term_pattern = r"\b" + re.escape(_fold(term)) + r"\b"
        if re.search(term_pattern, normalized):
            return True
    return False


def classify_intent(text: str) -> str:
    """Provide an advisory label; every input still goes through the Rule Engine."""
    return "mechanical_likely" if looks_mechanical(text) else "narrative_or_unknown"


def _validated_resolution(raw_resolution: Any) -> ValidatedResolution:
    try:
        return validate_resolution_response(raw_resolution)
    except ResolutionContractError:
        return fail_closed_resolution()


def _rule_feedback(resolution: ValidatedResolution) -> dict[str, str] | None:
    status = resolution.status
    if status == "resolved":
        return None
    raw_reason = resolution.reason
    if isinstance(raw_reason, str) and raw_reason.strip():
        message = raw_reason.strip()[:MAX_FEEDBACK_LENGTH]
    elif status == "needs_rule_validation":
        message = "O Rule Engine ainda não validou esta regra; nenhuma mudança mecânica foi aplicada."
    else:
        message = "O Rule Engine não resolveu esta ação; nenhuma mudança mecânica foi aplicada."
    feedback_type = "invalid_action" if status == "invalid_action" else "rule_validation"
    return {"type": feedback_type, "status": status, "message": message}


def _apply_authorized_changes(
    campaign: dict[str, Any], status: str, state_changes: dict[str, Any]
) -> None:
    if status != "resolved" or not state_changes:
        return
    mechanical_state = campaign.get("mechanical_state")
    if not isinstance(mechanical_state, dict):
        mechanical_state = {}
        campaign["mechanical_state"] = mechanical_state
    mechanical_state.update(state_changes)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def process_turn(campaign_id: str, player_input: str):
    campaign = get(campaign_id)
    if not campaign:
        raise CampaignNotFound("campaign not found")

    intent_classification = classify_intent(player_input)
    mechanical_state = campaign.get("mechanical_state", {})
    if not isinstance(mechanical_state, dict):
        mechanical_state = {}
    rule_state = build_rule_state(
        campaign_id=campaign_id,
        player_input=player_input,
        intent_classification=intent_classification,
        character=campaign.get("character"),
        mechanical_state=mechanical_state,
        inventory=campaign.get("inventory"),
        resources=campaign.get("resources"),
        scene=campaign.get("scene"),
    )
    # All player input is interpreted by the Rule Engine before the narrator,
    # including dialogue; the lexical label above never gates this request.
    raw_resolution = await rules.resolve(player_input, rule_state)
    resolution = _validated_resolution(raw_resolution)
    facts = resolution.narrator_facts
    resolution_status = resolution.status
    _apply_authorized_changes(campaign, resolution_status, resolution.state_changes)
    feedback = _rule_feedback(resolution)

    turn_record = {
        "turn_id": str(uuid.uuid4()),
        "created_at": _now(),
        "player": player_input,
        "intent_classification": intent_classification,
        "resolution_status": resolution_status,
        "facts_resolvidos": facts,
        "rule_feedback": feedback,
        "narrative": "",
        "narrative_status": "pending",
    }
    history = campaign.get("history")
    if not isinstance(history, list):
        history = []
    history.append(turn_record)
    campaign["history"] = history[-MAX_HISTORY:]

    # Persist validated state and a pending turn before calling the narrator.
    save(campaign)
    try:
        scene = campaign.get("scene", {})
        narrative = await mimo.narrate(
            campaign_id,
            scene if isinstance(scene, dict) else {},
            player_input,
            facts,
        )
    except ExternalServiceError:
        turn_record["narrative_status"] = "failed"
        save(campaign)
        raise

    turn_record["narrative"] = narrative
    turn_record["narrative_status"] = "completed"
    save(campaign)
    return campaign, facts, narrative, resolution_status, turn_record["turn_id"], feedback
