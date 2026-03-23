"""Session metadata parsing and prompt assembly from UI/database blocks only."""
from __future__ import annotations

import json
from typing import Any

def _build_prompt_from_blocks(blocks: dict[str, str]) -> str:
    lines = [
        "Ты играешь роль КЛИЕНТА. Ты принимаешь входящий звонок и ведешь диалог как реальный собеседник.",
        "",
        "## Роль клиента",
        blocks["client_role"],
        "",
        "## Описание архетипа",
        blocks["archetype_description"],
        "",
        "## Описание сценария",
        blocks["scenario_description"],
        "",
        "## Язык и формат ответа",
        blocks["language_and_format_instructions"],
    ]
    return "\n".join(lines)


def build_system_prompt(prompt_blocks: dict[str, str]) -> str:
    """Build LLM system prompt from structured blocks provided by UI/database."""
    return _build_prompt_from_blocks(prompt_blocks)


def parse_session_metadata(metadata_str: str) -> dict[str, Any]:
    """Parse job metadata JSON and extract structured prompt blocks."""
    out: dict[str, Any] = {
        "archetype": "",
        "difficulty": "",
        "product": "",
        "training_scenario_id": "",
        "training_scenario_name": "",
        "owner_user_id": "",
        "user_role": "",
        "user_email": "",
        "prompt_blocks": None,
    }
    if not metadata_str or not metadata_str.strip():
        return out
    try:
        data = json.loads(metadata_str)
        if isinstance(data, dict):
            if isinstance(data.get("archetype"), str):
                out["archetype"] = data["archetype"].strip()
            if isinstance(data.get("difficulty"), str):
                out["difficulty"] = data["difficulty"].strip()
            if isinstance(data.get("product"), str) and data["product"].strip():
                out["product"] = data["product"].strip()
            if isinstance(data.get("training_scenario_id"), str):
                out["training_scenario_id"] = data["training_scenario_id"]
            if isinstance(data.get("training_scenario_name"), str):
                out["training_scenario_name"] = data["training_scenario_name"]
            if isinstance(data.get("owner_user_id"), str):
                out["owner_user_id"] = data["owner_user_id"]
            if isinstance(data.get("user_role"), str):
                out["user_role"] = data["user_role"]
            if isinstance(data.get("user_email"), str):
                out["user_email"] = data["user_email"]
            blocks_raw = data.get("prompt_blocks")
            if isinstance(blocks_raw, dict):
                client_role = blocks_raw.get("client_role")
                archetype_description = blocks_raw.get("archetype_description")
                scenario_description = blocks_raw.get("scenario_description")
                language_and_format = blocks_raw.get("language_and_format_instructions")
                if (
                    isinstance(client_role, str)
                    and client_role.strip()
                    and isinstance(archetype_description, str)
                    and archetype_description.strip()
                    and isinstance(scenario_description, str)
                    and scenario_description.strip()
                    and isinstance(language_and_format, str)
                    and language_and_format.strip()
                ):
                    out["prompt_blocks"] = {
                        "client_role": client_role.strip(),
                        "archetype_description": archetype_description.strip(),
                        "scenario_description": scenario_description.strip(),
                        "language_and_format_instructions": language_and_format.strip(),
                    }
    except (json.JSONDecodeError, TypeError):
        pass

    return out
