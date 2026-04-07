from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import asyncpg

from judge.merged_evaluation import JudgeEvaluation

logger = logging.getLogger(__name__)


def _as_json_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_json_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _json_dumps_for_jsonb(value: Any) -> str:
    """asyncpg jsonb codec expects JSON text for some bind paths; dict/list must be serialized."""
    return json.dumps(value, default=str, ensure_ascii=False)


@dataclass(frozen=True)
class StoredJudgeEvaluation:
    evaluation: JudgeEvaluation
    updated_at: str
    created_at: str


class Database:
    def __init__(self) -> None:
        self._database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://dialogue:dialogue@localhost:5432/dialogues",
        )
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=10)
        logger.info("Database pool created (min=1 max=10)")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self._pool

    async def get_session_context(self, session_id: str) -> dict[str, Any] | None:
        """
        Return session metadata + linked training scenario text blocks.
        """
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    ds.id,
                    ds.room_name,
                    ds.product,
                    ds.started_at,
                    ds.ended_at,
                    ds.training_scenario_id,
                    ts.persona_description,
                    ts.scenario_description
                FROM dialogue_sessions ds
                LEFT JOIN training_scenarios ts
                    ON ts.id = ds.training_scenario_id
                WHERE ds.id = $1::uuid
                """,
                session_id,
            )
        if row is None:
            return None
        return {
            "session_id": str(row["id"]),
            "room_name": row["room_name"],
            "product": row["product"],
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
            "training_scenario_id": (
                str(row["training_scenario_id"]) if row["training_scenario_id"] else None
            ),
            "persona_description": row["persona_description"],
            "scenario_description": row["scenario_description"],
        }

    async def get_session_context_by_room_name(self, room_name: str) -> dict[str, Any] | None:
        """Resolve session by LiveKit room name (one row per call in practice)."""
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    ds.id,
                    ds.room_name,
                    ds.product,
                    ds.started_at,
                    ds.ended_at,
                    ds.training_scenario_id,
                    ts.persona_description,
                    ts.scenario_description
                FROM dialogue_sessions ds
                LEFT JOIN training_scenarios ts
                    ON ts.id = ds.training_scenario_id
                WHERE ds.room_name = $1
                ORDER BY ds.started_at DESC
                LIMIT 1
                """,
                room_name.strip(),
            )
        if row is None:
            return None
        return {
            "session_id": str(row["id"]),
            "room_name": row["room_name"],
            "product": row["product"],
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
            "training_scenario_id": (
                str(row["training_scenario_id"]) if row["training_scenario_id"] else None
            ),
            "persona_description": row["persona_description"],
            "scenario_description": row["scenario_description"],
        }

    async def get_training_scenario_id_by_name(self, name: str) -> str | None:
        """Resolve training_scenarios.id by unique name (seed data in init.sql)."""
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM training_scenarios WHERE name = $1",
                name.strip(),
            )
        if row is None:
            return None
        return str(row["id"])

    async def insert_session_with_messages(
        self,
        *,
        room_name: str,
        product: str,
        owner_user_id: str,
        training_scenario_id: str,
        messages: list[tuple[str, str]],
        job_id: str | None = None,
    ) -> str:
        """
        Insert dialogue_sessions + dialogue_messages in one transaction.
        messages: (role, content) with role 'user' (manager) or 'assistant' (client).
        Message order is preserved via monotonic created_at offsets.
        """
        if not messages:
            raise ValueError("messages must be non-empty")
        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                sid = await conn.fetchval(
                    """
                    INSERT INTO dialogue_sessions (
                        room_name, job_id, product, owner_user_id, training_scenario_id
                    )
                    VALUES ($1, $2, $3, $4::uuid, $5::uuid)
                    RETURNING id::text
                    """,
                    room_name,
                    job_id,
                    product,
                    owner_user_id,
                    training_scenario_id,
                )
                for i, (role, content) in enumerate(messages):
                    if role not in ("user", "assistant"):
                        raise ValueError(f"Invalid role {role!r}, expected user|assistant")
                    await conn.execute(
                        """
                        INSERT INTO dialogue_messages (session_id, role, content, created_at)
                        VALUES (
                            $1::uuid,
                            $2,
                            $3,
                            clock_timestamp() + ($4::bigint * interval '1 microsecond')
                        )
                        """,
                        sid,
                        role,
                        content,
                        i,
                    )
        return str(sid)

    async def get_session_transcript(self, session_id: str) -> list[dict[str, Any]]:
        """
        Return normalized transcript from dialogue_messages by session_id.
        """
        pool = self._require_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content, created_at
                FROM dialogue_messages
                WHERE session_id = $1::uuid
                ORDER BY created_at ASC
                """,
                session_id,
            )

        role_map = {"user": "manager", "assistant": "client"}
        transcript: list[dict[str, Any]] = []
        for row in rows:
            mapped_role = role_map.get(row["role"])
            if not mapped_role:
                continue
            transcript.append(
                {
                    "role": mapped_role,
                    "text": row["content"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
            )
        return transcript

    def _evaluation_from_judge_row(self, row: Any) -> JudgeEvaluation:
        """Rebuild evaluation when raw_result is empty or invalid."""
        scores = row["scores"]
        if not isinstance(scores, dict):
            scores = {}
        return JudgeEvaluation(
            scores=scores,
            criteria={"compliance": {}, "sales": {}, "knowledge": {}},
            total_score=float(row["total_score"] or 0.0),
            critical_errors=_as_json_list(row["critical_errors"]),
            feedback_positive=_as_json_list(row["feedback_positive"]),
            feedback_improvement=_as_json_list(row["feedback_improvement"]),
            recommendations=_as_json_list(row["recommendations"]),
            client_profile=_as_json_dict(row["client_profile"]),
            relevant_criteria=_as_json_list(row["relevant_criteria"]),
            model_used=str(row["model_used"] or "unknown"),
            error=row["error"],
            details=row["details"],
        )

    async def get_stored_judge_evaluation(self, session_id: str) -> StoredJudgeEvaluation | None:
        """
        If judge_results exists, return evaluation payload (prefer raw_result) and timestamps.
        Otherwise None.
        """
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT raw_result, updated_at, created_at, total_score, scores,
                       critical_errors, feedback_positive, feedback_improvement,
                       recommendations, client_profile, relevant_criteria, model_used,
                       error, details
                FROM judge_results
                WHERE session_id = $1::uuid
                """,
                session_id,
            )
        if row is None:
            logger.debug("get_stored_judge_evaluation: no row for session_id=%s", session_id)
            return None
        raw = row["raw_result"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = {}
        if isinstance(raw, dict) and raw:
            evaluation = JudgeEvaluation.model_validate(raw)
        else:
            evaluation = self._evaluation_from_judge_row(row)
        return StoredJudgeEvaluation(
            evaluation=evaluation,
            updated_at=row["updated_at"].isoformat(),
            created_at=row["created_at"].isoformat(),
        )

    async def upsert_judge_result(
        self,
        session_id: str,
        scenario_id: str,
        evaluation: JudgeEvaluation,
        *,
        judge_backend: str = "unknown",
    ) -> dict[str, str]:
        """
        Insert or update judge_results for a session. Returns created_at and updated_at (ISO UTC).
        """
        pool = self._require_pool()
        payload = evaluation.model_dump(mode="json")
        total_score = float(payload.get("total_score") or 0.0)
        scores = _as_json_dict(payload.get("scores"))
        critical_errors = _as_json_list(payload.get("critical_errors"))
        feedback_positive = _as_json_list(payload.get("feedback_positive"))
        feedback_improvement = _as_json_list(payload.get("feedback_improvement"))
        recommendations = _as_json_list(payload.get("recommendations"))
        client_profile = _as_json_dict(payload.get("client_profile"))
        relevant_criteria = _as_json_list(payload.get("relevant_criteria"))
        model_used = str(payload.get("model_used") or "unknown")
        err = payload.get("error")
        error_text = str(err) if err is not None else None
        details_val = payload.get("details")
        details_text = str(details_val) if details_val is not None else None
        raw_result = payload

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO judge_results (
                    session_id, scenario_id, total_score, scores,
                    critical_errors, feedback_positive, feedback_improvement,
                    recommendations, client_profile, relevant_criteria,
                    model_used, judge_backend, error, details, raw_result
                )
                VALUES (
                    $1::uuid, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb,
                    $8::jsonb, $9::jsonb, $10::jsonb, $11, $12, $13, $14, $15::jsonb
                )
                ON CONFLICT (session_id) DO UPDATE SET
                    scenario_id = EXCLUDED.scenario_id,
                    total_score = EXCLUDED.total_score,
                    scores = EXCLUDED.scores,
                    critical_errors = EXCLUDED.critical_errors,
                    feedback_positive = EXCLUDED.feedback_positive,
                    feedback_improvement = EXCLUDED.feedback_improvement,
                    recommendations = EXCLUDED.recommendations,
                    client_profile = EXCLUDED.client_profile,
                    relevant_criteria = EXCLUDED.relevant_criteria,
                    model_used = EXCLUDED.model_used,
                    judge_backend = EXCLUDED.judge_backend,
                    error = EXCLUDED.error,
                    details = EXCLUDED.details,
                    raw_result = EXCLUDED.raw_result,
                    updated_at = now()
                RETURNING created_at, updated_at
                """,
                session_id,
                scenario_id,
                total_score,
                _json_dumps_for_jsonb(scores),
                _json_dumps_for_jsonb(critical_errors),
                _json_dumps_for_jsonb(feedback_positive),
                _json_dumps_for_jsonb(feedback_improvement),
                _json_dumps_for_jsonb(recommendations),
                _json_dumps_for_jsonb(client_profile),
                _json_dumps_for_jsonb(relevant_criteria),
                model_used,
                judge_backend,
                error_text,
                details_text,
                _json_dumps_for_jsonb(raw_result),
            )
        if row is None:
            raise RuntimeError("upsert_judge_result: no row returned")
        logger.info(
            "upsert_judge_result session_id=%s total_score=%.2f model_used=%s backend=%s",
            session_id,
            total_score,
            model_used,
            judge_backend,
        )
        return {
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }
