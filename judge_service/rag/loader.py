from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"


def load_knowledge_documents() -> list[dict]:
    docs = []

    for path in KB_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8").strip()
        docs.append(
            {
                "path": str(path),
                "name": path.name,
                "category": path.parent.name,
                "content": text,
            }
        )

    return docs