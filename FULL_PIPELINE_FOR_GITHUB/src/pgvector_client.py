"""
pgvector_client.py — Kept same name for code compatibility, but now uses ChromaDB!
Retrieves Current Affairs and Textbook chunks seamlessly via local vectors.

FIX (2026-04-21): Use query_embeddings (pre-encoded float vectors) instead of
query_texts to avoid ChromaDB 'list index out of range' bug when the collection
was created with a custom embedding_function. The embedding is now done
explicitly before the query call.
"""
import logging
import os
import threading

import chromadb
from sentence_transformers import SentenceTransformer as _ST

_ST_INSTANCES: dict = {}
_ST_LOCK = threading.Lock()


class LocalSentenceTransformerEF:
    """Offline-safe ChromaDB embedding function using a local model path."""

    def __init__(self, model_path: str):
        self._model_path = model_path
        # Thread-safe singleton: only load the model once across all threads
        with _ST_LOCK:
            if model_path not in _ST_INSTANCES:
                _ST_INSTANCES[model_path] = _ST(model_path)
        self._model = _ST_INSTANCES[model_path]

    def name(self) -> str:
        return f"local_st_{os.path.basename(self._model_path)}"

    def __call__(self, input):
        if isinstance(input, str):
            input = [input]
        return self._model.encode(input, normalize_embeddings=True, show_progress_bar=False).tolist()

    def embed_query(self, text=None, input=None, **kwargs):
        val = text if text is not None else input
        return self.__call__([val])[0]

    def embed_documents(self, texts=None, input=None, **kwargs):
        val = texts if texts is not None else input
        return self.__call__(val)

    def encode(self, texts, normalize_embeddings=True):
        """Direct encode passthrough — used by retrieve helpers."""
        if isinstance(texts, str):
            texts = [texts]
        return self._model.encode(texts, normalize_embeddings=normalize_embeddings, show_progress_bar=False)


from src.config import (
    CHROMA_PERSIST_DIR, CHROMA_RAG_COLLECTION, RAG_EMBED_MODEL,
    PGV_TOP_K_CA, PGV_TOP_K_TEXTBOOK,
)

from src.utils import setup_logger
logger = setup_logger(__name__)

_chroma_client = None
_rag_collection = None
_embed_fn: LocalSentenceTransformerEF | None = None
_collection_lock = threading.Lock()


