from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, desc, func, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

logger = logging.getLogger(__name__)

COACH_USER_ID = "00000000-0000-0000-0000-000000000102"
MANAGER_USER_ID = "00000000-0000-0000-0000-000000000101"
MANAGER_PASSWORD_HASH = (
    "pbkdf2_sha256$600000$7b2107ce2bc6ba3df5734a2a521b86f8$"
    "0eb95df478ac77e2aab09ed3cc6a127d0699d08d1625c3360b45afad2b640c44"
)
COACH_PASSWORD_HASH = (
    "pbkdf2_sha256$600000$1aa20de0b878c7a27c35cdf7c2260885$"
    "866b8f822f592cceb0dd9d26d004b1e724771fa54918aa77ec5f0e99fcf0fceb"
)


class Base(DeclarativeBase):
    pass


class DialogueSession(Base):
    __tablename__ = "dialogue_sessions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    room_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    job_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    archetype: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(Text, nullable=False)
    product: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["DialogueMessage"]] = relationship(back_populates="session")
    judge_result: Mapped["JudgeResult | None"] = relationship(back_populates="session")


class DialogueMessage(Base):
    __tablename__ = "dialogue_messages"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("dialogue_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped[DialogueSession] = relationship(back_populates="messages")


class JudgeResult(Base):
    __tablename__ = "judge_results"
    __table_args__ = (UniqueConstraint("session_id", name="uq_judge_results_session_id"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("dialogue_sessions.id", ondelete="CASCADE"), nullable=False
    )
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    critical_errors: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    feedback_positive: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    feedback_improvement: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    recommendations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    timecodes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    client_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    relevant_criteria: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    model_used: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    judge_backend: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[DialogueSession] = relationship(back_populates="judge_result")


class Database:
    """Database connection and operations manager for judge service."""

    def __init__(self) -> None:
        self.engine = None
        self.async_session: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://dialogue:dialogue@localhost:5432/dialogues",
        )
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        logger.info("Database: connecting")
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.execute(
                text(
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
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO users (id, email, password_hash, role)
                    VALUES
                        (
                            :manager_id,
                            'manager@example.com',
                            :manager_password_hash,
                            'manager'
                        ),
                        (
                            :coach_id,
                            'coach@example.com',
                            :coach_password_hash,
                            'coach'
                        )
                    ON CONFLICT (email) DO NOTHING
                    """
                ),
                {
                    "manager_id": MANAGER_USER_ID,
                    "manager_password_hash": MANAGER_PASSWORD_HASH,
                    "coach_id": COACH_USER_ID,
                    "coach_password_hash": COACH_PASSWORD_HASH,
                },
            )
            await conn.execute(text("ALTER TABLE IF EXISTS dialogue_sessions ADD COLUMN IF NOT EXISTS owner_user_id UUID"))
            await conn.execute(
                text(
                    """
                    UPDATE dialogue_sessions
                    SET owner_user_id = CAST(:coach_id AS UUID)
                    WHERE owner_user_id IS NULL
                    """
                ),
                {"coach_id": COACH_USER_ID},
            )
            await conn.execute(
                text(
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
            )
            await conn.execute(
                text(
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
            )
            await conn.run_sync(Base.metadata.create_all)

        self._initialized = True
        logger.info("Database: initialized successfully")

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
            logger.info("Database: connection closed")

    def _require_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if not self._initialized or self.async_session is None:
            raise RuntimeError("Database not initialized")
        return self.async_session

    @staticmethod
    def _to_uuid(value: str | UUID) -> UUID:
        return value if isinstance(value, UUID) else UUID(value)

    def _scope_dialogue_session_query(self, stmt: Any, user_id: str, role: str) -> Any:
        if role == "coach":
            return stmt
        return stmt.where(DialogueSession.owner_user_id == self._to_uuid(user_id))

    async def get_session(self, session_id: str) -> DialogueSession | None:
        session_uuid = self._to_uuid(session_id)
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            result = await session.execute(
                select(DialogueSession).where(DialogueSession.id == session_uuid)
            )
            return result.scalar_one_or_none()

    async def get_latest_session_by_room(self, room_name: str) -> DialogueSession | None:
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            result = await session.execute(
                select(DialogueSession)
                .where(DialogueSession.room_name == room_name)
                .order_by(DialogueSession.started_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_session_for_actor(self, session_id: str, user_id: str, role: str) -> DialogueSession | None:
        session_uuid = self._to_uuid(session_id)
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            stmt = select(DialogueSession).where(DialogueSession.id == session_uuid)
            stmt = self._scope_dialogue_session_query(stmt, user_id=user_id, role=role)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_latest_session_by_room_for_actor(
        self,
        room_name: str,
        user_id: str,
        role: str,
    ) -> DialogueSession | None:
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            stmt = (
                select(DialogueSession)
                .where(DialogueSession.room_name == room_name)
                .order_by(DialogueSession.started_at.desc())
                .limit(1)
            )
            stmt = self._scope_dialogue_session_query(stmt, user_id=user_id, role=role)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_session_transcript(self, session_id: str) -> list[dict[str, Any]]:
        session_uuid = self._to_uuid(session_id)
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            result = await session.execute(
                select(DialogueMessage)
                .where(DialogueMessage.session_id == session_uuid)
                .order_by(DialogueMessage.created_at.asc())
            )
            records = result.scalars().all()

        transcript: list[dict[str, Any]] = []
        role_map = {"user": "manager", "assistant": "client"}
        for row in records:
            mapped_role = role_map.get(row.role)
            if not mapped_role:
                continue
            transcript.append(
                {
                    "role": mapped_role,
                    "text": row.content,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )

        logger.info(
            "Database: retrieved transcript for session %s: %s turns",
            session_id,
            len(transcript),
        )
        return transcript

    async def save_judge_result(
        self,
        session_id: str,
        scenario_id: str,
        evaluation: dict[str, Any],
    ) -> JudgeResult:
        session_uuid = self._to_uuid(session_id)
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            existing = await session.execute(
                select(JudgeResult).where(JudgeResult.session_id == session_uuid)
            )
            row = existing.scalar_one_or_none()
            if row is None:
                row = JudgeResult(
                    session_id=session_uuid,
                    scenario_id=scenario_id,
                )
                session.add(row)

            row.scenario_id = scenario_id
            row.total_score = float(evaluation.get("total_score") or 0.0)
            row.scores = evaluation.get("scores") or {}
            row.critical_errors = evaluation.get("critical_errors") or []
            row.feedback_positive = evaluation.get("feedback_positive") or []
            row.feedback_improvement = evaluation.get("feedback_improvement") or []
            row.recommendations = evaluation.get("recommendations") or []
            row.timecodes = evaluation.get("timecodes") or []
            row.client_profile = evaluation.get("client_profile") or {}
            row.relevant_criteria = evaluation.get("relevant_criteria") or []
            row.model_used = evaluation.get("model_used") or "unknown"
            row.judge_backend = evaluation.get("judge_backend") or "unknown"
            row.error = evaluation.get("error")
            row.details = evaluation.get("details")
            row.raw_result = evaluation

            await session.commit()
            await session.refresh(row)
            return row

    async def get_judge_result(self, session_id: str) -> JudgeResult | None:
        session_uuid = self._to_uuid(session_id)
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            result = await session.execute(
                select(JudgeResult).where(JudgeResult.session_id == session_uuid)
            )
            return result.scalar_one_or_none()

    async def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            result = await session.execute(
                select(DialogueSession, JudgeResult)
                .outerjoin(JudgeResult, JudgeResult.session_id == DialogueSession.id)
                .order_by(desc(DialogueSession.started_at))
                .limit(limit)
            )
            rows = result.all()

        sessions: list[dict[str, Any]] = []
        for session_row, judge_row in rows:
            sessions.append(
                {
                    "session_id": str(session_row.id),
                    "room_name": session_row.room_name,
                    "archetype": session_row.archetype,
                    "difficulty": session_row.difficulty,
                    "product": session_row.product,
                    "owner_user_id": str(session_row.owner_user_id),
                    "started_at": session_row.started_at.isoformat() if session_row.started_at else None,
                    "ended_at": session_row.ended_at.isoformat() if session_row.ended_at else None,
                    "total_score": judge_row.total_score if judge_row else None,
                    "judge_ready": judge_row is not None,
                    "scenario_id": judge_row.scenario_id if judge_row else None,
                }
            )
        return sessions

    async def list_sessions_for_actor(
        self,
        *,
        user_id: str,
        role: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        async_session = self._require_sessionmaker()
        async with async_session() as session:
            stmt = (
                select(DialogueSession, JudgeResult)
                .outerjoin(JudgeResult, JudgeResult.session_id == DialogueSession.id)
                .order_by(desc(DialogueSession.started_at))
                .limit(limit)
            )
            stmt = self._scope_dialogue_session_query(stmt, user_id=user_id, role=role)
            result = await session.execute(stmt)
            rows = result.all()

        sessions: list[dict[str, Any]] = []
        for session_row, judge_row in rows:
            sessions.append(
                {
                    "session_id": str(session_row.id),
                    "owner_user_id": str(session_row.owner_user_id),
                    "room_name": session_row.room_name,
                    "archetype": session_row.archetype,
                    "difficulty": session_row.difficulty,
                    "product": session_row.product,
                    "started_at": session_row.started_at.isoformat() if session_row.started_at else None,
                    "ended_at": session_row.ended_at.isoformat() if session_row.ended_at else None,
                    "total_score": judge_row.total_score if judge_row else None,
                    "judge_ready": judge_row is not None,
                    "scenario_id": judge_row.scenario_id if judge_row else None,
                }
            )
        return sessions
