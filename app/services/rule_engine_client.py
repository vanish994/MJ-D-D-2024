import httpx

from app.config import settings
from app.services.errors import ExternalServiceError


class RuleEngineClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def _post_json(self, path: str, payload: dict) -> dict:
        headers = {"X-API-Key": settings.rule_engine_api_key} if settings.rule_engine_api_key else {}
        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                response = await client.post(
                    f"{settings.rule_engine_url}{path}",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalServiceError("rule_engine", path) from exc
        if not isinstance(data, dict):
            raise ExternalServiceError("rule_engine", "invalid_response")
        return data

    async def resolve(
        self,
        action: str,
        state: dict,
        rule_ids: list[str] | None = None,
    ) -> dict:
        return await self._post_json(
            "/v1/resolve",
            {"action": action, "state": state, "rule_ids": rule_ids or []},
        )

    async def search(self, query: str, limit: int = 8) -> dict:
        if not 1 <= limit <= 30:
            raise ValueError("limit must be between 1 and 30")
        if not query.strip() or len(query) > 500:
            raise ValueError("query must contain 1 to 500 characters")
        return await self._post_json("/v1/rules/search", {"query": query, "limit": limit})
