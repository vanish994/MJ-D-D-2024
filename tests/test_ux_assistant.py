import unittest

from app.services.turn_service import _rule_feedback
from app.services.resolution_contract import ValidatedResolution
from app.services.ux_assistant import format_long_rest_summary, project_combat_ux


class UXAssistantTests(unittest.TestCase):
    def test_action_available_comes_only_from_current_snapshot(self):
        result = project_combat_ux({
            "current": True,
            "turn_resources": {"action": True},
            "available_actions": [{"name": "Atacar", "cost": "Ação", "explanation": "Descrição do Rule Engine."}],
        })
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["available_actions"][0]["name"], "Atacar")
        self.assertEqual(result["available_actions"][0]["cost"], "Ação")
        self.assertEqual(result["available_actions"][0]["explanation"], "Descrição do Rule Engine.")

    def test_action_unavailable_warning_comes_from_explicit_false(self):
        result = project_combat_ux({"current": True, "turn_resources": {"action": False}})
        warning = next(item for item in result["warnings"] if item["resource"] == "action")
        self.assertFalse(warning["available"])
        self.assertIn("já utilizou", warning["message"])
        self.assertIsNone(result["available_actions"])

    def test_bonus_action_available_warning(self):
        result = project_combat_ux({"current": True, "turn_resources": {"bonus_action": True}})
        warning = next(item for item in result["warnings"] if item["resource"] == "bonus_action")
        self.assertTrue(warning["available"])
        self.assertIn("Ação Bônus", warning["message"])

    def test_bonus_action_unavailable_warning(self):
        result = project_combat_ux({"current": True, "turn_resources": {"bonus_action": False}})
        warning = next(item for item in result["warnings"] if item["resource"] == "bonus_action")
        self.assertFalse(warning["available"])

    def test_reaction_available_warning(self):
        result = project_combat_ux({"current": True, "turn_resources": {"reaction": True}})
        warning = next(item for item in result["warnings"] if item["resource"] == "reaction")
        self.assertTrue(warning["available"])
        self.assertIn("Reação", warning["message"])

    def test_reaction_unavailable_warning(self):
        result = project_combat_ux({"current": True, "turn_resources": {"reaction": False}})
        warning = next(item for item in result["warnings"] if item["resource"] == "reaction")
        self.assertFalse(warning["available"])
        self.assertIn("já utilizou", warning["message"])

    def test_movement_uses_only_the_reported_amount_and_unit(self):
        result = project_combat_ux({
            "current": True,
            "turn_resources": {"movement_remaining": 12, "movement_unit": "ft"},
        })
        warning = next(item for item in result["warnings"] if item["resource"] == "movement_remaining")
        self.assertEqual(warning["value"], 12)
        self.assertEqual(warning["unit"], "ft")
        self.assertEqual(warning["message"], "Movimento restante: 12 ft.")

    def test_invalid_action_message_is_only_the_rule_engine_reason(self):
        feedback = _rule_feedback(
            ValidatedResolution(
                status="invalid_action",
                narrator_facts={},
                state_changes={},
                reason="A Ação Bônus já foi utilizada.",
            ),
        )
        self.assertEqual(feedback, {
            "type": "invalid_action",
            "status": "invalid_action",
            "message": "A Ação Bônus já foi utilizada.",
        })

    def test_long_rest_resources_are_not_recomputed(self):
        source = {"resources_recovered": [{"name": " recurso informado ", "amount": 2}]}
        self.assertEqual(format_long_rest_summary(source), source)

    def test_long_rest_effects_ended_are_passed_through(self):
        source = {"effects_ended": [{"name": "efeito informado", "duration": "engine"}]}
        self.assertEqual(format_long_rest_summary(source), source)

    def test_long_rest_effects_continuing_are_passed_through(self):
        source = {"effects_continuing": [{"name": "efeito contínuo", "remaining": "engine"}]}
        self.assertEqual(format_long_rest_summary(source), source)

    def test_what_can_i_do_returns_only_explicit_available_options(self):
        options = [{"name": "Esquivar", "cost": "Ação"}]
        result = project_combat_ux({"current": True, "available_actions": options})
        self.assertEqual(result["available_actions"], options)
        self.assertIsNone(result["available_bonus_actions"])
        self.assertIsNone(result["available_reactions"])

    def test_unknown_or_not_current_snapshot_never_shows_options(self):
        self.assertIsNone(project_combat_ux(None)["available_actions"])
        stale = project_combat_ux({
            "current": False,
            "available_actions": [{"name": "Atacar", "cost": "Ação"}],
        })
        self.assertEqual(stale["status"], "unavailable")
        self.assertIsNone(stale["available_actions"])

    def test_missing_mechanics_are_not_filled_with_defaults(self):
        result = project_combat_ux({"current": True})
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["hp_current"])
        self.assertIsNone(result["turn_resources"])
        self.assertIsNone(result["available_actions"])
        self.assertEqual(result["warnings"], [])

    def test_advanced_mode_hides_explanation_but_keeps_engine_cost(self):
        result = project_combat_ux({
            "current": True,
            "available_actions": [{"name": "Atacar", "cost": "Ação", "explanation": "texto do Rule Engine"}],
        }, mode="advanced")
        self.assertEqual(result["available_actions"], [{"name": "Atacar", "cost": "Ação"}])

    def test_invalid_snapshot_is_rejected_without_fabricating_actions(self):
        result = project_combat_ux({"current": True, "available_actions": [{"cost": "Ação"}]})
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["available_actions"])


if __name__ == "__main__":
    unittest.main()
