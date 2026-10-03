import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import turn_service
from app.services.resolution_contract import RULE_RESOLUTION_SCHEMA_VERSION
from app.services.turn_contract import RULE_STATE_SCHEMA_VERSION, build_rule_state


class TurnContractBuilderTests(unittest.TestCase):
    def test_preserves_campaign_data_and_builds_intent_metadata(self):
        character = {"name": "Ari", "abilities": {"strength": 14}}
        mechanical_state = {"hp": 9, "custom": {"flag": True}}
        inventory = [{"id": "item-1", "name": "Rope"}]
        resources = {"custom_resource": 2}
        scene = {"location": "Old bridge", "weather": "rain"}

        result = build_rule_state(
            campaign_id="campaign-123",
            player_input="Eu tento abrir a porta.",
            intent_classification="mechanical_likely",
            character=character,
            mechanical_state=mechanical_state,
            inventory=inventory,
            resources=resources,
            scene=scene,
        )

        self.assertEqual(result["schema_version"], RULE_STATE_SCHEMA_VERSION)
        self.assertEqual(result["campaign_id"], "campaign-123")
        self.assertEqual(result["character"], character)
        self.assertEqual(result["mechanical_state"], mechanical_state)
        self.assertIsInstance(result["mechanical_state"], dict)
        self.assertEqual(result["inventory"], inventory)
        self.assertEqual(result["resources"], resources)
        self.assertEqual(result["scene"], scene)
        self.assertEqual(
            result["intent"],
            {
                "classification": "mechanical_likely",
                "player_input": "Eu tento abrir a porta.",
            },
        )
        self.assertNotIn("status", result["intent"])
        self.assertNotIn("outcome", result["intent"])

    def test_none_fields_use_only_the_specified_empty_defaults(self):
        result = build_rule_state(
            campaign_id="campaign-empty",
            player_input="Converso com a guarda.",
            intent_classification="narrative_or_unknown",
            character=None,
            mechanical_state={},
            inventory=None,
            resources=None,
            scene=None,
        )

        self.assertEqual(result["character"], {})
        self.assertEqual(result["mechanical_state"], {})
        self.assertEqual(result["inventory"], [])
        self.assertEqual(result["resources"], {})
        self.assertEqual(result["scene"], {})
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "campaign_id",
                "character",
                "mechanical_state",
                "inventory",
                "resources",
                "scene",
                "intent",
            },
        )
        self.assertNotIn("hp", result["mechanical_state"])
        self.assertNotIn("available_actions", result)

    def test_rule_state_schema_version_is_stable(self):
        self.assertEqual(RULE_STATE_SCHEMA_VERSION, "mj-rule-state-v1")

    def test_non_object_mechanical_state_is_rejected(self):
        with self.assertRaises(TypeError):
            build_rule_state(
                campaign_id="campaign-123",
                player_input="Eu observo a sala.",
                intent_classification="narrative_or_unknown",
                character=None,
                mechanical_state=None,
                inventory=None,
                resources=None,
                scene=None,
            )


class FailClosedPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_unresolved_outer_status_discards_embedded_state_changes(self):
        campaign = {
            "id": "campaign-123",
            "name": "Test campaign",
            "character": {"name": "Ari"},
            "scene": {"location": "Old bridge"},
            "mechanical_state": {"hp": 9},
            "inventory": [{"id": "item-1"}],
            "resources": {"custom_resource": 2},
            "history": [],
        }
        snapshots = []
        rules = SimpleNamespace(
            resolve=AsyncMock(
                return_value={
                    "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                    "status": "needs_rule_validation",
                    "facts_resolvidos": {
                        "status": "resolved",
                        "state_changes": [{"key": "hp", "value": 0}],
                    },
                }
            )
        )
        mimo = SimpleNamespace(narrate=AsyncMock(return_value="A tentativa ainda não foi resolvida."))

        with (
            patch.object(turn_service, "get", return_value=campaign),
            patch.object(turn_service, "save", side_effect=lambda value: snapshots.append(copy.deepcopy(value))),
            patch.object(turn_service, "rules", rules),
            patch.object(turn_service, "mimo", mimo),
        ):
            result_campaign, facts, _narrative, status, _turn_id, _feedback = await turn_service.process_turn(
                "campaign-123", "Eu ataco o alvo."
            )

        self.assertEqual(status, "needs_rule_validation")
        self.assertEqual(facts, {})
        self.assertEqual(result_campaign["mechanical_state"], {"hp": 9})
        self.assertEqual(snapshots[0]["mechanical_state"], {"hp": 9})
        sent_state = rules.resolve.await_args.args[1]
        self.assertEqual(sent_state["schema_version"], "mj-rule-state-v1")
        self.assertEqual(sent_state["character"], {"name": "Ari"})
        self.assertEqual(sent_state["inventory"], [{"id": "item-1"}])
        self.assertEqual(sent_state["resources"], {"custom_resource": 2})
        self.assertEqual(sent_state["scene"], {"location": "Old bridge"})
        self.assertEqual(sent_state["mechanical_state"], {"hp": 9})
        self.assertEqual(sent_state["intent"]["classification"], "mechanical_likely")
        self.assertEqual(sent_state["intent"]["player_input"], "Eu ataco o alvo.")
        mimo.narrate.assert_awaited_once()
        narrator_input = mimo.narrate.await_args.args[0]
        self.assertEqual(narrator_input.campaign.campaign_id, "campaign-123")
        self.assertEqual(narrator_input.scene, {"location": "Old bridge"})
        self.assertEqual(narrator_input.player_input, "Eu ataco o alvo.")
        self.assertEqual(narrator_input.resolved_facts, {})
        self.assertEqual(narrator_input.ux_context, {})


if __name__ == "__main__":
    unittest.main()
