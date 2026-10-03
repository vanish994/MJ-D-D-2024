import unittest
from dataclasses import replace

import httpx
from unittest.mock import patch

from app.config import settings
from app.services.errors import ExternalServiceError
from app.services.mimo_client import MimoClient
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
        with patch("app.services.mimo_client.settings", config):
            response = await client.narrate("campaign-x", {}, "Eu tento abrir a porta", {})

        self.assertEqual(response, "A cena segue sem afirmar resultado mecânico.")
        self.assertEqual(observed["url"], "https://mimo.example.test/v1/chat/completions")
        self.assertEqual(observed["headers"]["Authorization"], "Bearer mock-mimo-key")
        self.assertEqual(observed["json"]["model"], "mimo-v2.5-no-thinking")
        self.assertFalse(observed["json"]["stream"])
        user_content = observed["json"]["messages"][1]["content"]
        self.assertIn('"FATOS_RESOLVIDOS": {}', user_content)

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
