import unittest
from dataclasses import replace
import json

import httpx
from unittest.mock import patch

from app.config import settings
from app.services.errors import ExternalServiceError
from app.services.mimo_client import MimoClient
from app.services.narrator_input import build_narrator_input
from app.services.resolution_contract import (
    RULE_RESOLUTION_SCHEMA_VERSION,
    ValidatedResolution,
    validate_resolution_response,
)
from app.services.rule_engine_client import RuleEngineClient


class ExternalClientMockTests(unittest.IsolatedAsyncioTestCase):
    async def test_rule_engine_resolve_request_contract_with_mock_transport(self):
        observed = {}

        async def handler(request):
            observed["url"] = str(request.url)
            observed["headers"] = request.headers
            observed["json"] = __import__("json").loads(request.content)
            return httpx.Response(200, json={"status": "needs_rule_validation"})

        config = replace(
            settings,
            rule_engine_url="https://rules.example.test",
            rule_engine_api_key="mock-rule-key",
        )
        client = RuleEngineClient(transport=httpx.MockTransport(handler))
        with patch("app.services.rule_engine_client.settings", config):
            result = await client.resolve(player_input="Eu tento atacar.", state={"hp": 10})

        self.assertEqual(result, {"status": "needs_rule_validation"})
        self.assertEqual(observed["url"], "https://rules.example.test/v1/resolve")
        self.assertEqual(observed["headers"]["X-API-Key"], "mock-rule-key")
        self.assertEqual(observed["json"], {
            "action": "Eu tento atacar.",
            "state": {"hp": 10},
            "rule_ids": [],
        })

    async def test_mimo_request_contract_and_empty_facts_with_mock_transport(self):
        observed = {}

        async def handler(request):
            observed["url"] = str(request.url)
            observed["headers"] = request.headers
            observed["json"] = __import__("json").loads(request.content)
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "A cena segue sem afirmar resultado mecânico."}}]
            })

        config = replace(settings, mimo_url="https://mimo.example.test", mimo_api_key="mock-mimo-key")
        client = MimoClient(transport=httpx.MockTransport(handler))
        narrator_input = build_narrator_input(
            {"id": "campaign-x", "scene": {"type": "exploration"}},
            "Eu tento abrir a porta",
            ValidatedResolution("needs_rule_validation", {}, {}),
        )
        with patch("app.services.mimo_client.settings", config):
            response = await client.narrate(narrator_input)

        self.assertEqual(response, "A cena segue sem afirmar resultado mecânico.")
        self.assertEqual(observed["url"], "https://mimo.example.test/v1/chat/completions")
        self.assertEqual(observed["headers"]["Authorization"], "Bearer mock-mimo-key")
        self.assertEqual(observed["json"]["model"], "mimo-v2.5-no-thinking")
        self.assertFalse(observed["json"]["stream"])
        user_content = observed["json"]["messages"][1]["content"]
        turn_data = json.loads(user_content.split("\n", 1)[1])
        self.assertEqual(turn_data["schema_version"], "narrator-input-v1")
        self.assertEqual(turn_data["campaign"], {"campaign_id": "campaign-x"})
        self.assertEqual(turn_data["player_input"], "Eu tento abrir a porta")
        self.assertEqual(turn_data["resolved_facts"], {})
        self.assertEqual(turn_data["FATOS_RESOLVIDOS"], {})
        self.assertNotIn("mechanical_state", turn_data)

    async def test_mimo_sends_only_validated_resolved_facts_and_exact_legacy_alias(self):
        observed = {}

        async def handler(request):
            observed["json"] = json.loads(request.content)
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "O guarda considera sua proposta."}}]
            })

        resolution = validate_resolution_response({
            "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
            "status": "resolved",
            "outcome": {"success": True, "total": 17},
        })
        narrator_input = build_narrator_input(
            {"id": "campaign-x"}, "Eu converso com o guarda.", resolution
        )
        config = replace(settings, mimo_url="https://mimo.example.test", mimo_api_key="")
        client = MimoClient(transport=httpx.MockTransport(handler))
        with patch("app.services.mimo_client.settings", config):
            await client.narrate(narrator_input)

        user_content = observed["json"]["messages"][1]["content"]
        turn_data = json.loads(user_content.split("\n", 1)[1])
        self.assertEqual(turn_data["resolved_facts"]["status"], "resolved")
        self.assertEqual(turn_data["resolved_facts"]["outcome"]["total"], 17)
        self.assertEqual(turn_data["FATOS_RESOLVIDOS"], turn_data["resolved_facts"])

    async def test_upstream_http_error_is_wrapped_without_body_or_secret(self):
        async def handler(_request):
            return httpx.Response(503, text="upstream internal details")

        config = replace(settings, rule_engine_url="https://rules.example.test")
        client = RuleEngineClient(transport=httpx.MockTransport(handler))
        with patch("app.services.rule_engine_client.settings", config):
            with self.assertRaises(ExternalServiceError) as caught:
                await client.resolve("x", {})
        self.assertEqual(caught.exception.service, "rule_engine")
        self.assertNotIn("upstream internal details", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
