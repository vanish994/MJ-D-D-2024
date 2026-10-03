import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.ux_assistant import CombatUXSnapshot, LongRestSummary


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    character: dict[str, Any] = Field(default_factory=dict)
    explanation_mode: Literal["beginner", "normal", "advanced"] = "beginner"

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("character")
    @classmethod
    def character_must_be_small_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("character must contain JSON-compatible values") from exc
        if len(encoded.encode("utf-8")) > 20_000:
            raise ValueError("character data must be at most 20 KB")
        return value


class CampaignUXSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation_mode: Literal["beginner", "normal", "advanced"]


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_input: str = Field(min_length=1, max_length=10_000)
    stream: bool = False

    @field_validator("player_input")
    @classmethod
    def player_input_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("player_input must not be blank")
        return value


class RuleSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=8, ge=1, le=30)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class FactsResolved(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_id: str | None = None
    status: str = "unresolved"
    action: str | None = None
    outcome: str | None = None
    rolls: list[dict[str, Any]] = Field(default_factory=list)
    damage: dict[str, Any] | None = None
    conditions_applied: list[dict[str, Any]] = Field(default_factory=list)
    state_changes: list[dict[str, Any]] = Field(default_factory=list)
    rules_used: list[str] = Field(default_factory=list)
    ux_snapshot: CombatUXSnapshot | None = None
    long_rest_summary: LongRestSummary | None = None
