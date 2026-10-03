from fastapi import APIRouter, HTTPException

from app.models import RuleSearchRequest
from app.services.errors import ExternalServiceError
from app.services.rule_engine_client import RuleEngineClient


router = APIRouter(prefix="/v1/rules", tags=["rules"])
client = RuleEngineClient()


@router.post("/search")
async def search(body: RuleSearchRequest):
    try:
        return await client.search(body.query, body.limit)
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_error", "service": exc.service, "operation": exc.operation},
        ) from exc
