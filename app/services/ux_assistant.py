"""UX projection helpers.

This module is deliberately a formatter, not a rules engine. It can only expose
structured values explicitly returned by the external Rule Engine.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ExplanationMode = Literal["beginner", "normal", "advanced"]


class TurnResources(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: bool | None = None
    bonus_action: bool | None = None
    reaction: bool | None = None
    movement_remaining: float | None = None
    movement_unit: str | None = None


class ActionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    cost: str | None = None
    explanation: str | None = None
    rule_refs: list[str] | None = None


class UnavailableAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)


class CombatUXSnapshot(BaseModel):
    """Optional Rule Engine snapshot; `current` must be explicit to enable options."""

    model_config = ConfigDict(extra="forbid")

    current: bool | None = None
    observed_at: str | None = None
    resolution_id: str | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    conditions: list[dict[str, Any]] | None = None
    active_effects: list[dict[str, Any]] | None = None
    concentration: dict[str, Any] | None = None
    turn_resources: TurnResources | None = None
    available_actions: list[ActionOption] | None = None
    available_bonus_actions: list[ActionOption] | None = None
    available_reactions: list[ActionOption] | None = None
    unavailable_actions: list[UnavailableAction] | None = None
    class_resources: dict[str, Any] | None = None
    character_resources: dict[str, Any] | None = None
    relevant_inventory: list[dict[str, Any]] | None = None
    position: dict[str, Any] | None = None
    turn_number: int | None = None
    round_number: int | None = None
    combat_active: bool | None = None


class LongRestSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hp_before: int | None = None
    hp_after: int | None = None
    hp_max: int | None = None
    resources_recovered: list[dict[str, Any]] | None = None
    effects_ended: list[dict[str, Any]] | None = None
    effects_continuing: list[dict[str, Any]] | None = None


def _warning(key: str, value: Any) -> dict[str, Any]:
    labels = {
        "action": "Ação",
        "bonus_action": "Ação Bônus",
        "reaction": "Reação",
    }
    label = labels[key]
    if value is True:
        message = f"Você ainda possui {label} neste turno."
    else:
        message = f"Você já utilizou {label} neste turno."
    return {"resource": key, "available": value, "message": message}


def project_combat_ux(
    raw_snapshot: dict[str, Any] | CombatUXSnapshot | None,
    mode: ExplanationMode = "beginner",
) -> dict[str, Any]:
    """Return a UI-ready projection without inventing facts or default availability."""
    if raw_snapshot is None:
        return {
            "status": "unavailable",
            "currentness": "unknown",
            "explanation_mode": mode,
            "source": "rule_engine",
            "turn_resources": None,
            "available_actions": None,
            "available_bonus_actions": None,
            "available_reactions": None,
            "unavailable_actions": None,
            "warnings": [],
            "message": "O Rule Engine ainda não forneceu um snapshot estruturado do turno.",
        }
    try:
        snapshot = raw_snapshot if isinstance(raw_snapshot, CombatUXSnapshot) else CombatUXSnapshot.model_validate(raw_snapshot)
    except ValidationError:
        return {
            "status": "unavailable",
            "currentness": "unknown",
            "explanation_mode": mode,
            "source": "rule_engine",
            "turn_resources": None,
            "available_actions": None,
            "available_bonus_actions": None,
            "available_reactions": None,
            "unavailable_actions": None,
            "warnings": [],
            "message": "O snapshot do Rule Engine não corresponde ao contrato UX validado.",
        }

    if snapshot.current is not True:
        return {
            "status": "unavailable",
            "currentness": "not_confirmed_current",
            "explanation_mode": mode,
            "source": "rule_engine",
            "resolution_id": snapshot.resolution_id,
            "observed_at": snapshot.observed_at,
            "turn_resources": None,
            "available_actions": None,
            "available_bonus_actions": None,
            "available_reactions": None,
            "unavailable_actions": None,
            "warnings": [],
            "message": "As opções não serão apresentadas como atuais sem confirmação do Rule Engine.",
        }

    resources = snapshot.turn_resources
    warnings = []
    if resources is not None:
        for key in ("action", "bonus_action", "reaction"):
            value = getattr(resources, key)
            if value is not None:
                warnings.append(_warning(key, value))
        if resources.movement_remaining is not None:
            warning = {
                "resource": "movement_remaining",
                "value": resources.movement_remaining,
                "unit": resources.movement_unit,
            }
            if resources.movement_unit:
                warning["message"] = f"Movimento restante: {resources.movement_remaining:g} {resources.movement_unit}."
            else:
                warning["message"] = f"Movimento restante informado: {resources.movement_remaining:g} (unidade não especificada)."
            warnings.append(warning)

    def dump_options(values: list[ActionOption] | None) -> list[dict[str, Any]] | None:
        if values is None:
            return None
        output = []
        for item in values:
            row = item.model_dump(exclude_none=True)
            if mode == "advanced":
                row.pop("explanation", None)
            output.append(row)
        return output

    any_action_data = any(
        value is not None
        for value in (
            snapshot.available_actions,
            snapshot.available_bonus_actions,
            snapshot.available_reactions,
        )
    )
    return {
        "status": "available" if any_action_data else "incomplete",
        "currentness": "confirmed_current",
        "explanation_mode": mode,
        "source": "rule_engine",
        "resolution_id": snapshot.resolution_id,
        "observed_at": snapshot.observed_at,
        "hp_current": snapshot.hp_current,
        "hp_max": snapshot.hp_max,
        "conditions": snapshot.conditions,
        "active_effects": snapshot.active_effects,
        "concentration": snapshot.concentration,
        "turn_resources": resources.model_dump(exclude_none=True) if resources else None,
        "available_actions": dump_options(snapshot.available_actions),
        "available_bonus_actions": dump_options(snapshot.available_bonus_actions),
        "available_reactions": dump_options(snapshot.available_reactions),
        "unavailable_actions": [item.model_dump() for item in snapshot.unavailable_actions]
        if snapshot.unavailable_actions is not None else None,
        "class_resources": snapshot.class_resources,
        "character_resources": snapshot.character_resources,
        "relevant_inventory": snapshot.relevant_inventory,
        "position": snapshot.position,
        "turn_number": snapshot.turn_number,
        "round_number": snapshot.round_number,
        "combat_active": snapshot.combat_active,
        "warnings": warnings,
        "message": None if any_action_data else "O Rule Engine ainda não forneceu opções estruturadas para este turno.",
    }


def format_long_rest_summary(raw_summary: dict[str, Any] | LongRestSummary | None) -> dict[str, Any] | None:
    """Format only explicit Rule Engine rest results; never infer recovery or effect duration."""
    if raw_summary is None:
        return None
    try:
        summary = raw_summary if isinstance(raw_summary, LongRestSummary) else LongRestSummary.model_validate(raw_summary)
    except ValidationError:
        return None
    return summary.model_dump(exclude_none=True)
