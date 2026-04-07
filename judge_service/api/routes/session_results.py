from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Query, Request

from api.schemas import SessionResultResponse
from api.services.session_results import run_session_results

logger = logging.getLogger(__name__)

router = APIRouter(tags=["session-results"])


@router.get("/session-results", response_model=SessionResultResponse)
async def get_session_results(
    request: Request,
    session_id: str | None = Query(default=None),
    room_name: str | None = Query(default=None),
    refresh: bool = Query(
        default=False,
        description="If true, re-run LLM judge even when judge_results exists.",
    ),
) -> SessionResultResponse:
    database = request.app.state.database
    judge = request.app.state.judge
    t0 = time.perf_counter()
    logger.info(
        "GET /api/session-results session_id=%s room_name=%s refresh=%s",
        session_id,
        room_name,
        refresh,
    )
    try:
        out = await run_session_results(
            database,
            judge,
            session_id=session_id,
            room_name=room_name,
            refresh=refresh,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        jr = out.judge_result
        total = jr.total_score if jr is not None else None
        logger.info(
            "GET /api/session-results done in %.0fms session_id=%s total_score=%s",
            elapsed_ms,
            out.session.session_id,
            total,
        )
        return out
    except ValueError as exc:
        logger.warning("GET /api/session-results 400: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        logger.warning("GET /api/session-results 404: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
