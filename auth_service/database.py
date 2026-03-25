from __future__ import annotations

import logging
import os
from dataclasses import dataclass

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
