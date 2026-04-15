"""Shared user-message builder for step judges."""

from __future__ import annotations


def transcript_block(persona: str, transcript_text: str) -> str:
    return (
        f"persona_description:\n{persona or '(не задано)'}\n\n"
        f"transcript:\n{transcript_text}"
    )
