"""
Dialogue logging to PostgreSQL for manager quality and analytics.
Logs session metadata (settings) and each user/assistant message.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

import asyncpg  # pyright: ignore[reportMissingImports]
import httpx

logger = logging.getLogger("dialogue_logging")

# Skip system messages; only user (manager) and assistant (client) are logged
LOG_ROLES = frozenset({"user", "assistant"})


class DialogueLogger:
    """Async logger for dialogue sessions and messages. Uses a single connection."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn: asyncpg.Connection | None = None

    async def _get_conn(self) -> asyncpg.Connection:
        if self._conn is None or self._conn.is_closed():
            self._conn = await asyncpg.connect(self._database_url)
        return self._conn

    async def create_session(
        self,
        room_name: str,
        job_id: str | None,
        product: str,
        owner_user_id: str,
    ) -> UUID | None:
        """Insert a session row; return session id or None on error."""
        if not owner_user_id.strip():
            logger.warning("create_session skipped: owner_user_id is missing")
            return None
        try:
            conn = await self._get_conn()
            row = await conn.fetchrow(
                """
                INSERT INTO dialogue_sessions (room_name, job_id, product, owner_user_id)
                VALUES ($1, $2, $3, $4::uuid)
                RETURNING id
                """,
                room_name,
                job_id or "",
                product,
                owner_user_id,
            )
            return row["id"] if row else None
        except Exception as e:
            logger.exception("create_session failed: %s", e)
            return None

    async def insert_message(self, session_id: UUID, role: str, content: str) -> None:
        """Append a dialogue message. No-op if role not in user/assistant or content empty."""
        if role not in LOG_ROLES or not (content and content.strip()):
            return
        try:
            conn = await self._get_conn()
            await conn.execute(
                """
                INSERT INTO dialogue_messages (session_id, role, content)
                VALUES ($1, $2, $3)
                """,
                session_id,
                role,
                content.strip(),
            )
        except Exception as e:
            logger.exception("insert_message failed: %s", e)

    async def end_session(self, session_id: UUID) -> None:
        """Set ended_at for the session."""
        try:
            conn = await self._get_conn()
            await conn.execute(
                "UPDATE dialogue_sessions SET ended_at = now() WHERE id = $1",
                session_id,
            )
        except Exception as e:
            logger.exception("end_session failed: %s", e)

    async def close(self) -> None:
        if self._conn and not self._conn.is_closed():
            await self._conn.close()
            self._conn = None


async def trigger_judge_session(
    *,
    judge_service_url: str,
    session_id: UUID,
    room_name: str,
    product: str,
) -> dict[str, Any] | None:
    """Trigger judge_service for a completed session."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{judge_service_url.rstrip('/')}/api/judge-session",
                json={
                    "session_id": str(session_id),
                    "room_name": room_name,
                    "product": product,
                },
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.exception("trigger_judge_session failed: %s", e)
        return None


def _chat_message_to_text(msg: Any) -> str:
    """Extract plain text from a ChatMessage for storage."""
    try:
        if hasattr(msg, "text_content") and callable(getattr(msg, "text_content")):
            out = msg.text_content
            return (out or "").strip()
        if hasattr(msg, "content"):
            parts = []
            for c in msg.content:
                if isinstance(c, str):
                    parts.append(c)
            return " ".join(parts).strip()
    except Exception:
        pass
    return ""


def _role_to_str(msg: Any) -> str:
    """Get role string from a ChatMessage."""
    if hasattr(msg, "role"):
        r = msg.role
        if isinstance(r, str):
            return r
        return str(r) if r is not None else "assistant"
    return "assistant"


def make_conversation_item_callback(
    logger_instance: DialogueLogger,
    session_id: UUID,
    loop: asyncio.AbstractEventLoop,
) -> Any:
    """Return a callback suitable for session.on('conversation_item_added') that logs to DB."""

    def _on_item(ev: Any) -> None:
        item = getattr(ev, "item", None)
        if item is None:
            return
        # Only log ChatMessage (skip FunctionCall, FunctionCallOutput, etc.)
        if getattr(item, "type", None) != "message":
            return
        role = _role_to_str(item)
        content = _chat_message_to_text(item)
        if role not in LOG_ROLES or not content:
            return
        asyncio.run_coroutine_threadsafe(
            logger_instance.insert_message(session_id, role, content),
            loop,
        )

    return _on_item

