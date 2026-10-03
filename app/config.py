import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    rule_engine_url: str = os.getenv("RULE_ENGINE_URL", "http://localhost:8001").rstrip("/")
    rule_engine_api_key: str = os.getenv("RULE_ENGINE_API_KEY", "")
    mimo_url: str = os.getenv("MIMO_URL", "http://localhost:3000").rstrip("/")
    mimo_api_key: str = os.getenv("MIMO_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/campaigns.db")
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://localhost:3000")
    port: int = int(os.getenv("PORT", "8000"))

    @property
    def cors_origins(self) -> tuple[str, ...]:
        origins = tuple(item.strip() for item in self.cors_origin.split(",") if item.strip())
        return origins or ("http://localhost:3000",)


settings = Settings()
