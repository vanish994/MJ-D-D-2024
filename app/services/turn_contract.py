"""Versioned, non-mechanical state envelope sent to the Rule Engine."""

from typing import Any


RULE_STATE_SCHEMA_VERSION = "mj-rule-state-v1"


def build_rule_state(
    *,
    campaign_id: str,
    player_input: str,
    intent_classification: str,
    character: Any,
    mechanical_state: dict[str, Any],
    inventory: Any,
    resources: Any,
    scene: Any,
) -> dict[str, Any]:
    """Build the Rule Engine state payload without deriving game mechanics.

    Optional campaign fields use the contract's empty-container defaults only
    when absent (`None`). Values that are present are passed through unchanged.
    The mechanical state must remain an object; malformed values are rejected.
    """
    if not isinstance(mechanical_state, dict):
        raise TypeError("mechanical_state must be a dict")

    return {
        "schema_version": RULE_STATE_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "character": {} if character is None else character,
        "mechanical_state": dict(mechanical_state),
        "inventory": [] if inventory is None else inventory,
        "resources": {} if resources is None else resources,
        "scene": {} if scene is None else scene,
        "intent": {
            "classification": intent_classification,
            "player_input": player_input,
        },
    }
