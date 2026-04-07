from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import Database
from api.routes import health, session_results
from judge import LLMJudge

logger = logging.getLogger(__name__)


def _redact_database_url(url: str) -> str:
    """Hide password in postgresql://user:pass@host for logs."""
    if "://" not in url or "@" not in url:
        return url
    try:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            creds, hostpart = rest.rsplit("@", 1)
            if ":" in creds:
                user, _ = creds.split(":", 1)
                return f"{scheme}://{user}:***@{hostpart}"
    except ValueError:
        pass
    return url


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db_url = os.getenv("DATABASE_URL", "(default localhost)")
    logger.info(
        "Startup: DATABASE_URL=%s KNOWLEDGE_RAG=%s",
        _redact_database_url(db_url) if db_url != "(default localhost)" else db_url,
        os.getenv("KNOWLEDGE_RAG", "1"),
    )
    database = Database()
    await database.initialize()
    app.state.database = database
    logger.info("Database pool ready")
    app.state.judge = LLMJudge()
    logger.info("LLMJudge initialized; API ready")
    yield
    logger.info("Shutdown: closing database pool")
    await database.close()
    app.state.judge = None
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Judge Service (new)",
        description="Dummy judge API for frontend integration",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(session_results.router, prefix="/api")

    return app


__all__ = ["create_app"]
