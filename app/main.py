from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.campaigns import router as campaigns_router
from app.api.rules import router as rules_router
from app.api.turns import router as turns_router
from app.api.ux import router as ux_router
from app.config import settings
from app.storage.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="MJ-D-D-2024", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "MJ-D-D-2024"}


app.include_router(campaigns_router)
app.include_router(rules_router)
app.include_router(turns_router)
app.include_router(ux_router)
