"""RAG over corp FAQ (РсВ ФАК): Chroma HTTP server only (Docker `chroma` service)."""

from .chroma_store import ChromaFAQStore, get_faq_store

__all__ = ["ChromaFAQStore", "get_faq_store"]
