import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.models import FactsResolved
from app.services.campaign_service import get, save
from app.services.errors import CampaignNotFound, ExternalServiceError
from app.services.mimo_client import MimoClient
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
STATE_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
MAX_STATE_CHANGES = 32
MAX_FACTS_BYTES = 50_000
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


def _validated_facts(resolution: Any) -> tuple[dict[str, Any], str]:
    if not isinstance(resolution, dict):
        return {}, "needs_rule_validation"
    status = resolution.get("status")
    if status != "resolved":
        return {}, status if isinstance(status, str) else "needs_rule_validation"

    raw_facts = resolution.get("facts_resolvidos")
    if raw_facts is None:
        raw_facts = resolution.get("FATOS_RESOLVIDOS")
    if not isinstance(raw_facts, dict):
        return {}, "needs_rule_validation"
    try:
        facts_model = FactsResolved.model_validate(raw_facts)
        facts = facts_model.model_dump(exclude_none=True)
        encoded = json.dumps(facts, ensure_ascii=False, allow_nan=False)
    except (ValidationError, TypeError, ValueError):
        return {}, "needs_rule_validation"

    if facts.get("status") != "resolved" or len(encoded.encode("utf-8")) > MAX_FACTS_BYTES:
        return {}, "needs_rule_validation"
    changes = facts.get("state_changes", [])
    if not isinstance(changes, list) or len(changes) > MAX_STATE_CHANGES:
        return {}, "needs_rule_validation"
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"key", "value"}:
            return {}, "needs_rule_validation"
        if not isinstance(change["key"], str) or not STATE_KEY_RE.fullmatch(change["key"]):
            return {}, "needs_rule_validation"
    return facts, "resolved"


def _rule_feedback(resolution: Any, status: str) -> dict[str, str] | None:
    if status in ("not_required", "narrative_only", "resolved"):
        return None
    raw_reason = None
    if isinstance(resolution, dict):
        raw_reason = resolution.get("reason") or resolution.get("message")
    if isinstance(raw_reason, str) and raw_reason.strip():
        message = raw_reason.strip()[:MAX_FEEDBACK_LENGTH]
    elif status == "needs_rule_validation":
        message = "O Rule Engine ainda não validou esta regra; nenhuma mudança mecânica foi aplicada."
    else:
        message = "O Rule Engine não resolveu esta ação; nenhuma mudança mecânica foi aplicada."
    feedback_type = "invalid_action" if status in {"invalid", "invalid_action", "rejected"} else "rule_validation"
    return {"type": feedback_type, "status": status, "message": message}


def _apply_authorized_changes(campaign: dict[str, Any], facts: dict[str, Any]) -> None:
    if facts.get("status") != "resolved":
        return
    mechanical_state = campaign.get("mechanical_state")
    if not isinstance(mechanical_state, dict):
        mechanical_state = {}
        campaign["mechanical_state"] = mechanical_state
    for change in facts.get("state_changes", []):
        mechanical_state[change["key"]] = change["value"]


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
    resolution = await rules.resolve(player_input, rule_state)
    facts, resolution_status = _validated_facts(resolution)
    _apply_authorized_changes(campaign, facts)
    feedback = _rule_feedback(resolution, resolution_status)

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
