import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.errors import ExternalServiceError
from app.services import turn_service
from app.services.resolution_contract import RULE_RESOLUTION_SCHEMA_VERSION
from app.services.turn_contract import build_rule_state


def resolved_response():
    return {
        "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
        "resolution_id": "res-test-1",
        "status": "resolved",
        "action": {"type": "attack_roll", "actor_id": "character-test"},
        "check": {"ability": "strength", "dc": 15, "modifier": 3},
        "rolls": [{"type": "d20", "result": 17}],
        "outcome": {"success": True, "total": 20},
        "facts_resolvidos": {
            "resolution_id": "res-test-1",
            "status": "resolved",
            "state_changes": [{"key": "hp", "value": 7}],
            "rules_used": ["rule-ref-test"],
        },
        "state_changes": {"hp": 7},
        "rules_used": ["rule-ref-test"],
    }


class TurnServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.campaign = {
            "id": "campaign-test",
            "name": "Teste",
            "character": {},
            "scene": {},
            "mechanical_state": {"hp": 10},
            "inventory": [],
            "resources": {},
            "history": [],
        }
        self.snapshots = []

    def _save_snapshot(self, campaign):
        self.snapshots.append(copy.deepcopy(campaign))
        return campaign

    async def test_unresolved_mechanical_action_sends_empty_facts_to_narrator(self):
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value={"status": "needs_rule_validation"}))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="A cena continua em suspense."))
        with (
            patch.object(turn_service, "get", return_value=self.campaign),
            patch.object(turn_service, "save", side_effect=self._save_snapshot),
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            campaign, facts, narrative, status, turn_id, feedback = await turn_service.process_turn(
                "campaign-test", "Eu tento atacar o guardião."
            )

        self.assertEqual(facts, {})
        self.assertEqual(status, "needs_rule_validation")
        self.assertEqual(feedback["type"], "rule_validation")
        self.assertEqual(campaign["mechanical_state"], {"hp": 10})
        fake_mimo.narrate.assert_awaited_once()
        narrator_input = fake_mimo.narrate.await_args.args[0]
        self.assertEqual(narrator_input.schema_version, "narrator-input-v1")
        self.assertEqual(narrator_input.campaign.campaign_id, "campaign-test")
        self.assertEqual(narrator_input.player_input, "Eu tento atacar o guardião.")
        self.assertEqual(narrator_input.resolved_facts, {})
        self.assertEqual(narrative, "A cena continua em suspense.")
        self.assertTrue(turn_id)
        self.assertEqual(self.snapshots[0]["history"][0]["narrative_status"], "pending")
        self.assertEqual(self.snapshots[-1]["history"][0]["narrative_status"], "completed")

    async def test_only_explicitly_resolved_facts_apply_state_changes(self):
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value=resolved_response()))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="O resultado confirmado altera a cena."))
        with (
            patch.object(turn_service, "get", return_value=self.campaign),
            patch.object(turn_service, "save", side_effect=self._save_snapshot),
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            campaign, facts, _narrative, status, _turn_id, feedback = await turn_service.process_turn(
                "campaign-test", "Eu ataco o guardião."
            )

        self.assertEqual(status, "resolved")
        self.assertIsNone(feedback)
        self.assertEqual(facts["status"], "resolved")
        self.assertEqual(campaign["mechanical_state"]["hp"], 7)
        self.assertEqual(campaign["history"][0]["facts_resolvidos"], facts)
        self.assertEqual(fake_mimo.narrate.await_args.args[0].resolved_facts, facts)
        self.assertEqual(self.snapshots[0]["mechanical_state"]["hp"], 7)

    async def test_malformed_or_unresolved_nested_facts_fail_closed(self):
        response = resolved_response()
        response["facts_resolvidos"]["status"] = "needs_rule_validation"
        response["facts_resolvidos"]["state_changes"] = [{"key": "hp", "value": 1}]
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value=response))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="A tentativa permanece indefinida."))
        with (
            patch.object(turn_service, "get", return_value=self.campaign),
            patch.object(turn_service, "save", side_effect=self._save_snapshot),
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            campaign, facts, _narrative, status, _turn_id, _feedback = await turn_service.process_turn(
                "campaign-test", "Eu rolo para atacar."
            )
        self.assertEqual(facts, {})
        self.assertEqual(status, "needs_rule_validation")
        self.assertEqual(campaign["mechanical_state"]["hp"], 10)
        self.assertEqual(fake_mimo.narrate.await_args.args[0].resolved_facts, {})

    async def test_bad_state_change_key_rejects_the_entire_facts_object(self):
        response = resolved_response()
        response["facts_resolvidos"]["state_changes"] = [{"key": "hp.value", "value": 1}]
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value=response))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="A tentativa permanece indefinida."))
        with (
            patch.object(turn_service, "get", return_value=self.campaign),
            patch.object(turn_service, "save", side_effect=self._save_snapshot),
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            campaign, facts, _narrative, status, _turn_id, _feedback = await turn_service.process_turn(
                "campaign-test", "Eu ataco."
            )
        self.assertEqual(facts, {})
        self.assertEqual(status, "needs_rule_validation")
        self.assertEqual(campaign["mechanical_state"]["hp"], 10)

    async def test_dialogue_turn_calls_rule_engine_before_mimo(self):
        events = []

        async def resolve(_action, _state):
            events.append("rule_engine")
            return {
                "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                "status": "awaiting_input",
            }

        async def narrate(*_args):
            events.append("mimo")
            return "O mercador sorri."

        fake_rules = SimpleNamespace(resolve=AsyncMock(side_effect=resolve))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(side_effect=narrate))
        with (
            patch.object(turn_service, "get", return_value=self.campaign),
            patch.object(turn_service, "save", side_effect=self._save_snapshot),
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            campaign, facts, _narrative, status, _turn_id, feedback = await turn_service.process_turn(
                "campaign-test", "Converso com o mercador sobre a viagem."
            )
        fake_rules.resolve.assert_awaited_once_with(
            "Converso com o mercador sobre a viagem.",
            build_rule_state(
                campaign_id="campaign-test",
                player_input="Converso com o mercador sobre a viagem.",
                intent_classification="narrative_or_unknown",
                character={},
                mechanical_state={"hp": 10},
                inventory=[],
                resources={},
                scene={},
            ),
        )
        self.assertEqual(events, ["rule_engine", "mimo"])
        self.assertEqual(facts, {})
        self.assertEqual(status, "awaiting_input")
        self.assertEqual(feedback["status"], "awaiting_input")
        self.assertEqual(
            campaign["history"][0]["intent_classification"], "narrative_or_unknown"
        )

    async def test_mimo_failure_keeps_a_failed_turn_record(self):
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value={"status": "needs_rule_validation"}))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(side_effect=ExternalServiceError("mimo_proxy", "narration")))
        with (
            patch.object(turn_service, "get", return_value=self.campaign),
            patch.object(turn_service, "save", side_effect=self._save_snapshot),
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            with self.assertRaises(ExternalServiceError):
                await turn_service.process_turn("campaign-test", "Eu tento atacar.")
        self.assertEqual(self.snapshots[0]["history"][0]["narrative_status"], "pending")
        self.assertEqual(self.snapshots[-1]["history"][0]["narrative_status"], "failed")

    def test_intent_classifier_normalizes_accents_and_word_boundaries(self):
        self.assertEqual(turn_service.classify_intent("Faço um teste de Percepção"), "mechanical_likely")
        self.assertEqual(turn_service.classify_intent("Eu rolo iniciativa"), "mechanical_likely")
        self.assertEqual(turn_service.classify_intent("Converso com o mercador"), "narrative_or_unknown")
        self.assertEqual(turn_service.classify_intent("O atacante viajou"), "narrative_or_unknown")
        self.assertEqual(turn_service.classify_intent("Converso com o mercador"), "narrative_or_unknown")


if __name__ == "__main__":
    unittest.main()
