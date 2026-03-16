"""
FastAPI application for judge service.
Evaluates training sessions using LLM and stores results in PostgreSQL.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from database import Database, DialogueSession, JudgeResult
from judge import LLMJudge
from scenarios import get_scenario_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Judge Service",
    description="Service for evaluating training sessions using LLM",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database = Database()
judge: LLMJudge | None = None


class JudgeSessionRequest(BaseModel):
    session_id: str | None = None
    room_name: str | None = None
    archetype: str | None = None
    difficulty: str | None = None
    product: str | None = None

    @model_validator(mode="after")
    def _require_identifier(self) -> "JudgeSessionRequest":
        if not self.session_id and not self.room_name:
            raise ValueError("Either session_id or room_name is required")
        return self


class TranscriptTurn(BaseModel):
    role: str
    text: str
    created_at: str | None = None


class SessionMetadataResponse(BaseModel):
    session_id: str
    room_name: str
    archetype: str
    difficulty: str
    product: str
    started_at: str | None = None
    ended_at: str | None = None


class JudgeResultResponse(BaseModel):
    scenario_id: str
    scores: dict[str, Any] = Field(default_factory=dict)
    total_score: float = 0.0
    critical_errors: list[str] = Field(default_factory=list)
    feedback_positive: list[str] = Field(default_factory=list)
    feedback_improvement: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    client_profile: dict[str, Any] = Field(default_factory=dict)
    relevant_criteria: list[str] = Field(default_factory=list)
    model_used: str = "unknown"
    judge_backend: str = "unknown"
    error: str | None = None
    details: str | None = None
    created_at: str | None = None


class SessionResultResponse(BaseModel):
    session: SessionMetadataResponse
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    judge_result: JudgeResultResponse | None = None


class SessionListItemResponse(BaseModel):
    session_id: str
    room_name: str
    archetype: str
    difficulty: str
    product: str
    owner_user_id: str
    started_at: str | None = None
    ended_at: str | None = None
    total_score: float | None = None
    judge_ready: bool = False
    scenario_id: str | None = None


class ActorContext(BaseModel):
    user_id: str
    role: str


def _difficulty_to_scenario_level(difficulty: str | None) -> str:
    return {
        "1": "easy",
        "2": "medium",
        "3": "hard",
        "4": "hard",
    }.get(str(difficulty or "1"), "easy")


def _archetype_to_scenario_archetype(archetype: str | None) -> str:
    # The current scenario pack is limited; map current UI archetypes to the closest known config.
    return {
        "novice": "novice_ip",
        "friendly": "novice_ip",
        "skeptic": "novice_ip",
        "busy_owner": "novice_ip",
    }.get(str(archetype or "novice"), "novice_ip")


def _resolve_scenario_id(
    archetype: str | None,
    difficulty: str | None,
    product: str | None,
) -> str:
    scenario_level = _difficulty_to_scenario_level(difficulty)
    scenario_archetype = _archetype_to_scenario_archetype(archetype)
    scenario_id = get_scenario_id(scenario_level, scenario_archetype)
    if scenario_id:
        return scenario_id

    # Fallback while the scenario catalog is still narrow / outdated.
    logger.warning(
        "No scenario mapping for archetype=%s difficulty=%s product=%s, using fallback",
        archetype,
        difficulty,
        product,
    )
    return "novice_ip_no_account_easy"


def _serialize_session(row: DialogueSession) -> SessionMetadataResponse:
    return SessionMetadataResponse(
        session_id=str(row.id),
        room_name=row.room_name,
        archetype=row.archetype,
        difficulty=row.difficulty,
        product=row.product,
        started_at=row.started_at.isoformat() if row.started_at else None,
        ended_at=row.ended_at.isoformat() if row.ended_at else None,
    )


def _serialize_judge_result(row: JudgeResult | None) -> JudgeResultResponse | None:
    if row is None:
        return None
    return JudgeResultResponse(
        scenario_id=row.scenario_id,
        scores=row.scores or {},
        total_score=row.total_score or 0.0,
        critical_errors=row.critical_errors or [],
        feedback_positive=row.feedback_positive or [],
        feedback_improvement=row.feedback_improvement or [],
        recommendations=row.recommendations or [],
        client_profile=row.client_profile or {},
        relevant_criteria=row.relevant_criteria or [],
        model_used=row.model_used or "unknown",
        judge_backend=row.judge_backend or "unknown",
        error=row.error,
        details=row.details,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


async def _resolve_session(
    session_id: str | None,
    room_name: str | None,
) -> DialogueSession:
    session_row = None
    if session_id:
        session_row = await database.get_session(session_id)
    elif room_name:
        session_row = await database.get_latest_session_by_room(room_name)

    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_row


async def _require_actor(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> ActorContext:
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=401, detail="Missing actor context")
    if x_user_role not in {"manager", "coach"}:
        raise HTTPException(status_code=403, detail="Invalid role")
    return ActorContext(user_id=x_user_id, role=x_user_role)


async def _resolve_session_for_actor(
    *,
    actor: ActorContext,
    session_id: str | None,
    room_name: str | None,
) -> DialogueSession:
    session_row = None
    if session_id:
        session_row = await database.get_session_for_actor(session_id, actor.user_id, actor.role)
    elif room_name:
        session_row = await database.get_latest_session_by_room_for_actor(room_name, actor.user_id, actor.role)

    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_row


@app.on_event("startup")
async def startup() -> None:
    global judge
    await database.initialize()

    llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()
    logger.info("Judge service: using LLM provider %s", llm_provider)
    if llm_provider == "ollama":
        logger.info(
            "Judge service: Ollama config base_url=%s model=%s",
            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            os.getenv("OLLAMA_MODEL", "qwen2:7b-instruct-q4_K_M"),
        )
    else:
        logger.info(
            "Judge service: OpenRouter config base_url=%s model=%s",
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        )
        if not os.getenv("OPENROUTER_API_KEY"):
            logger.warning("Judge service: OPENROUTER_API_KEY is not set")

    judge = LLMJudge()
    logger.info("Judge service started successfully")


@app.on_event("shutdown")
async def shutdown() -> None:
    await database.close()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "judge-service",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()
    judge_backend = getattr(judge, "backend_name", "unknown") if judge else "not initialized"
    return {
        "status": "healthy",
        "database": "connected" if database._initialized else "disconnected",
        "judge": "initialized" if judge is not None else "not initialized",
        "llm_provider": llm_provider,
        "judge_backend": judge_backend,
    }


@app.post("/api/judge-session", response_model=SessionResultResponse)
async def judge_session(request: JudgeSessionRequest) -> SessionResultResponse:
    session_row = await _resolve_session(request.session_id, request.room_name)
    transcript = await database.get_session_transcript(str(session_row.id))
    if not transcript:
        raise HTTPException(status_code=400, detail="Session has no transcript data")

    scenario_id = _resolve_scenario_id(
        archetype=request.archetype or session_row.archetype,
        difficulty=request.difficulty or session_row.difficulty,
        product=request.product or session_row.product,
    )
    logger.info(
        "Judging session %s room=%s archetype=%s difficulty=%s product=%s scenario_id=%s",
        session_row.id,
        session_row.room_name,
        request.archetype or session_row.archetype,
        request.difficulty or session_row.difficulty,
        request.product or session_row.product,
        scenario_id,
    )

    if judge is None:
        raise HTTPException(status_code=503, detail="Judge is not initialized")

    evaluation = judge.evaluate(transcript, scenario_id=scenario_id)
    judge_row = await database.save_judge_result(str(session_row.id), scenario_id, evaluation)

    return SessionResultResponse(
        session=_serialize_session(session_row),
        transcript=[TranscriptTurn(**turn) for turn in transcript],
        judge_result=_serialize_judge_result(judge_row),
    )


@app.get("/api/session-results", response_model=SessionResultResponse)
async def get_session_results(
    session_id: str | None = Query(default=None),
    room_name: str | None = Query(default=None),
    actor: ActorContext = Depends(_require_actor),
) -> SessionResultResponse:
    session_row = await _resolve_session_for_actor(actor=actor, session_id=session_id, room_name=room_name)
    transcript = await database.get_session_transcript(str(session_row.id))
    judge_row = await database.get_judge_result(str(session_row.id))
    return SessionResultResponse(
        session=_serialize_session(session_row),
        transcript=[TranscriptTurn(**turn) for turn in transcript],
        judge_result=_serialize_judge_result(judge_row),
    )


@app.get("/api/sessions", response_model=list[SessionListItemResponse])
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    actor: ActorContext = Depends(_require_actor),
) -> list[SessionListItemResponse]:
    rows = await database.list_sessions_for_actor(user_id=actor.user_id, role=actor.role, limit=limit)
    return [SessionListItemResponse(**row) for row in rows]
