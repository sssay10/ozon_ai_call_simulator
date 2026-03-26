from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from .schemas import KBChunk


class KBLoader:
    def __init__(self, kb_root: str):
        self.kb_root = Path(kb_root)

    def load_chunks(self) -> List[KBChunk]:
        if not self.kb_root.exists():
            raise FileNotFoundError(f"KB root does not exist: {self.kb_root}")

        chunks: List[KBChunk] = []

        for path in sorted(self.kb_root.rglob("*.yaml")):
            with path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)

            if raw is None:
                continue

            chunk = KBChunk.model_validate(raw)
            chunks.append(chunk)

        return chunks