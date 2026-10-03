"""Versioned, allowlisted data passed from the MJ orchestrator to the narrator."""

import json
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    ValidationError,
    model_validator,
)

from app.services.resolution_contract import (
    RULE_RESOLUTION_SCHEMA_VERSION,
    ValidatedResolution,
)

NARRATOR_INPUT_SCHEMA_VERSION = "narrator-input-v1"


class CampaignReference(BaseModel):
    """The narrator receives a campaign identifier, never a database dump."""

    model_config = ConfigDict(extra="forbid", strict=True)

    campaign_id: StrictStr = Field(min_length=1, max_length=128)


class NarratorInput(BaseModel):
    """Validated narrative context; this contract grants no mechanical authority."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["narrator-input-v1"]
    campaign: CampaignReference
    player_input: StrictStr = Field(min_length=1, max_length=10_000)
    scene: dict[StrictStr, Any] = Field(default_factory=dict)
    character_context: dict[StrictStr, Any] = Field(default_factory=dict)
    narrative_context: dict[StrictStr, Any] = Field(default_factory=dict)
    resolved_facts: dict[StrictStr, Any] = Field(default_factory=dict)
    ux_context: dict[StrictStr, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_authorized_facts_and_json(self):
        facts = self.resolved_facts
        if facts:
            if (
                facts.get("schema_version") != RULE_RESOLUTION_SCHEMA_VERSION
                or facts.get("status") != "resolved"
            ):
                raise ValueError(
                    "resolved_facts must come from a validated resolved response"
                )
            snapshot = facts.get("ux_snapshot")
            expected_ux = snapshot if isinstance(snapshot, dict) else {}
            if self.ux_context != expected_ux:
                raise ValueError(
                    "ux_context must exactly match the explicit resolved UX snapshot"
                )
        elif self.ux_context:
            raise ValueError("ux_context requires explicitly resolved facts")

        try:
            json.dumps(
                self.model_dump(mode="python"),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise ValueError(
                "narrator input must contain JSON-compatible values"
            ) from exc
        return self


def _explicit_context(campaign: dict[str, Any], key: str) -> dict[str, Any]:
    """Read only a purpose-built context field; do not mine unrelated campaign data."""
    value = campaign.get(key)
    return value if isinstance(value, dict) else {}


def _scene_context(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project scene facts and public participant/location fields only."""
    source = _explicit_context(campaign, "scene")
    scene: dict[str, Any] = {}
    if isinstance(source.get("type"), str):
        scene["type"] = source["type"]
    if isinstance(source.get("description"), str):
        scene["description"] = source["description"]

    location = source.get("location")
    if isinstance(location, str):
        scene["location"] = location
    elif isinstance(location, dict):
        public_location = {
            key: location[key]
            for key in ("name", "type", "public_description")
            if isinstance(location.get(key), str)
        }
        if public_location:
            scene["location"] = public_location

    participants = source.get("participants")
    if isinstance(participants, list):
        public_participants = []
        for participant in participants:
            if isinstance(participant, str):
                public_participants.append(participant)
            elif isinstance(participant, dict):
                public_participant = {
                    key: participant[key]
                    for key in (
                        "id",
                        "name",
                        "public_description",
                        "known_relationship",
                    )
                    if isinstance(participant.get(key), str)
                }
                if public_participant:
                    public_participants.append(public_participant)
        scene["participants"] = public_participants
    return scene


def build_narrator_input(
    campaign: dict[str, Any],
    player_input: str,
    resolution: ValidatedResolution,
) -> NarratorInput:
    """Build the narrator boundary from the current campaign and validated result.

    `character_context` and `narrative_context` are opt-in, curated campaign fields.
    The builder deliberately does not copy `character`, `mechanical_state`,
    `inventory`, `resources`, `npcs`, or `history` automatically.
    """
    campaign_id = campaign.get("id") if isinstance(campaign, dict) else None
    facts: dict[str, Any] = {}
    if resolution.status == "resolved" and isinstance(resolution.narrator_facts, dict):
        candidate = resolution.narrator_facts
        if (
            candidate.get("schema_version") == RULE_RESOLUTION_SCHEMA_VERSION
            and candidate.get("status") == "resolved"
        ):
            facts = candidate

    snapshot = facts.get("ux_snapshot")
    ux_context = snapshot if isinstance(snapshot, dict) else {}

    return NarratorInput.model_validate(
        {
            "schema_version": NARRATOR_INPUT_SCHEMA_VERSION,
            "campaign": {"campaign_id": campaign_id},
            "player_input": player_input,
            "scene": _scene_context(campaign),
            "character_context": _explicit_context(campaign, "character_context"),
            "narrative_context": _explicit_context(campaign, "narrative_context"),
            "resolved_facts": facts,
            "ux_context": ux_context,
        }
    )


__all__ = [
    "NARRATOR_INPUT_SCHEMA_VERSION",
    "CampaignReference",
    "NarratorInput",
    "build_narrator_input",
]
