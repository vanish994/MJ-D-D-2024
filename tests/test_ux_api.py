import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import turn_service
from app.services.campaign_service import get, save


class UXApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_file = Path(self.temp_dir.name) / "campaigns.db"
        self.storage_settings = replace(settings, database_url=f"sqlite:///{db_file}")
        self.settings_patch = patch("app.storage.db.settings", self.storage_settings)
        self.settings_patch.start()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.settings_patch.stop()
        self.temp_dir.cleanup()

    def _campaign_id(self):
        response = self.client.post("/v1/campaigns", json={"name": "Campanha UX"})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_assistant_without_engine_snapshot_reports_unknown_not_empty_state(self):
        campaign_id = self._campaign_id()
        response = self.client.get(f"/v1/campaigns/{campaign_id}/assistant")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "unavailable")
        self.assertEqual(data["currentness"], "unknown")
        self.assertIsNone(data["available_actions"])
        self.assertIsNone(data["turn_resources"])
        self.assertEqual(data["explanation_mode"], "beginner")

    def test_mode_can_be_changed_without_touching_mechanical_state(self):
        campaign_id = self._campaign_id()
        response = self.client.patch(
            f"/v1/campaigns/{campaign_id}/ux-settings",
            json={"explanation_mode": "advanced"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ux_settings"]["explanation_mode"], "advanced")
        campaign = get(campaign_id)
        self.assertEqual(campaign["mechanical_state"], {})

    def test_assistant_uses_only_latest_resolved_current_engine_snapshot(self):
        campaign_id = self._campaign_id()
        campaign = get(campaign_id)
        campaign["history"].append({
            "created_at": "2026-10-03T00:00:00+00:00",
            "resolution_status": "resolved",
            "facts_resolvidos": {
                "status": "resolved",
                "ux_snapshot": {
                    "current": True,
                    "resolution_id": "resolution-test",
                    "turn_resources": {"action": True, "movement_remaining": 5, "movement_unit": "ft"},
                    "available_actions": [{"name": "Atacar", "cost": "Ação"}],
                },
            },
        })
        save(campaign)
        response = self.client.get(f"/v1/campaigns/{campaign_id}/assistant")
        data = response.json()
        self.assertEqual(data["status"], "available")
        self.assertEqual(data["resolution_id"], "resolution-test")
        self.assertEqual(data["available_actions"], [{"name": "Atacar", "cost": "Ação"}])
        self.assertEqual(data["turn_resources"]["movement_remaining"], 5)

    def test_later_unresolved_attempt_invalidates_old_action_menu(self):
        campaign_id = self._campaign_id()
        campaign = get(campaign_id)
        campaign["history"].extend([
            {"resolution_status": "resolved", "facts_resolvidos": {"ux_snapshot": {
                "current": True,
                "available_actions": [{"name": "Atacar", "cost": "Ação"}],
            }}},
            {"resolution_status": "needs_rule_validation", "facts_resolvidos": {}},
        ])
        save(campaign)
        data = self.client.get(f"/v1/campaigns/{campaign_id}/assistant").json()
        self.assertEqual(data["status"], "unavailable")
        self.assertIsNone(data["available_actions"])

    def test_invalid_action_reason_is_returned_from_engine_and_facts_stay_empty(self):
        campaign_id = self._campaign_id()
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value={
            "status": "invalid_action",
            "reason": "A Ação Bônus já foi utilizada neste turno.",
        }))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="A cena continua."))
        with (
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            response = self.client.post(
                f"/v1/campaigns/{campaign_id}/turn",
                json={"player_input": "Eu tento conjurar uma magia."},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["facts_resolvidos"], {})
        self.assertEqual(data["rule_feedback"]["message"], "A Ação Bônus já foi utilizada neste turno.")
        self.assertEqual(data["campaign"]["mechanical_state"], {})
        self.assertEqual(fake_mimo.narrate.await_args.args[-1], {})

    def test_long_rest_summary_comes_only_from_resolved_engine_payload(self):
        campaign_id = self._campaign_id()
        summary = {
            "hp_before": 4,
            "hp_after": 9,
            "hp_max": 9,
            "resources_recovered": [{"name": "resource-from-engine", "amount": 1}],
            "effects_ended": [{"name": "effect-ended-by-engine"}],
            "effects_continuing": [{"name": "effect-kept-by-engine"}],
        }
        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value={
            "status": "resolved",
            "facts_resolvidos": {
                "status": "resolved",
                "action": "long_rest",
                "long_rest_summary": summary,
            },
        }))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="A noite termina."))
        with (
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            response = self.client.post(
                f"/v1/campaigns/{campaign_id}/turn",
                json={"player_input": "Faço um descanso longo."},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["long_rest_summary"], summary)


if __name__ == "__main__":
    unittest.main()
