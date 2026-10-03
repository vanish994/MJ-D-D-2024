import unittest

from app.services.resolution_contract import (
    RULE_RESOLUTION_SCHEMA_VERSION,
    ResolutionContractError,
    validate_resolution_response,
)


class ResolutionContractTests(unittest.TestCase):
    def resolved_payload(self):
        return {
            "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
            "resolution_id": "res_123",
            "status": "resolved",
            "action": {"type": "ability_check", "actor_id": "character_001"},
            "request": {"player_input": "Eu tento abrir a porta."},
            "check": {"ability": "strength", "skill": None, "dc": 15, "modifier": 3},
            "rolls": [{"type": "d20", "result": 14}],
            "outcome": {"success": True, "total": 17},
            "facts_resolvidos": {},
            "state_changes": {},
            "rules_used": [],
            "ux_snapshot": {},
            "long_rest_summary": None,
        }

    def test_all_supported_statuses_are_accepted(self):
        statuses = (
            "needs_rule_validation",
            "awaiting_input",
            "awaiting_roll",
            "resolved",
            "invalid_action",
            "rule_not_found",
        )
        for status in statuses:
            with self.subTest(status=status):
                payload = self.resolved_payload() if status == "resolved" else {
                    "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                    "status": status,
                }
                payload["status"] = status
                result = validate_resolution_response(payload)
                self.assertEqual(result.status, status)
                if status != "resolved":
                    self.assertEqual(result.narrator_facts, {})
                    self.assertEqual(result.state_changes, {})

    def test_resolved_payload_validates_and_projects_only_contract_fields(self):
        result = validate_resolution_response(self.resolved_payload())

        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.state_changes, {})
        self.assertEqual(result.narrator_facts["schema_version"], "rule-resolution-v1")
        self.assertEqual(result.narrator_facts["status"], "resolved")
        self.assertEqual(result.narrator_facts["action"], {
            "type": "ability_check",
            "actor_id": "character_001",
        })
        self.assertEqual(result.narrator_facts["check"]["dc"], 15)
        self.assertEqual(result.narrator_facts["rolls"], [{"type": "d20", "result": 14}])
        self.assertEqual(result.narrator_facts["outcome"], {"success": True, "total": 17})
        self.assertEqual(result.narrator_facts["state_changes"], {})
        self.assertEqual(result.narrator_facts["rules_used"], [])
        self.assertEqual(result.narrator_facts["ux_snapshot"], {})
        self.assertNotIn("request", result.narrator_facts)
        self.assertNotIn("long_rest_summary", result.narrator_facts)

    def test_ability_check_action_ability_is_preserved_in_rule_resolution_v1(self):
        payload = self.resolved_payload()
        payload["action"]["ability"] = "strength"

        result = validate_resolution_response(payload)

        self.assertEqual(result.narrator_facts["action"]["ability"], "strength")

    def test_awaiting_roll_does_not_require_outcome(self):
        result = validate_resolution_response(
            {
                "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                "status": "awaiting_roll",
                "action": {"type": "ability_check"},
                "check": {"ability": "strength", "dc": 15},
            }
        )
        self.assertEqual(result.status, "awaiting_roll")
        self.assertEqual(result.narrator_facts, {})
        self.assertEqual(result.state_changes, {})

    def test_legacy_minimal_needs_validation_response_is_supported(self):
        result = validate_resolution_response({"status": "needs_rule_validation"})
        self.assertEqual(result.status, "needs_rule_validation")
        self.assertEqual(result.narrator_facts, {})
        self.assertEqual(result.state_changes, {})

    def test_unversioned_needs_validation_with_state_changes_is_rejected(self):
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response({
                "status": "needs_rule_validation",
                "state_changes": {"hp": 1},
            })

    def test_unresolved_status_discards_embedded_facts_and_state_changes(self):
        result = validate_resolution_response({
            "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
            "status": "needs_rule_validation",
            "facts_resolvidos": {"status": "resolved", "outcome": "hit"},
            "state_changes": {"hp": 1},
            "rules_used": ["rule-1"],
            "ux_snapshot": {"current": True},
            "long_rest_summary": {"hp_after": 10},
        })
        self.assertEqual(result.narrator_facts, {})
        self.assertEqual(result.state_changes, {})

    def test_legacy_facts_state_changes_are_normalized_only_when_resolved(self):
        result = validate_resolution_response({
            "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
            "status": "resolved",
            "facts_resolvidos": {
                "status": "resolved",
                "state_changes": [{"key": "hp", "value": 5}],
            },
        })
        self.assertEqual(result.state_changes, {"hp": 5})
        self.assertEqual(result.narrator_facts["state_changes"], {"hp": 5})

    def test_current_outer_and_legacy_nested_state_changes_must_not_conflict(self):
        payload = self.resolved_payload()
        payload["state_changes"] = {"hp": 5}
        payload["facts_resolvidos"] = {
            "status": "resolved",
            "state_changes": [{"key": "hp", "value": 4}],
        }
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response(payload)

    def test_uppercase_legacy_fatos_alias_is_accepted_inside_resolved_response(self):
        payload = self.resolved_payload()
        payload.pop("facts_resolvidos")
        payload["FATOS_RESOLVIDOS"] = {"status": "resolved"}
        result = validate_resolution_response(payload)
        self.assertEqual(result.narrator_facts["action"]["type"], "ability_check")
        self.assertNotIn("facts_resolvidos", result.narrator_facts)

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response({
                "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                "status": "narrative_only",
            })

    def test_incorrect_schema_version_is_rejected(self):
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response({
                "schema_version": "rule-resolution-v0",
                "status": "needs_rule_validation",
            })

    def test_unversioned_resolved_response_is_rejected(self):
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response({"status": "resolved"})

    def test_type_errors_malformed_rolls_and_unexpected_fields_are_rejected(self):
        invalid_updates = (
            {"check": {"dc": "15"}},
            {"outcome": {"success": "true"}},
            {"rolls": [{"type": "d20"}]},
            {"rolls": [{"type": "d20", "result": "14"}]},
            {"rules_used": [3]},
            {"state_changes": {"hp": {"value": 5}}},
            {"state_changes": {"hp.value": 5}},
            {"ux_snapshot": {"unrecognized": True}},
            {"long_rest_summary": {"unrecognized": True}},
            {"unexpected": "not allowed"},
        )
        for update in invalid_updates:
            with self.subTest(update=update):
                payload = self.resolved_payload()
                payload.update(update)
                with self.assertRaises(ResolutionContractError):
                    validate_resolution_response(payload)

    def test_nested_facts_must_be_resolved_and_match_known_schema(self):
        for facts in (
            {"status": "needs_rule_validation", "state_changes": [{"key": "hp", "value": 1}]},
            {"status": "resolved", "unknown": "not allowed"},
            {"status": "resolved", "state_changes": [{"key": "hp.value", "value": 1}]},
            {"status": "resolved", "state_changes": [{"key": "hp", "value": [1]}]},
        ):
            with self.subTest(facts=facts):
                payload = self.resolved_payload()
                payload["facts_resolvidos"] = facts
                with self.assertRaises(ResolutionContractError):
                    validate_resolution_response(payload)

    def test_non_object_response_is_rejected(self):
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response(["status", "resolved"])

    def test_excessively_nested_response_is_rejected(self):
        nested = {}
        for _ in range(1100):
            nested = {"child": nested}
        with self.assertRaises(ResolutionContractError):
            validate_resolution_response({
                "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
                "status": "resolved",
                "facts_resolvidos": nested,
            })


if __name__ == "__main__":
    unittest.main()
