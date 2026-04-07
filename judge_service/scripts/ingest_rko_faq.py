#!/usr/bin/env python3
"""Build / refresh Chroma index from corp_data.xlsx (sheet «РсВ ФАК»).

Chroma is the Docker `chroma` service (same Compose network as judge_service).

  docker compose up -d chroma
  docker compose run --rm judge_service uv run python scripts/ingest_rko_faq.py

Targets: `chroma_script_defaults.py` (host machine). Inside the judge container use Compose env.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from chroma_script_defaults import CHROMA_HOST, CHROMA_PORT

FAQ_XLSX = _ROOT / "corp_data.xlsx"

from judge.knowledge_rag.chroma_store import ChromaFAQStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ingest_rko_faq")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest РсВ ФАК into ChromaDB")
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=None,
        help=f"Path to xlsx (default: {FAQ_XLSX})",
    )
    args = parser.parse_args()

    xlsx = args.xlsx.resolve() if args.xlsx is not None else FAQ_XLSX

    if not xlsx.is_file():
        logger.error("File not found: %s", xlsx)
        return 1

    store = ChromaFAQStore(
        http_host=CHROMA_HOST,
        http_port=CHROMA_PORT,
        xlsx_path=xlsx,
    )
    n = store.ingest_from_xlsx(xlsx)
    logger.info("Done: %s FAQ documents -> %s:%s", n, CHROMA_HOST, CHROMA_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
