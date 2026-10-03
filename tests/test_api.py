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


class OrchestratorApiTests(unittest.TestCase):
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

    def test_health_and_campaign_create_get(self):
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["service"], "MJ-D-D-2024")

        created = self.client.post("/v1/campaigns", json={"name": "  A Jornada  ", "character": {"class": "Ranger"}})
        self.assertEqual(created.status_code, 201)
        data = created.json()
        self.assertEqual(data["name"], "A Jornada")
        self.assertTrue(data["id"])
        retrieved = self.client.get(f"/v1/campaigns/{data['id']}")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json()["character"]["class"], "Ranger")

    def test_unresolved_turn_returns_empty_facts_and_does_not_change_state(self):
        campaign_response = self.client.post("/v1/campaigns", json={"name": "Campanha"})
        campaign_id = campaign_response.json()["id"]
        campaign = get(campaign_id)
        campaign["mechanical_state"] = {"hp": 12}
        save(campaign)

        fake_rules = SimpleNamespace(resolve=AsyncMock(return_value={"status": "needs_rule_validation"}))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(return_value="A tentativa fica em aberto."))
        with (
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            response = self.client.post(
                f"/v1/campaigns/{campaign_id}/turn",
                json={"player_input": "Eu tento atacar o guardião.", "stream": False},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["facts_resolvidos"], {})
        self.assertEqual(result["resolution_status"], "needs_rule_validation")
        self.assertEqual(result["campaign"]["mechanical_state"], {"hp": 12})
        self.assertTrue(result["narrative"])
        self.assertEqual(fake_mimo.narrate.await_args.args[-1], {})

    def test_dialogue_turn_calls_rule_engine_before_mimo(self):
        campaign_id = self.client.post("/v1/campaigns", json={"name": "Campanha"}).json()["id"]
        events = []

        async def resolve(action, state):
            events.append("rule_engine")
            self.assertEqual(action, "Converso com o mercador.")
            self.assertEqual(state, {})
            return {"status": "narrative_only"}

        async def narrate(*args):
            events.append("mimo")
            self.assertEqual(args[-1], {})
            return "O mercador responde."

        fake_rules = SimpleNamespace(resolve=AsyncMock(side_effect=resolve))
        fake_mimo = SimpleNamespace(narrate=AsyncMock(side_effect=narrate))
        with (
            patch.object(turn_service, "rules", fake_rules),
            patch.object(turn_service, "mimo", fake_mimo),
        ):
            response = self.client.post(
                f"/v1/campaigns/{campaign_id}/turn",
                json={"player_input": "Converso com o mercador.", "stream": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(events, ["rule_engine", "mimo"])
        self.assertEqual(response.json()["facts_resolvidos"], {})
        self.assertEqual(response.json()["resolution_status"], "narrative_only")

    def test_stream_true_is_rejected_instead_of_silently_ignored(self):
        campaign_id = self.client.post("/v1/campaigns", json={"name": "Campanha"}).json()["id"]
        response = self.client.post(
            f"/v1/campaigns/{campaign_id}/turn",
            json={"player_input": "Converso com o mercador.", "stream": True},
        )
        self.assertEqual(response.status_code, 501)

    def test_missing_campaign_is_404(self):
        response = self.client.get("/v1/campaigns/not-a-campaign")
        self.assertEqual(response.status_code, 404)

    def test_search_route_uses_mocked_rule_engine(self):
        fake_client = SimpleNamespace(search=AsyncMock(return_value={"results": [], "count": 0}))
        with patch("app.api.rules.client", fake_client):
            response = self.client.post("/v1/rules/search", json={"query": "concentração", "limit": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": [], "count": 0})
        fake_client.search.assert_awaited_once_with("concentração", 3)


if __name__ == "__main__":
    unittest.main()
