import unittest

from pydantic import ValidationError

from app.services.narrator_input import (
    NARRATOR_INPUT_SCHEMA_VERSION,
    NarratorInput,
    build_narrator_input,
)
from app.services.resolution_contract import (
    RULE_RESOLUTION_SCHEMA_VERSION,
    ValidatedResolution,
    validate_resolution_response,
)
from app.services.turn_contract import RULE_STATE_SCHEMA_VERSION


def valid_input():
    return {
        "schema_version": NARRATOR_INPUT_SCHEMA_VERSION,
        "campaign": {"campaign_id": "campaign-test"},
        "player_input": "Eu tento convencer o guarda.",
        "scene": {},
        "character_context": {},
        "narrative_context": {},
        "resolved_facts": {},
        "ux_context": {},
    }


def resolved_with_snapshot():
    return validate_resolution_response(
        {
            "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
            "status": "resolved",
            "ux_snapshot": {
                "current": True,
                "turn_resources": {"bonus_action": True, "reaction": False},
            },
        }
    )


class NarratorInputContractTests(unittest.TestCase):
    def test_valid_narrator_input_v1_is_accepted(self):
        result = NarratorInput.model_validate(valid_input())
        self.assertEqual(result.schema_version, "narrator-input-v1")
        self.assertEqual(result.resolved_facts, {})
        self.assertEqual(result.ux_context, {})

    def test_unknown_or_missing_version_is_rejected(self):
        payload = valid_input()
        payload["schema_version"] = "narrator-input-v0"
        with self.assertRaises(ValidationError):
            NarratorInput.model_validate(payload)

        payload = valid_input()
        del payload["schema_version"]
        with self.assertRaises(ValidationError):
            NarratorInput.model_validate(payload)

    def test_player_input_is_preserved_without_rewriting(self):
        text = "  Tento persuadir o guarda — sem sacar a arma.  "
        result = build_narrator_input(
            {"id": "campaign-test"},
            text,
            ValidatedResolution("awaiting_input", {}, {}),
        )
        self.assertEqual(result.player_input, text)

    def test_validated_resolved_facts_are_accepted(self):
        resolution = validate_resolution_response(
            {
                "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                "status": "resolved",
                "action": {"type": "social_check"},
                "outcome": {"success": True, "total": 17},
                "state_changes": {"reputation": 1},
            }
        )
        result = build_narrator_input(
            {"id": "campaign-test"}, "Eu argumento com o guarda.", resolution
        )
        self.assertEqual(result.resolved_facts["status"], "resolved")
        self.assertEqual(result.resolved_facts["outcome"]["total"], 17)

    def test_empty_facts_are_a_valid_narrator_input(self):
        result = build_narrator_input(
            {"id": "campaign-test"},
            "Pergunto ao guarda sobre a estrada.",
            ValidatedResolution("awaiting_input", {}, {}),
        )
        self.assertEqual(result.resolved_facts, {})
        self.assertEqual(result.ux_context, {})

    def test_unresolved_or_forged_facts_are_never_promoted(self):
        untrusted = ValidatedResolution(
            "needs_rule_validation",
            {
                "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                "status": "resolved",
                "state_changes": {"hp": 0},
                "ux_snapshot": {"current": True, "turn_resources": {"action": True}},
            },
            {"hp": 0},
        )
        result = build_narrator_input(
            {"id": "campaign-test"}, "Eu tento atacar.", untrusted
        )
        self.assertEqual(result.resolved_facts, {})
        self.assertEqual(result.ux_context, {})

    def test_ux_context_is_only_the_explicit_validated_snapshot(self):
        result = build_narrator_input(
            {"id": "campaign-test"}, "Converso com o guarda.", resolved_with_snapshot()
        )
        self.assertEqual(
            result.ux_context,
            {
                "current": True,
                "turn_resources": {"bonus_action": True, "reaction": False},
            },
        )
        self.assertNotIn("available_actions", result.ux_context)
        self.assertNotIn("action", result.ux_context["turn_resources"])

    def test_unknown_fields_and_unresolved_ux_data_are_rejected(self):
        payload = valid_input()
        payload["unexpected"] = "no"
        with self.assertRaises(ValidationError):
            NarratorInput.model_validate(payload)

        payload = valid_input()
        payload["ux_context"] = {"bonus_action_available": True}
        with self.assertRaises(ValidationError):
            NarratorInput.model_validate(payload)

        payload = valid_input()
        payload["campaign"]["name"] = "not part of campaign reference"
        with self.assertRaises(ValidationError):
            NarratorInput.model_validate(payload)

    def test_context_builder_does_not_dump_campaign_or_private_scene_fields(self):
        campaign = {
            "id": "campaign-test",
            "name": "Campanha confidencial",
            "character": {"name": "Personagem", "hp": 12},
            "mechanical_state": {"hp": 12},
            "inventory": ["item privado"],
            "resources": {"spell_slots": 2},
            "npcs": [{"name": "NPC secreto"}],
            "history": [{"player": "fala anterior"}],
            "secret_world_knowledge": "não transmitir",
            "scene": {
                "type": "social",
                "location": {
                    "name": "Portão",
                    "public_description": "de pedra",
                    "secret": "entrada oculta",
                },
                "description": "Um guarda observa a estrada.",
                "participants": [
                    {
                        "name": "Guarda",
                        "public_description": "usa uma capa azul",
                        "secret": "é um espião",
                    }
                ],
                "private_gm_note": "não transmitir",
            },
            "character_context": {"identity": "viajante"},
            "narrative_context": {"known_facts": ["a estrada está fechada"]},
        }
        result = build_narrator_input(
            campaign,
            "Pergunto sobre a estrada.",
            ValidatedResolution("awaiting_input", {}, {}),
        )
        serialized = result.model_dump(mode="json")
        self.assertEqual(serialized["campaign"], {"campaign_id": "campaign-test"})
        self.assertEqual(serialized["character_context"], {"identity": "viajante"})
        self.assertEqual(
            serialized["narrative_context"], {"known_facts": ["a estrada está fechada"]}
        )
        self.assertEqual(
            serialized["scene"],
            {
                "type": "social",
                "location": {"name": "Portão", "public_description": "de pedra"},
                "description": "Um guarda observa a estrada.",
                "participants": [
                    {"name": "Guarda", "public_description": "usa uma capa azul"}
                ],
            },
        )
        self.assertNotIn("character", serialized)
        self.assertNotIn("mechanical_state", serialized)
        self.assertNotIn("history", serialized)
        self.assertNotIn("secret_world_knowledge", serialized)
        self.assertNotIn("private_gm_note", serialized["scene"])

    def test_existing_contract_versions_are_unchanged(self):
        self.assertEqual(RULE_STATE_SCHEMA_VERSION, "mj-rule-state-v1")
        self.assertEqual(RULE_RESOLUTION_SCHEMA_VERSION, "rule-resolution-v1")
        self.assertEqual(NARRATOR_INPUT_SCHEMA_VERSION, "narrator-input-v1")


if __name__ == "__main__":
    unittest.main()
