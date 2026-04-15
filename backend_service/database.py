from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

MANAGER_USER_ID = "00000000-0000-0000-0000-000000000101"
COACH_USER_ID = "00000000-0000-0000-0000-000000000102"
MANAGER_EMAIL = "manager@example.com"
COACH_EMAIL = "coach@example.com"
MANAGER_PASSWORD_HASH = (
    "pbkdf2_sha256$600000$7b2107ce2bc6ba3df5734a2a521b86f8$"
    "0eb95df478ac77e2aab09ed3cc6a127d0699d08d1625c3360b45afad2b640c44"
)
COACH_PASSWORD_HASH = (
    "pbkdf2_sha256$600000$1aa20de0b878c7a27c35cdf7c2260885$"
    "866b8f822f592cceb0dd9d26d004b1e724771fa54918aa77ec5f0e99fcf0fceb"
)


@dataclass(slots=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    role: str


@dataclass(slots=True)
class PublicUserRecord:
    id: str
    email: str
    role: str


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    owner_user_id: str
    room_name: str
    product: str
    started_at: str | None
    ended_at: str | None
    total_score: float | None
    judge_ready: bool
    scenario_id: str | None


@dataclass(slots=True)
class TrainingScenarioRecord:
    id: str
    name: str
    persona_description: str
    main_pain: str
    created_by_user_id: str
    created_at: str | None
    updated_at: str | None


class Database:
    def __init__(self) -> None:
        self._database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://dialogue:dialogue@localhost:5432/dialogues",
        )
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=10)
        logger.info(
            "Auth database pool ready (schema from agent_service/scripts/init.sql on empty Postgres volume)"
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self._pool

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, password_hash, role
                FROM users
                WHERE lower(email) = lower($1)
                """,
                email.strip(),
            )
        if row is None:
            return None
        return UserRecord(
            id=str(row["id"]),
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
        )

    async def get_user_by_id(self, user_id: str) -> UserRecord | None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, password_hash, role
                FROM users
                WHERE id = $1::uuid
                """,
                user_id,
            )
        if row is None:
            return None
        return UserRecord(
            id=str(row["id"]),
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
        )

    async def create_user(self, *, email: str, password_hash: str, role: str) -> PublicUserRecord:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, password_hash, role)
                VALUES ($1, $2, $3)
                RETURNING id, email, role
                """,
                email.strip().lower(),
                password_hash,
                role,
            )
        return PublicUserRecord(
            id=str(row["id"]),
            email=row["email"],
            role=row["role"],
        )

    async def list_users(self) -> list[PublicUserRecord]:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, email, role
                FROM users
                ORDER BY created_at ASC, email ASC
                """
            )
        return [
            PublicUserRecord(
                id=str(row["id"]),
                email=row["email"],
                role=row["role"],
            )
            for row in rows
        ]

    async def list_sessions_for_actor(
        self,
        *,
        user_id: str,
        role: str,
        limit: int = 50,
    ) -> list[SessionRecord]:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            if role == "coach":
                rows = await conn.fetch(
                    """
                    SELECT
                        ds.id AS session_id,
                        ds.owner_user_id,
                        ds.room_name,
                        ds.product,
                        ds.started_at,
                        ds.ended_at,
                        jr.total_score,
                        (jr.id IS NOT NULL) AS judge_ready,
                        jr.scenario_id
                    FROM dialogue_sessions ds
                    LEFT JOIN judge_results jr ON jr.session_id = ds.id
                    ORDER BY ds.started_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT
                        ds.id AS session_id,
                        ds.owner_user_id,
                        ds.room_name,
                        ds.product,
                        ds.started_at,
                        ds.ended_at,
                        jr.total_score,
                        (jr.id IS NOT NULL) AS judge_ready,
                        jr.scenario_id
                    FROM dialogue_sessions ds
                    LEFT JOIN judge_results jr ON jr.session_id = ds.id
                    WHERE ds.owner_user_id = $1::uuid
                    ORDER BY ds.started_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                )

        return [
            SessionRecord(
                session_id=str(row["session_id"]),
                owner_user_id=str(row["owner_user_id"]),
                room_name=row["room_name"],
                product=row["product"],
                started_at=row["started_at"].isoformat() if row["started_at"] else None,
                ended_at=row["ended_at"].isoformat() if row["ended_at"] else None,
                total_score=float(row["total_score"]) if row["total_score"] is not None else None,
                judge_ready=bool(row["judge_ready"]),
                scenario_id=row["scenario_id"],
            )
            for row in rows
        ]

    async def list_training_scenarios(self) -> list[TrainingScenarioRecord]:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    name,
                    persona_description,
                    main_pain,
                    created_by_user_id,
                    created_at,
                    updated_at
                FROM training_scenarios
                ORDER BY updated_at DESC, created_at DESC
                """
            )
        return [
            TrainingScenarioRecord(
                id=str(row["id"]),
                name=row["name"],
                persona_description=row["persona_description"],
                main_pain=row["main_pain"],
                created_by_user_id=str(row["created_by_user_id"]),
                created_at=row["created_at"].isoformat() if row["created_at"] else None,
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
            )
            for row in rows
        ]

    async def create_training_scenario(
        self,
        *,
        name: str,
        persona_description: str,
        main_pain: str,
        created_by_user_id: str,
    ) -> TrainingScenarioRecord:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO training_scenarios (name, persona_description, main_pain, created_by_user_id)
                VALUES ($1, $2, $3, $4::uuid)
                RETURNING
                    id,
                    name,
                    persona_description,
                    main_pain,
                    created_by_user_id,
                    created_at,
                    updated_at
                """,
                name.strip(),
                persona_description.strip(),
                main_pain.strip(),
                created_by_user_id,
            )
        return TrainingScenarioRecord(
            id=str(row["id"]),
            name=row["name"],
            persona_description=row["persona_description"],
            main_pain=row["main_pain"],
            created_by_user_id=str(row["created_by_user_id"]),
            created_at=row["created_at"].isoformat() if row["created_at"] else None,
            updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        )

    async def update_training_scenario(
        self,
        *,
        scenario_id: str,
        name: str,
        persona_description: str,
        main_pain: str,
    ) -> TrainingScenarioRecord | None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE training_scenarios
                SET
                    name = $2,
                    persona_description = $3,
                    main_pain = $4,
                    updated_at = $5::timestamptz
                WHERE id = $1::uuid
                RETURNING
                    id,
                    name,
                    persona_description,
                    main_pain,
                    created_by_user_id,
                    created_at,
                    updated_at
                """,
                scenario_id,
                name.strip(),
                persona_description.strip(),
                main_pain.strip(),
                datetime.now().astimezone(),
            )
        if row is None:
            return None
        return TrainingScenarioRecord(
            id=str(row["id"]),
            name=row["name"],
            persona_description=row["persona_description"],
            main_pain=row["main_pain"],
            created_by_user_id=str(row["created_by_user_id"]),
            created_at=row["created_at"].isoformat() if row["created_at"] else None,
            updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        )