def _get_rag_collection():
    """Lazy singleton: open the ChromaDB RAG collection once."""
    global _chroma_client, _rag_collection, _embed_fn
    if _rag_collection is None:
        with _collection_lock:
            if _rag_collection is None:  # double-checked locking
                logger.info(f"[RAG] Connecting to ChromaDB at: {CHROMA_PERSIST_DIR}")
                _embed_fn = LocalSentenceTransformerEF(model_path=RAG_EMBED_MODEL)
                _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
                _rag_collection = _chroma_client.get_or_create_collection(
                    name=CHROMA_RAG_COLLECTION,
                    embedding_function=_embed_fn, # Explicitly use local model
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(
                    f"[RAG] Collection '{CHROMA_RAG_COLLECTION}' ready. "
                    f"Total docs: {_rag_collection.count():,}"
                )
    return _rag_collection, _embed_fn


def _encode(text: str) -> list[list[float]]:
    """Return a [[float, ...]] embedding vector ready for query_embeddings."""
    _, ef = _get_rag_collection()
    return ef.encode([text], normalize_embeddings=True).tolist()


def _safe_filtered_count(coll, source_type: str) -> int:
    """
    Count documents matching source_type without triggering ChromaDB's
    'list index out of range' bug. Uses .get() with a limit=1 probe first.
    """
    try:
        # get() is safe — it won't HNSW-query, so no index-out-of-range risk
        probe = coll.get(
            where={"source_type": source_type},
            limit=1,
            include=["documents"],
        )
        if not probe["documents"]:
            return 0
        # Full count — only needed if probe shows at least 1 doc
        all_docs = coll.get(
            where={"source_type": source_type},
            include=["documents"],
        )
        return len(all_docs["documents"])
    except Exception as e:
        logger.debug(f"[RAG] _safe_filtered_count({source_type!r}) failed: {e}")
        return 0


def retrieve_textbook_chunks(query_text: str, top_k: int = None) -> list[dict]:
    """
    Retrieve top-k textbook chunks semantically similar to query_text.
    Uses pre-encoded embeddings to avoid ChromaDB query_texts bug.
    """
    k = top_k or PGV_TOP_K_TEXTBOOK
    coll, _ = _get_rag_collection()

    tb_count = _safe_filtered_count(coll, "textbook")
    if tb_count == 0:
        logger.warning(
            "[RAG] No textbook documents in ChromaDB. "
            "Run: python data_ingestion.py --books"
        )
        return []

    try:
        query_vec = _encode(query_text)
        with _collection_lock:
            results = coll.query(
                query_embeddings=query_vec,          # ← pre-encoded, avoids the bug
                n_results=min(k * 3, tb_count),
                where={"source_type": "textbook"},
                include=["documents", "metadatas", "distances"],
            )
        docs  = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        
        # Shuffle internally to create structural variety
        import random
        combined = list(zip(docs, metas))
        random.shuffle(combined)
        
        return [
            {
                "content":    d,
                "book_title": m.get("book_title", "Textbook"),
                "subject":    m.get("subject", ""),
                "paper":      m.get("paper", ""),
            }
            for d, m in combined[:k]
        ]
    except Exception as e:
        logger.warning(f"[RAG] Textbook retrieve failed: {e}")
        return []


def retrieve_ca_chunks(query_text: str, top_k: int = None) -> list[dict]:
    """
    Retrieve Current Affairs chunks. Currently the ingestion pipeline stores only
    'textbook' and 'PYQ' source types; CA is a future extension. Falls back to
    an unfiltered search if no dedicated 'CA' docs exist.
    """
    k = top_k or PGV_TOP_K_CA
    coll, _ = _get_rag_collection()

    # Check if dedicated CA docs exist
    ca_count = _safe_filtered_count(coll, "CA")
    if ca_count == 0:
        # Graceful fallback: return empty (textbook chunks will cover context)
        logger.debug("[RAG] No CA documents — CA retrieval skipped.")
        return []

    try:
        query_vec = _encode(query_text)
        with _collection_lock:
            results = coll.query(
                query_embeddings=query_vec,
                n_results=min(k * 3, ca_count),
                where={"source_type": "CA"},
                include=["documents", "metadatas"],
            )
        docs  = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        import random
        combined = list(zip(docs, metas))
        random.shuffle(combined)

        return [
            {"content": d, "source": m.get("source_file", "CA Source")}
            for d, m in combined[:k]
        ]
    except Exception as e:
        logger.warning(f"[RAG] CA retrieve failed: {e}")
        return []


def format_chunks_as_context(ca_chunks: list[dict], tb_chunks: list[dict]) -> str:
    """Format retrieved chunks into a structured string for the LLM prompt."""
    parts = []
    if tb_chunks:
        parts.append("--- TEXTBOOK EXTRACTS ---")
        for i, c in enumerate(tb_chunks):
            parts.append(
                f"[TB:{i+1}] Source: {c.get('book_title')} ({c.get('subject')} | {c.get('paper')})\n"
                f"{c.get('content', '').strip()}"
            )
    if ca_chunks:
        parts.append("--- CURRENT AFFAIRS ---")
        for i, c in enumerate(ca_chunks):
            parts.append(f"[CA:{i+1}] Source: {c.get('source')}\n{c.get('content', '').strip()}")
    if not parts:
        return "[No retrieved context — LLM will rely on parametric knowledge only]"
    return "\n\n".join(parts)
