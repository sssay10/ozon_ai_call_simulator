"""ChromaDB HTTP client + similarity search (Docker Chroma server only; no embedded DB)."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from judge.knowledge_rag.faq_parse import parse_rsv_faq_sheet

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "rko_rsv_faq"
DEFAULT_XLSX = "corp_data.xlsx"


def _patch_onnx_model_dir() -> None:
    """Store ONNX MiniLM under project .cache (embeddings run in judge process)."""
    try:
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

        root = Path(os.environ.get("JUDGE_SERVICE_ROOT") or Path(__file__).resolve().parents[2])
        cache_root = Path(os.getenv("CHROMA_ONNX_CACHE", str(root / ".cache" / "chroma")))
        cache_root.mkdir(parents=True, exist_ok=True)
        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = cache_root / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    except Exception as exc:  # pragma: no cover
        logger.debug("ONNX cache patch skipped: %s", exc)


_patch_onnx_model_dir()


def _default_embed_fn() -> Any:
    """Embeddings are computed in the judge client and sent to the Chroma server."""
    return embedding_functions.DefaultEmbeddingFunction()


class ChromaFAQStore:
    """Talks to a Chroma server via HttpClient (e.g. `chroma` service in Docker Compose)."""

    def __init__(
        self,
        *,
        http_host: str,
        http_port: int = 8000,
        collection_name: str = DEFAULT_COLLECTION,
        xlsx_path: Path | None = None,
    ) -> None:
        host = http_host.strip()
        if not host:
            raise ValueError("CHROMA_HTTP_HOST must be set (e.g. chroma in Compose, localhost from host)")

        self._collection_name = collection_name
        self._xlsx_path = xlsx_path or Path(os.getenv("CORP_XLSX_PATH", DEFAULT_XLSX))
        self._embed_fn = _default_embed_fn()
        self._http_port = http_port
        self._persist_label = f"http://{host}:{http_port}"
        self._client = chromadb.HttpClient(host=host, port=http_port)
        logger.info("Chroma FAQ store: HttpClient -> %s", self._persist_label)

        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embed_fn,
            metadata={"description": "РсВ ФАК from corp_data.xlsx"},
        )

    @classmethod
    def from_env(cls) -> ChromaFAQStore:
        root = Path(os.getenv("JUDGE_SERVICE_ROOT", ".")).resolve()
        xlsx = Path(os.getenv("CORP_XLSX_PATH", str(root / DEFAULT_XLSX)))
        host = os.getenv("CHROMA_HTTP_HOST", "chroma").strip()
        port = int(os.getenv("CHROMA_HTTP_PORT", "8000"))
        return cls(http_host=host, http_port=port, xlsx_path=xlsx)

    def collection_count(self) -> int:
        return int(self._collection.count())

    def clear(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embed_fn,
            metadata={"description": "РсВ ФАК from corp_data.xlsx"},
        )

    def ingest_from_xlsx(self, path: Path | None = None) -> int:
        """Replace collection contents with parsed FAQ from xlsx."""
        p = path or self._xlsx_path
        if not p.is_file():
            raise FileNotFoundError(f"corp xlsx not found: {p}")
        docs = parse_rsv_faq_sheet(p)
        self.clear()
        if not docs:
            logger.warning("FAQ parse produced 0 documents from %s", p)
            return 0
        texts = [d.as_embedding_text() for d in docs]
        ids = [
            hashlib.sha256(t.encode("utf-8")).hexdigest()[:32] + f"_{i}"
            for i, t in enumerate(texts)
        ]
        metadatas = [
            {"question": d.question[:2000], "row": str(d.row_start), "sheet": d.sheet}
            for d in docs
        ]
        self._collection.add(ids=ids, documents=texts, metadatas=metadatas)
        logger.info("ingested %s FAQ chunks into Chroma (%s)", len(docs), self._persist_label)
        return len(docs)

    def search(self, query: str, n_results: int = 8) -> list[str]:
        """Return top matching FAQ texts for the judge prompt."""
        q = (query or "").strip()
        if not q or self.collection_count() == 0:
            return []
        n = max(1, min(n_results, 32))
        res = self._collection.query(query_texts=[q], n_results=n)
        docs_out = res.get("documents") or []
        if not docs_out or not docs_out[0]:
            logger.debug("Chroma search: no documents (n_results=%s)", n)
            return []
        found = list(docs_out[0])
        logger.debug(
            "Chroma search: n_results=%s returned=%s chunks (query_len=%s)",
            n,
            len(found),
            len(q),
        )
        return found


_faq_store: ChromaFAQStore | None = None


def get_faq_store() -> ChromaFAQStore:
    global _faq_store
    if _faq_store is None:
        _faq_store = ChromaFAQStore.from_env()
    return _faq_store
