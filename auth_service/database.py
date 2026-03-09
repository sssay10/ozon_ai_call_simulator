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
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('manager', 'coach')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role)
                VALUES ($1, $2, $3, 'manager')
                ON CONFLICT (email) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role
                """,
                MANAGER_USER_ID,
                MANAGER_EMAIL,
                MANAGER_PASSWORD_HASH,
            )
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role)
                VALUES ($1, $2, $3, 'coach')
                ON CONFLICT (email) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role
                """,
                COACH_USER_ID,
                COACH_EMAIL,
                COACH_PASSWORD_HASH,
            )

            await conn.execute(
                "ALTER TABLE IF EXISTS dialogue_sessions ADD COLUMN IF NOT EXISTS owner_user_id UUID"
            )
            await conn.execute(
                """
                UPDATE dialogue_sessions
                SET owner_user_id = $1::uuid
                WHERE owner_user_id IS NULL
                """,
                COACH_USER_ID,
            )
            await conn.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_name = 'dialogue_sessions'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_dialogue_sessions_owner_user_id'
                    ) THEN
                        ALTER TABLE dialogue_sessions
                        ADD CONSTRAINT fk_dialogue_sessions_owner_user_id
                        FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE RESTRICT;
                    END IF;
                END
                $$;
                """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dialogue_sessions_owner_user_id ON dialogue_sessions(owner_user_id)"
            )
            await conn.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'dialogue_sessions'
                          AND column_name = 'owner_user_id'
                          AND is_nullable = 'YES'
                    ) THEN
                        ALTER TABLE dialogue_sessions
                        ALTER COLUMN owner_user_id SET NOT NULL;
                    END IF;
                EXCEPTION
                    WHEN undefined_table THEN
                        NULL;
                END
                $$;
                """
            )
        logger.info("Auth database schema is ready")

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
