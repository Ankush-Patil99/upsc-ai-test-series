"""
chroma_client.py — ChromaDB client for semantic duplicate detection (Node 6).

Blueprint Section 7.2:
  - Contains UPSC PYQs (2000-2024) + all previously generated questions
  - Embedding model: BAAI/bge-small-en (local, offline)
  - Threshold: reject if cosine similarity > 0.85 with any existing question
  - Storage: local persistent directory
"""

import logging
import os
import threading
import chromadb
from sentence_transformers import SentenceTransformer as _ST

class LocalSentenceTransformerEF:
    """Offline-safe ChromaDB embedding function using a local model path."""
    def __init__(self, model_path: str):
        self._model = _ST(model_path)
        self._model_path = model_path
    def name(self) -> str:
        return f"local_st_{os.path.basename(self._model_path)}"
    def __call__(self, input):
        if getattr(input, '__class__', None).__name__ == 'str': input = [input]
        return self._model.encode(input, normalize_embeddings=True, show_progress_bar=False).tolist()
    def embed_query(self, text=None, input=None, **kwargs):
        val = text if text is not None else input
        return self.__call__([val])[0]
    def embed_documents(self, texts=None, input=None, **kwargs):
        val = texts if texts is not None else input
        return self.__call__(val)

from src.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, DEDUP_EMBED_MODEL, DEDUP_THRESHOLD

from src.utils import setup_logger
logger = setup_logger(__name__)

# ── Lazy singletons ──────────────────────────────────────────────────────────
_chroma_client   = None
_collection      = None
_embed_fn: LocalSentenceTransformerEF | None = None
_collection_lock = threading.Lock()   # guards both init AND every query call


def _get_collection():
    global _chroma_client, _collection, _embed_fn
    if _collection is None:
        with _collection_lock:
            if _collection is None:   # double-checked locking
                logger.info(f"[ChromaDB] Connecting to persistent store at: {CHROMA_PERSIST_DIR}")
                _embed_fn      = LocalSentenceTransformerEF(model_path=DEDUP_EMBED_MODEL)
                _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
                _collection = _chroma_client.get_or_create_collection(
                    name=CHROMA_COLLECTION,
                    embedding_function=_embed_fn,  # Explicitly use local model
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"[ChromaDB] Collection '{CHROMA_COLLECTION}' ready. "
                            f"Total documents: {_collection.count()}")
    return _collection


def _encode_query(text: str) -> list[list[float]]:
    """Pre-encode text → [[float,...]] for query_embeddings."""
    _get_collection()   # ensure _embed_fn is initialised
    return _embed_fn([text])


def check_duplicate(question_stem: str) -> tuple[bool, float]:
    """
    Checks if the question_stem is semantically too similar to any existing
    question in ChromaDB (PYQs + previously generated questions).

    Returns:
        (is_duplicate: bool, max_similarity: float)
        is_duplicate = True if any match has cosine similarity > DEDUP_THRESHOLD
    """
    if not question_stem or len(question_stem.strip()) < 15:
        logger.info("[ChromaDB] Empty or very short question stem — skipping duplicate check.")
        return False, 0.0

    collection = _get_collection()

    # Thread-safe count check — avoids 'list index out of range' when collection
    # is empty or very small, and prevents concurrent HNSW corruption.
    with _collection_lock:
        count = collection.count()

    if count == 0:
        logger.info("[ChromaDB] Collection is empty — skipping duplicate check.")
        return False, 0.0

    try:
        query_vec = _encode_query(question_stem)

        # Only compare against GENERATED questions, NOT PYQ source passages.
        # PYQ passages share topic content with new questions by design — comparing
        # against them causes false-positive duplicates for any topic covered in PYQs.
        with _collection_lock:
            gen_count_result = collection.get(
                where={"source_type": "generated"}, limit=1, include=["documents"]
            )
            gen_count = len(gen_count_result["documents"])

        if gen_count == 0:
            # No generated questions yet — nothing to deduplicate against
            logger.info("[ChromaDB] No generated questions yet — skipping dedup check.")
            return False, 0.0

        with _collection_lock:
            results = collection.query(
                query_embeddings=query_vec,
                n_results=min(3, gen_count),
                where={"source_type": "generated"},   # only check generated questions
                include=["distances", "documents"]
            )

        distances = results.get("distances", [[]])[0]
        if not distances:
            return False, 0.0

        similarities = [1.0 - (d / 2.0) for d in distances]
        max_similarity = max(similarities)

        is_dup = max_similarity > DEDUP_THRESHOLD

        if is_dup:
            top_match = results["documents"][0][0] if results["documents"][0] else ""
            logger.warning(
                f"[ChromaDB] Duplicate detected! Similarity={max_similarity:.3f} "
                f"(threshold={DEDUP_THRESHOLD}). Closest match: '{top_match[:80]}...'"
            )
        else:
            logger.info(f"[ChromaDB] Uniqueness check passed. Max similarity={max_similarity:.3f}")

        return is_dup, max_similarity

    except Exception as e:
        logger.error(f"[ChromaDB] Duplicate check failed: {e}. Assuming not duplicate.")
        return False, 0.0


def add_question(question_id: str, question_stem: str, metadata: dict = None):
    """
    Adds an approved question to ChromaDB so future generations can detect it
    as a duplicate. Called after QA approval.
    Always tags with source_type='generated' so check_duplicate filters only
    against generated questions (not PYQ source passages).
    """
    collection = _get_collection()
    try:
        merged_meta = {**(metadata or {}), "source_type": "generated"}
        # Pre-encode to ensure we don't trigger ChromaDB's default internet-based
        # embedding function.
        embeddings = _encode_query(question_stem)
        collection.add(
            ids=[question_id],
            documents=[question_stem],
            embeddings=embeddings,
            metadatas=[merged_meta]
        )
        logger.info(f"[ChromaDB] Question '{question_id}' added to dedup collection.")
    except Exception as e:
        logger.error(f"[ChromaDB] Failed to add question '{question_id}': {e}")
def retrieve_pyq_chunks(query_text: str, top_k: int = 5) -> list[str]:
    """
    Retrieves recent/relevant PYQs to act as style/focus context for the LLM.
    PYQs have source_type = 'PYQ' in the dedup collection metadata.
    """
    collection = _get_collection()

    with _collection_lock:
        try:
            # Check if there are any PYQs safely
            probe = collection.get(
                where={"source_type": "PYQ"},
                limit=1,
                include=["documents"]
            )
            if not probe["documents"]:
                return []
                
            all_pyqs = collection.get(where={"source_type": "PYQ"}, include=["documents"])
            pyq_count = len(all_pyqs["documents"])
            
            query_vec = _encode_query(query_text)
            results = collection.query(
                query_embeddings=query_vec,
                n_results=min(top_k, pyq_count),
                where={"source_type": "PYQ"},
                include=["documents"]
            )
            docs = results.get("documents", [[]])[0]
            return docs
        except Exception as e:
            logger.warning(f"[ChromaDB] PYQ context retrieve failed: {e}")
            return []
