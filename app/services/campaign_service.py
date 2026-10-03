import json
from datetime import datetime, timezone
from typing import Any

from app.storage.db import database, init_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(campaign: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(campaign, dict) or not campaign.get("id"):
        raise ValueError("campaign must be an object with an id")
    now = _now()
    campaign.setdefault("created_at", now)
    campaign["updated_at"] = now
    encoded = json.dumps(campaign, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    with database() as con:
        con.execute(
            """
            INSERT INTO campaigns(id, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (campaign["id"], encoded, campaign["created_at"], campaign["updated_at"]),
        )
    return campaign


def get(campaign_id: str) -> dict[str, Any] | None:
    with database() as con:
        row = con.execute("SELECT data FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        return None
    value = json.loads(row["data"])
    if not isinstance(value, dict):
        raise ValueError("stored campaign data is not a JSON object")
    return value


__all__ = ["get", "init_db", "save"]
