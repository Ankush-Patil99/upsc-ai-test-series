"""
data_ingestion.py — One-time data ingestion using ChromaDB (Serverless RAG setup)
Replaced Postgres PGVector with local ChromaDB to avoid HPC connection issues.
"""
import argparse
import contextlib
import json
import logging
import os
import sys

# Crucial for offline HPC clusters: Stop it from trying to hit HuggingFace over the proxy
os.environ["HF_HOME"] = "/home/scai/mtech/aib242291/UPSC_Test_Agent/models"
os.environ["HF_HUB_OFFLINE"] = "1"

from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer as _ST

class LocalSentenceTransformerEF:
    """Custom ChromaDB-compatible embedding function that loads SentenceTransformer from a local path.
    Bypasses chromadb's SentenceTransformerEmbeddingFunction which does hub resolution."""
    def __init__(self, model_path: str):
        self._model = _ST(model_path)
        self._model_path = model_path

    def name(self) -> str:
        return f"local_st_{os.path.basename(self._model_path)}"

    def __call__(self, input):
        return self._model.encode(input, normalize_embeddings=True).tolist()
from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz


@contextlib.contextmanager
def _suppress_mupdf_stderr():
    """
    Dual-layer suppression of MuPDF's C-level error output.

    PyMuPDF routes MuPDF warnings through TWO paths depending on version/build:
      a) Direct fprintf(stderr, ...) → silenced by redirecting fd 2 with os.dup2
      b) Python callback that writes to sys.stderr → silenced by replacing sys.stderr

    We also drain fitz.TOOLS.mupdf_warnings() on ENTRY to clear any residual
    output buffered from the PREVIOUS file's processing, and again on EXIT before
    restoring stderr so nothing leaks into the next file's log.
    """
    # Drain any warnings queued from the previous call
    try:
        fitz.TOOLS.mupdf_warnings(reset=True)
    except Exception:
        pass

    # ── Python-level suppress (covers PyMuPDF callback path) ─────────────────
    old_sys_stderr = sys.stderr
    _devnull_file   = open(os.devnull, "w")
    sys.stderr      = _devnull_file

    # ── C fd-level suppress (covers direct fprintf path) ─────────────────────
    _devnull_fd     = os.open(os.devnull, os.O_WRONLY)
    _old_stderr_fd  = os.dup(2)
    os.dup2(_devnull_fd, 2)

    try:
        yield
    finally:
        # Drain again before restoring so nothing leaks out
        try:
            fitz.TOOLS.mupdf_warnings(reset=True)
        except Exception:
            pass
        # Restore fd 2
        os.dup2(_old_stderr_fd, 2)
        os.close(_old_stderr_fd)
        os.close(_devnull_fd)
        # Restore sys.stderr
        sys.stderr = old_sys_stderr
        _devnull_file.close()

from src.config import (
    RAG_EMBED_MODEL, DEDUP_EMBED_MODEL,
    CHROMA_PERSIST_DIR, CHROMA_COLLECTION, CHROMA_RAG_COLLECTION,
    KB_BASE_DIR, SYLLABUS_MAP_PATH, UPSC_FACTS_PATH, COVERAGE_TRACKER
)

