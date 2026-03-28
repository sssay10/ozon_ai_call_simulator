from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"


def _parse_metadata(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    meta: dict[str, str] = {}
    body_lines: list[str] = []
    in_metadata = True

    for line in lines:
        stripped = line.strip()

        if in_metadata and stripped and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key in {"criterion", "scenario"}:
                meta[key] = value
                continue

        in_metadata = False
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return meta, body


def load_knowledge_documents() -> list[dict]:
    docs = []

    for path in KB_DIR.rglob("*.md"):
        raw_text = path.read_text(encoding="utf-8").strip()
        meta, body = _parse_metadata(raw_text)

        docs.append(
            {
                "path": str(path),
                "name": path.name,
                "category": path.parent.name,
                "criterion": meta.get("criterion"),
                "scenario": meta.get("scenario"),
                "content": body,
            }
        )

    return docs
