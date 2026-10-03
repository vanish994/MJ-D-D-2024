import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.errors import ExternalServiceError
from app.services import turn_service


def resolved_response():
    return {
        "status": "resolved",
        "facts_resolvidos": {
            "resolution_id": "res-test-1",
            "status": "resolved",
            "action": "attack_roll",
            "outcome": "hit",
            "rolls": [{"formula": "1d20", "dice": [{"sides": 20, "result": 17}], "modifier": 3, "total": 20}],
            "damage": None,
            "conditions_applied": [],
            "state_changes": [{"key": "hp", "value": 7}],
            "rules_used": ["rule-ref-test"],
        },
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
        fake_mimo.narrate.assert_awaited_once_with(
            "campaign-test", {}, "Eu tento atacar o guardião.", {}
        )
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
        self.assertEqual(fake_mimo.narrate.await_args.args[-1], facts)
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
        self.assertEqual(fake_mimo.narrate.await_args.args[-1], {})

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

    async def test_narrative_only_turn_calls_rule_engine_before_mimo(self):
        events = []

        async def resolve(_action, _state):
            events.append("rule_engine")
            return {"status": "narrative_only"}

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
            "Converso com o mercador sobre a viagem.", {"hp": 10}
        )
        self.assertEqual(events, ["rule_engine", "mimo"])
        self.assertEqual(facts, {})
        self.assertEqual(status, "narrative_only")
        self.assertIsNone(feedback)
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
