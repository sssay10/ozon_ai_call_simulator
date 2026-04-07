from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "judge-service-new",
        "status": "running",
        "version": "0.1.0",
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "judge": "stub",
    }