(BASE_DIR / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(BASE_DIR / "logs" / "data_ingestion.log"), mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("data_ingestion")

BASE_DIR      = Path(__file__).parent
DATA_DIR      = BASE_DIR / "data"
BOOKS_DIR     = DATA_DIR / "books"
PYQS_DIR      = DATA_DIR / "pyqs" / "PYQs"
TEST_SERIES_DIR = DATA_DIR / "pyqs" / "Other test series"
SYLLABUS_DIR  = DATA_DIR / "syllabus"

CHUNK_SIZE    = 512
CHUNK_OVERLAP = 64
splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

BOOK_METADATA = {
    "A-Brief-History-of-Modern-India": {"title": "Spectrum Modern India", "paper": "GS1", "subject": "History"},
    "Ethics-Lexion":                   {"title": "Ethics Lexicon",        "paper": "GS4", "subject": "Ethics"},
    "GC leong":                        {"title": "GC Leong Geography",    "paper": "GS1", "subject": "Geography"},
    "Indian Art and Culture-Nitin Singhania": {"title": "Nitin Singhania Art & Culture", "paper": "GS1", "subject": "Art"},
    "Ramesh Singh - Indian Economy":   {"title": "Ramesh Singh Economy",  "paper": "GS3", "subject": "Economy"},
    "Shanakr IAS Environment":         {"title": "Shankar IAS Environment","paper": "GS3","subject": "Environment"},
    "dd-basu-introduction-to-the-constitution": {"title": "DD Basu Constitution", "paper": "GS2", "subject": "Polity"},
}

NCERT_SUBJECT_MAP = {
    "Polity NCERT":    {"paper": "GS2", "subject": "Polity"},
    "History NCERT":   {"paper": "GS1", "subject": "History"},
    "Geography NCERT": {"paper": "GS1", "subject": "Geography"},
    "Economics NCERT": {"paper": "GS3", "subject": "Economy"},
    "Science NCERT":   {"paper": "GS3", "subject": "Science"},
    "Sociology NCERT": {"paper": "GS1", "subject": "Sociology"},
    "ART NCERT":       {"paper": "GS1", "subject": "Art"},
}

def _extract_page_text_column_aware(page) -> str:
    """
    Extracts text from a single PDF page, respecting 2-column layouts.

    Problem with the naive `get_text("blocks", sort=True)`:
      PyMuPDF's sort=True orders blocks by (y0, x0). For a 2-column page this
      interleaves left-column and right-column blocks row-by-row, so a single
      MCQ question gets fragmented across chunks — e.g. the question stem
      (left col) is separated from its options (right col), making the stored
      embeddings semantically useless for retrieval.

    Fix:
      1. Detect if the page has a 2-column layout by checking whether at least
         10% of the text characters are clearly in the right half of the page.
         (Using character count instead of block count, because PyMuPDF sometimes
         merges blocks differently on the left vs right side).
      2. If yes: read LEFT column (x0 < midpoint), sorted by y, then RIGHT
         column (x0 >= midpoint), sorted by y. This keeps each question intact.
      3. If no (single-column): fall back to the original top-to-bottom sort.
    """
    blocks = page.get_text("blocks", sort=True)
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return ""

    midpoint = page.rect.width / 2
    left_blocks = [b for b in text_blocks if b[0] < midpoint]
    right_blocks = [b for b in text_blocks if b[0] >= midpoint]
    
    right_chars = sum(len(b[4]) for b in right_blocks)
    total_chars = sum(len(b[4]) for b in text_blocks)
    
    is_two_column = (right_chars / total_chars) >= 0.10

    if is_two_column:
        left_blocks  = sorted(left_blocks, key=lambda b: b[1])
        right_blocks = sorted(right_blocks, key=lambda b: b[1])
        ordered_blocks = left_blocks + right_blocks
    else:
        ordered_blocks = text_blocks  # already sorted top-to-bottom by sort=True

    return "\n".join(b[4].strip() for b in ordered_blocks)


def extract_text(pdf_path: Path) -> str:
    """
    Extracts plain text from a PDF page-by-page, ignoring image blocks.

    Uses get_text("blocks") rather than get_text("text") because "blocks"
    is more fault-tolerant with malformed content streams — it extracts
    what it can from each block independently, whereas "text" aborts the
    entire page on the first stream error and returns empty string.
    Each page is processed with column-aware extraction to prevent
    2-column MCQ question interleaving.
    Each page is wrapped individually so one bad page doesn't kill the rest.
    """
    pages_text = []
    try:
        with _suppress_mupdf_stderr():
            doc  = fitz.open(str(pdf_path))
            for page in doc:
                try:
                    page_text = _extract_page_text_column_aware(page)
                    if page_text:
                        pages_text.append(page_text)
                except Exception:
                    pass   # skip unreadable pages, continue with the rest
            doc.close()
    except Exception as e:
        logger.error(f"  Failed to open '{pdf_path.name}': {e}")
        return ""

    text = "\n\n".join(pages_text).strip()
    if not text:
        logger.warning(
            f"  ⚠ No text extracted from '{pdf_path.name}' — "
            f"all pages may be image-only (scanned). Run OCR to make it searchable."
        )
    return text

def get_book_meta(pdf_path: Path):
    name = pdf_path.stem
    for key, meta in BOOK_METADATA.items():
        if key.lower() in name.lower(): return meta
    parent = pdf_path.parent.name
    if parent in NCERT_SUBJECT_MAP: return {"title": f"{parent} — {name}", **NCERT_SUBJECT_MAP[parent]}
    return {"title": name, "paper": "GS1", "subject": "General"}

def ingest_books_to_chroma():
    """Reads PDFs and stores in ChromaDB instead of Postgres."""
    logger.info("=== Ingesting Textbooks to ChromaDB ===")
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    embed_fn = LocalSentenceTransformerEF(model_path=RAG_EMBED_MODEL)
    coll = client.get_or_create_collection(name=CHROMA_RAG_COLLECTION, embedding_function=embed_fn, metadata={"hnsw:space": "cosine"})

    pdfs = sorted(BOOKS_DIR.rglob("*.pdf"))
    logger.info(f"Found {len(pdfs)} textbook PDFs.")

    for pdf_path in pdfs:
        logger.info(f"Processing: {pdf_path.name}")
        text = extract_text(pdf_path)
        if not text: continue
        
        meta = get_book_meta(pdf_path)
        chunks = splitter.split_text(text)
        
        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            if len(chunk) < 50: continue
            ids.append(f"tb_{pdf_path.stem}_{i:05d}")
            docs.append(chunk)
            metas.append({
                "source_type": "textbook", "book_title": meta.get("title", pdf_path.stem),
                "subject": meta.get("subject", "General"), "paper": meta.get("paper", "GS1")
            })

        for start in range(0, len(ids), 500):
            coll.upsert(ids=ids[start:start+500], documents=docs[start:start+500], metadatas=metas[start:start+500])
        logger.info(f"  Added {len(ids)} chunks.")
    logger.info("✅ Textbooks ingested via ChromaDB.")

def ingest_pyqs_to_chroma():
    """Ingests PYQs into ChromaDB for duplicate detection."""
    logger.info("=== Ingesting PYQs to ChromaDB ===")
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    embed_fn = LocalSentenceTransformerEF(model_path=DEDUP_EMBED_MODEL)
    coll = client.get_or_create_collection(name=CHROMA_COLLECTION, embedding_function=embed_fn, metadata={"hnsw:space": "cosine"})

    all_pdfs = sorted(PYQS_DIR.rglob("*.pdf")) + sorted(TEST_SERIES_DIR.rglob("*.pdf"))
    logger.info(f"Found {len(all_pdfs)} PYQ PDFs.")

    for pdf_path in all_pdfs:
        logger.info(f"Processing: {pdf_path.name}")
        text = extract_text(pdf_path)
        if not text: continue
        chunks = splitter.split_text(text)

        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            if len(chunk) < 40: continue
            doc_id = f"pyq_{pdf_path.stem}_{i:05d}"
            # NOTE: existence check removed — upsert handles duplicates idempotently.
            # Keeping the check caused 0 chunks on every re-run after the first.
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({"source_type": "PYQ", "source_file": pdf_path.name})
            
        for start in range(0, len(ids), 500):
            coll.upsert(ids=ids[start:start+500], documents=docs[start:start+500], metadatas=metas[start:start+500])
        logger.info(f"  Added {len(ids)} chunks.")
    logger.info("✅ PYQs ingested via ChromaDB.")

def build_syllabus_map():
    logger.info("=== Building syllabus_map.json ===")
    os.makedirs(KB_BASE_DIR, exist_ok=True)
    from src.syllabus_tagger import rebuild_index, get_syllabus_index
    rebuild_index()
    syllabus_map = get_syllabus_index()
    with open(SYLLABUS_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(syllabus_map, f, indent=2)
    logger.info("✅ syllabus map written.")

def init_static_kb():
    os.makedirs(KB_BASE_DIR, exist_ok=True)
    if not os.path.exists(UPSC_FACTS_PATH):
        with open(UPSC_FACTS_PATH, "w", encoding="utf-8") as f: json.dump({"Example": {"fact": "Test fact"}}, f)
        logger.info("✅ upsc_facts.json initialized")
    if not os.path.exists(COVERAGE_TRACKER):
        with open(COVERAGE_TRACKER, "w", encoding="utf-8") as f: json.dump({}, f)
        logger.info("✅ topic_coverage.json initialized")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--books", action="store_true")
    parser.add_argument("--pyqs", action="store_true")
    parser.add_argument("--syllabus", action="store_true")
    parser.add_argument("--kb", action="store_true")
    args = parser.parse_args()

    if args.all or args.kb: init_static_kb()
    if args.all or args.syllabus: build_syllabus_map()
    if args.all or args.books: ingest_books_to_chroma()
    if args.all or args.pyqs: ingest_pyqs_to_chroma()
    logger.info("🎉 Complete!")
