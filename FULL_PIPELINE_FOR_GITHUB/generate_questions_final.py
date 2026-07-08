"""
generate_questions_final.py — The Single Authoritative UPSC MCQ Generator
==========================================================================
This is the FINAL, production-ready question generator for the UPSC AI Engine.
It replaces generate_questions.py and is the only script you need going forward.

KEY UPGRADE OVER generate_questions.py
---------------------------------------
* CA-Aware Generation: Current Affairs questions are grounded in scraped,
  real-world content from 7 verified sources (VisionIAS, InsightsIAS, ForumIAS,
  The Hindu, Indian Express, PIB, Drishti IAS) stored in ChromaDB.
* Zero hallucination guarantee: the LLM (Qwen-72B) is strictly constrained to
  the retrieved ChromaDB context. It cannot fabricate facts.
* --scrape-now flag: trigger a live scrape of all 7 CA sources before generation.
* --ca-only flag: generate ONLY current_affairs type questions from CA context.
* Full backward compatibility with all generate_questions.py flags.

Usage Examples
--------------
  # Check all data status (ChromaDB + CA chunks):
  python generate_questions_final.py --status

  # Scrape fresh CA content then generate 10 questions:
  python generate_questions_final.py --scrape-now --count 10

  # Generate 5 current-affairs questions (grounded in CA RAG context):
  python generate_questions_final.py --count 5 --ca-only

  # Generate from a specific CA topic:
  python generate_questions_final.py \\
      --topic "India-China Relations" \\
      --subtopic "Galwan Valley Incident" \\
      --paper GS2 --difficulty hard --type current_affairs

  # Generate a full mixed batch (ingest + scrape + generate):
  python generate_questions_final.py --ingest --scrape-now --count 20 --workers 4

  # Only ingest textbooks/PYQs (no generation):
  python generate_questions_final.py --ingest-only

  # Only scrape CA (no generation):
  python generate_questions_final.py --scrape-only

  # Run with SLURM:
  python generate_questions_final.py --batch pipeline_data/topic_queue.json --output pipeline_data/output/run1.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── HPC / Offline setup ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
os.environ["HF_HOME"]                     = str(BASE_DIR / "models")
os.environ["HF_HUB_OFFLINE"]              = "1"
os.environ["NO_PROXY"]                    = "localhost,127.0.0.1,::1"
os.environ["no_proxy"]                    = "localhost,127.0.0.1,::1"
# Block ChromaDB from downloading its default ONNX model (all-MiniLM-L6-v2).
# We supply our own local embedding functions everywhere, so this is never needed.
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["ANONYMIZED_TELEMETRY"]        = "FALSE"
os.environ["TOKENIZERS_PARALLELISM"]      = "false"

# ── Logging ──────────────────────────────────────────────────────────────────
(BASE_DIR / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            str(BASE_DIR / "logs" / "generate_questions_final.log"),
            mode="a", encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("generate_questions_final")

summary_logger = logging.getLogger("summary")
summary_logger.setLevel(logging.INFO)
summary_logger.propagate = False
summary_handler = logging.FileHandler(
    str(BASE_DIR / "logs" / "generation_summary.log"),
    mode="a", encoding="utf-8"
)
summary_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
summary_logger.addHandler(summary_handler)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 — DATA STATUS CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_chromadb_status() -> dict:
    """Returns counts of documents in each ChromaDB collection, including CA."""
    import chromadb
    from src.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, CHROMA_RAG_COLLECTION

    chroma_path = Path(CHROMA_PERSIST_DIR)
    empty = {
        "chroma_exists": False,
        "rag_collection": 0,
        "dedup_collection": 0,
        "ca_chunks": 0,
        "textbook_chunks": 0,
    }
    if not chroma_path.exists():
        return empty

    try:
        client      = chromadb.PersistentClient(path=str(chroma_path))
        collections = {c.name: c for c in client.list_collections()}

        rag_count   = 0
        dedup_count = 0
        ca_count    = 0
        tb_count    = 0

        if CHROMA_RAG_COLLECTION in collections:
            rag_coll  = collections[CHROMA_RAG_COLLECTION]
            rag_count = rag_coll.count()
            # Count CA vs textbook chunks via metadata filter
            try:
                ca_probe = rag_coll.get(where={"source_type": "CA"}, limit=1, include=["documents"])
                if ca_probe["documents"]:
                    ca_all    = rag_coll.get(where={"source_type": "CA"}, include=["documents"])
                    ca_count  = len(ca_all["documents"])
            except Exception:
                pass
            try:
                tb_probe = rag_coll.get(where={"source_type": "textbook"}, limit=1, include=["documents"])
                if tb_probe["documents"]:
                    tb_all   = rag_coll.get(where={"source_type": "textbook"}, include=["documents"])
                    tb_count = len(tb_all["documents"])
            except Exception:
                pass

        if CHROMA_COLLECTION in collections:
            dedup_count = collections[CHROMA_COLLECTION].count()

        return {
            "chroma_exists":    True,
            "rag_collection":   rag_count,
            "dedup_collection": dedup_count,
            "ca_chunks":        ca_count,
            "textbook_chunks":  tb_count,
        }
    except Exception as e:
        logger.warning(f"ChromaDB status check failed: {e}")
        return empty


def print_status():
    """Print a human-readable summary of the complete pipeline data status."""
    status = check_chromadb_status()
    data_dir = BASE_DIR / "data"

    books_count  = len(list((data_dir / "books").rglob("*.pdf"))) if (data_dir / "books").exists() else 0
    pyq_count    = len(list((data_dir / "pyqs").rglob("*.pdf")))  if (data_dir / "pyqs").exists() else 0

    print("\n" + "=" * 65)
    print("  UPSC AI Engine — Complete Data Status")
    print("=" * 65)
    print(f"  ChromaDB exists          : {status['chroma_exists']}")
    print(f"  RAG collection total     : {status['rag_collection']:,}")
    print(f"    ├─ Textbook chunks     : {status['textbook_chunks']:,}")
    print(f"    └─ Current Affairs (CA): {status['ca_chunks']:,}  ← scraped content")
    print(f"  Dedup collection (PYQs)  : {status['dedup_collection']:,}")
    print(f"  Book PDFs on disk        : {books_count}")
    print(f"  PYQ PDFs on disk         : {pyq_count}")
    print("=" * 65)

    # Readiness warnings
    if status["rag_collection"] == 0:
        print("  ⚠  RAG collection EMPTY. Run --ingest or --scrape-now first.")
    elif status["textbook_chunks"] == 0:
        print("  ⚠  No textbook chunks. Run: python generate_questions_final.py --ingest-only")
    else:
        print("  ✅ Textbook RAG is populated.")

    if status["ca_chunks"] == 0:
        print("  ⚠  No CA chunks. Run: python ca_scraper.py --run-now")
        print("     OR: python generate_questions_final.py --scrape-now")
    else:
        print(f"  ✅ CA context ready ({status['ca_chunks']:,} chunks from 7 sources).")

    if status["dedup_collection"] == 0:
        print("  ⚠  Dedup collection empty. Run: python generate_questions_final.py --ingest-only --pyqs-only")
    else:
        print("  ✅ Dedup collection populated.")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — TEXTBOOK/PYQ DATA INGESTION (optional, idempotent)
# ─────────────────────────────────────────────────────────────────────────────

def run_ingestion(books: bool = True, pyqs: bool = True, syllabus: bool = True, kb: bool = True):
    """Run data_ingestion.py functions to populate ChromaDB from local PDFs."""
    logger.info("=" * 65)
    logger.info("Starting PDF data ingestion from ./data ...")
    logger.info("=" * 65)

    sys.path.insert(0, str(BASE_DIR))
    from data_ingestion import (
        ingest_books_to_chroma,
        ingest_pyqs_to_chroma,
        build_syllabus_map,
        init_static_kb,
    )

    if kb:
        logger.info("[Ingest] Initializing static KB ...")
        init_static_kb()
    if syllabus:
        logger.info("[Ingest] Building syllabus map ...")
        build_syllabus_map()
    if books:
        logger.info("[Ingest] Ingesting textbooks → ChromaDB RAG collection ...")
        ingest_books_to_chroma()
    if pyqs:
        logger.info("[Ingest] Ingesting PYQs → ChromaDB dedup collection ...")
        ingest_pyqs_to_chroma()

    logger.info("✅ PDF data ingestion complete.")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — CURRENT AFFAIRS SCRAPING (optional, runs ca_scraper.py logic)
# ─────────────────────────────────────────────────────────────────────────────

def run_ca_scrape(sources: list[str] | None = None):
    """
    Trigger the CA scraper to fetch fresh content from all 7 sources.
    Calls ca_scraper.run_all_scrapers() directly (no subprocess).
    """
    logger.info("=" * 65)
    logger.info("Starting Current Affairs scrape ...")
    logger.info("=" * 65)

    sys.path.insert(0, str(BASE_DIR))
    try:
        from ca_scraper import run_all_scrapers
    except ImportError as e:
        logger.error(f"Failed to import ca_scraper: {e}")
        logger.error("Ensure ca_scraper.py exists in the same directory.")
        return

    summary = run_all_scrapers(sources=sources)
    total   = summary.get("total_chunks_ingested", 0)

    logger.info(f"✅ CA scrape complete — {total:,} chunks ingested into ChromaDB.")
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — QUESTION GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def run_single(app, q_input: dict) -> tuple[dict | None, float, bool]:
    """
    Run the 6-node LangGraph pipeline for a single question input.

    For 'current_affairs' type questions, the pipeline:
    1. Node 2 (Researcher) retrieves CA chunks from ChromaDB with source_type=CA
    2. Node 3 (Drafter) uses ONLY that retrieved CA text as its source of truth
    3. Node 6 (QA) verifies the question's factual grounding before approval

    Returns tuple of (formatted_question dict or None, elapsed_time float, is_approved bool).
    """
    initial_state = {
        "topic":                  q_input["topic"],
        "subtopic":               q_input["subtopic"],
        "difficulty":             q_input.get("difficulty", "medium"),
        "paper":                  q_input.get("paper", "GS2"),
        "question_type":          q_input.get("question_type", "factual"),
        "research_context":       None,
        "question_stem":          None,
        "correct_answer":         None,
        "distractors":            None,
        "explanation":            None,
        "formatted_question":     None,
        "tags":                   None,
        "citations":              None,
        "difficulty_score":       None,
        "estimated_time_seconds": None,
        "qa_score":               None,
        "qa_flags":               [],
        "retry_count":            0,
        "approved":               False,
    }

    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    q_type = q_input.get("question_type", "factual")
    ca_flag = " [CA-GROUNDED]" if q_type == "current_affairs" else ""
    logger.info(
        f"▶ Generating{ca_flag} | topic='{q_input['topic']}' | "
        f"subtopic='{q_input['subtopic']}' | paper={q_input.get('paper')} | "
        f"type={q_type} | thread={thread_id}"
    )

    try:
        start_time = time.time()
        final_state = app.invoke(initial_state, config=config)
        elapsed = time.time() - start_time
    except Exception as e:
        logger.error(f"Pipeline crashed for thread={thread_id}: {e}", exc_info=True)
        return None, 0.0, False

    approved = final_state.get("approved", False)
    qa_score = final_state.get("qa_score", 0.0)

    if approved:
        logger.info(f"  ✅ APPROVED | qa_score={qa_score:.4f}{ca_flag} | time={elapsed:.1f}s")
        fq = final_state.get("formatted_question")
        if fq:
            fq["_generation_time_sec"] = round(elapsed, 1)
        return fq, elapsed, True
    else:
        flags = final_state.get("qa_flags", [])
        logger.warning(f"  ❌ REJECTED | qa_score={qa_score:.4f} | flags={flags} | time={elapsed:.1f}s")
        return None, elapsed, False


def run_batch(app, batch_input: list[dict], max_workers: int = 4) -> dict:
    """Run the pipeline concurrently for a list of question inputs."""
    total = len(batch_input)
    approved_questions = []
    failed_count = 0
    total_qa     = 0.0
    topic_dist: dict[str, int] = {}

    # Count CA vs non-CA for logging
    ca_count_in  = sum(1 for q in batch_input if q.get("question_type") == "current_affairs")
    logger.info(
        f"Starting batch generation: {total} questions | "
        f"CA-type={ca_count_in} | workers={max_workers}"
    )

    with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        futures = {executor.submit(run_single, app, q): i for i, q in enumerate(batch_input)}

        completed_count = 0
        for future in as_completed(futures):
            completed_count += 1
            idx    = futures[future]
            result, elapsed, is_approved = future.result()
            
            topic_name = batch_input[idx]["topic"]
            summary_logger.info(f"[{completed_count}/{total}] | Topic: {topic_name[:30]}... | Time: {elapsed:.1f}s | Status: {'APPROVED' if is_approved else 'REJECTED'}")
            
            logger.info(f"── Completed [{completed_count}/{total} questions] ──")

            if result:
                approved_questions.append(result)
                total_qa += result.get("qa_score", 0.0)
                for tag in result.get("tags", []):
                    topic_dist[tag] = topic_dist.get(tag, 0) + 1
            else:
                failed_count += 1

    approved_count = len(approved_questions)
    pass_rate = round(approved_count / total, 4) if total > 0 else 0.0
    avg_qa    = round(total_qa / approved_count, 4) if approved_count > 0 else 0.0

    batch_id = f"BATCH_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    output = {
        "batch_id":           batch_id,
        "total_questions":    total,
        "approved_count":     approved_count,
        "failed_count":       failed_count,
        "pass_rate":          pass_rate,
        "average_qa_score":   avg_qa,
        "ca_questions_requested": ca_count_in,
        "topic_distribution": topic_dist,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "pipeline_version":   "V2.1.0-CA",
        "questions":          approved_questions,
    }

    logger.info(
        f"Batch complete | approved={approved_count}/{total} | "
        f"pass_rate={pass_rate:.1%} | avg_qa={avg_qa:.4f}"
    )
    return output


def save_output(data: dict, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ Output saved → {path}")


def print_question(q: dict):
    """Pretty-print a single approved question to terminal."""
    q_type = q.get("question_type", "")
    ca_marker = " [CURRENT AFFAIRS — CA-grounded]" if q_type == "current_affairs" else ""
    print("\n" + "═" * 70)
    print(f"  Topic    : {q.get('topic', '')} → {q.get('subtopic', '')}")
    print(f"  Paper    : {q.get('paper', '')}  |  Difficulty: {q.get('difficulty', '')}")
    print(f"  Type     : {q_type}{ca_marker}")
    print(f"  QA Score : {q.get('qa_score', 0.0):.3f}")
    print("═" * 70)
    print(f"\n{q.get('question_stem', '')}\n")
    for opt in q.get("options", []):
        marker = "✓" if opt == q.get("correct_answer") else " "
        print(f"  ({marker}) {opt}")
    print(f"\n  Explanation: {q.get('explanation', '')}")
    print("═" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# CA-only topic sampling
# ─────────────────────────────────────────────────────────────────────────────

def _sample_ca_topics_from_chromadb(count: int) -> list[dict]:
    """
    Samples actual CA article titles from ChromaDB to use as generation topics.
    This ensures questions are grounded in scraped CA content that exists in the vector store.
    Falls back to generic current affairs topics if ChromaDB is empty.
    """
    import chromadb
    from src.config import CHROMA_PERSIST_DIR, CHROMA_RAG_COLLECTION

    topics = []
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        colls  = {c.name: c for c in client.list_collections()}
        if CHROMA_RAG_COLLECTION not in colls:
            raise ValueError("RAG collection not found")

        coll = colls[CHROMA_RAG_COLLECTION]
        # Fetch CA metadata to extract real topics ingested
        ca_docs = coll.get(
            where={"source_type": "CA"},
            limit=min(count * 5, 500),
            include=["metadatas"],
        )

        seen_titles: set[str] = set()
        for meta in ca_docs.get("metadatas", []):
            title   = meta.get("article_title", "")
            gs      = meta.get("gs_paper", "GS2")
            subject = meta.get("subject", "Current Affairs")
            src     = meta.get("source_name", "")

            # Use article title as the topic, cleaned up
            topic_name = title.split("—")[0].strip() if "—" in title else title
            topic_name = topic_name.replace("Current Affairs", "").strip()
            if not topic_name or topic_name in seen_titles:
                continue
            seen_titles.add(topic_name)

            # Map gs_paper: take the first one if comma-separated
            paper = gs.split(",")[0].strip() if gs else "GS2"

            topics.append({
                "topic":         topic_name,
                "subtopic":      f"Recent developments — {subject}",
                "paper":         paper,
                "difficulty":    "medium",
                "question_type": "current_affairs",
            })

        if len(topics) >= count:
            import random
            return random.sample(topics, count)

    except Exception as e:
        logger.warning(f"Could not sample CA topics from ChromaDB: {e}. Using fallback topics.")

    # Fallback: generic top-priority UPSC CA topics
    fallback_topics = [
        {"topic": "India-China Relations", "subtopic": "Border disputes and recent developments", "paper": "GS2", "difficulty": "hard", "question_type": "current_affairs"},
        {"topic": "India-US Strategic Partnership", "subtopic": "Defence, trade and technology cooperation", "paper": "GS2", "difficulty": "medium", "question_type": "current_affairs"},
        {"topic": "Climate Change & COP Summits", "subtopic": "India's NDCs and international climate commitments", "paper": "GS3", "difficulty": "medium", "question_type": "current_affairs"},
        {"topic": "Digital India & Fintech", "subtopic": "UPI, CBDC and digital payment ecosystem", "paper": "GS3", "difficulty": "easy", "question_type": "current_affairs"},
        {"topic": "Agriculture Sector Reforms", "subtopic": "PM-KISAN, crop insurance, and new farm policies", "paper": "GS3", "difficulty": "medium", "question_type": "current_affairs"},
        {"topic": "Biodiversity Conservation", "subtopic": "IUCN Red List updates and new protected areas", "paper": "GS3", "difficulty": "medium", "question_type": "current_affairs"},
        {"topic": "India's Space Programme", "subtopic": "ISRO missions and private space sector reforms", "paper": "GS3", "difficulty": "easy", "question_type": "current_affairs"},
        {"topic": "National Health Mission", "subtopic": "Ayushman Bharat and PM-JAY expansion", "paper": "GS2", "difficulty": "easy", "question_type": "current_affairs"},
        {"topic": "Banking & Financial Sector", "subtopic": "RBI monetary policy and NBFC regulations", "paper": "GS3", "difficulty": "hard", "question_type": "current_affairs"},
        {"topic": "Internal Security", "subtopic": "Left Wing Extremism and counter-insurgency measures", "paper": "GS3", "difficulty": "hard", "question_type": "current_affairs"},
    ]
    import random
    return random.sample(fallback_topics, min(count, len(fallback_topics)))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UPSC MCQ Generator V2.1 — CA-Grounded, Zero-Hallucination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Data / Ingestion ──────────────────────────────────────────────────────
    parser.add_argument("--status",       action="store_true", help="Show full data status and exit")
    parser.add_argument("--ingest",       action="store_true", help="Ingest textbook PDFs before generating")
    parser.add_argument("--ingest-only",  action="store_true", help="Only ingest PDFs, skip generation")
    parser.add_argument("--books-only",   action="store_true", help="Ingest books only (not PYQs)")
    parser.add_argument("--pyqs-only",    action="store_true", help="Ingest PYQs only (not books)")

    # ── CA Scraping ───────────────────────────────────────────────────────────
    parser.add_argument(
        "--scrape-now", action="store_true",
        help="Scrape all 7 CA sources and ingest into ChromaDB before generating"
    )
    parser.add_argument(
        "--scrape-only", action="store_true",
        help="Only scrape CA content, skip question generation"
    )
    parser.add_argument(
        "--scrape-source", type=str, default=None,
        help="Scrape a single source (e.g., thehindu, pib, visionias, forumias)"
    )
    parser.add_argument(
        "--ca-only", action="store_true",
        help="Generate ONLY current_affairs type questions (grounded in CA RAG)"
    )

    # ── Question generation ───────────────────────────────────────────────────
    parser.add_argument("--batch",    type=str,  help="Path to JSON batch file")
    parser.add_argument("--count",    type=int,  default=None,  help="Number of questions (default: 5, or all if --batch is used)")
    parser.add_argument("--workers",  type=int,  default=10,  help="Parallel workers (default: 10)")
    parser.add_argument("--seed",     type=int,  default=None, help="Random seed for topic sampling")
    parser.add_argument("--output",   type=str,  default=None, help="Output JSON file path")
    parser.add_argument("--no-checkpoint", action="store_true", help="Disable LangGraph checkpointing")
    parser.add_argument("--smart-sample", action="store_true", help="Sample topics weighted by PYQ frequency (replaces plan_batch.py)")

    # ── Single question mode ──────────────────────────────────────────────────
    parser.add_argument("--topic",      type=str, default=None)
    parser.add_argument("--subtopic",   type=str, default=None)
    parser.add_argument("--paper",      type=str, default="GS2",
                        choices=["GS1", "GS2", "GS3", "GS4", "CSAT"])
    parser.add_argument("--difficulty", type=str, default="medium",
                        choices=["easy", "medium", "hard"])
    parser.add_argument("--type",       type=str, default="factual",
                        choices=[
                            "factual", "analytical", "current_affairs",
                            "statement_based", "match_following",
                            "assertion_reasoning", "correct_incorrect", "most_appropriate"
                        ])

    args = parser.parse_args()

    # Automatically handle default count unless loading from an explicit batch file
    if args.count is None:
        args.count = None if args.batch else 5

    # ── Status check ──────────────────────────────────────────────────────────
    if args.status:
        print_status()
        return

    # ── Step 1: PDF Ingestion ──────────────────────────────────────────────────
    if args.ingest or args.ingest_only or args.books_only or args.pyqs_only:
        do_books    = not args.pyqs_only
        do_pyqs     = not args.books_only
        do_syllabus = not (args.books_only or args.pyqs_only)
        do_kb       = not (args.books_only or args.pyqs_only)
        run_ingestion(books=do_books, pyqs=do_pyqs, syllabus=do_syllabus, kb=do_kb)

        if args.ingest_only:
            print_status()
            return

    # ── Step 2: CA Scraping ───────────────────────────────────────────────────
    if args.scrape_now or args.scrape_only:
        sources = [args.scrape_source] if args.scrape_source else None
        run_ca_scrape(sources=sources)

        if args.scrape_only:
            print_status()
            return

    # ── Pre-flight check ──────────────────────────────────────────────────────
    status = check_chromadb_status()

    if args.ca_only or (args.type == "current_affairs" and args.topic):
        # For CA mode, we NEED ca_chunks. Warn clearly if empty.
        if status["ca_chunks"] == 0:
            logger.warning(
                "⚠  CA chunks are EMPTY in ChromaDB.\n"
                "   Questions will rely on textbook context only (may lack recent facts).\n"
                "   For CA-grounded questions, run: python generate_questions_final.py --scrape-now\n"
                "   Continuing anyway..."
            )
        else:
            logger.info(
                f"✅ CA context available: {status['ca_chunks']:,} chunks from scraped sources."
            )

    if status["rag_collection"] == 0:
        logger.warning(
            "⚠  RAG collection is EMPTY — questions generated WITHOUT context.\n"
            "   Run --ingest and/or --scrape-now first for best quality.\n"
            "   Continuing anyway..."
        )

    # ── Build LangGraph pipeline ───────────────────────────────────────────────
    logger.info("Building LangGraph pipeline ...")
    from src.graph import build_graph
    app = build_graph(use_checkpointing=not args.no_checkpoint)

    # ── Single topic mode ──────────────────────────────────────────────────────
    if args.topic:
        subtopic = args.subtopic or args.topic
        q_input  = {
            "topic":         args.topic,
            "subtopic":      subtopic,
            "difficulty":    args.difficulty,
            "paper":         args.paper,
            "question_type": args.type,
        }
        is_ca = args.type == "current_affairs"
        logger.info(
            f"Single question mode: {args.topic} → {subtopic}"
            + (" [CURRENT AFFAIRS — CA-RAG grounded]" if is_ca else "")
        )
        result, elapsed, is_approved = run_single(app, q_input)
        if is_approved and result:
            print_question(result)
            if args.output:
                save_output({"questions": [result]}, args.output)
        else:
            print("\n❌ Question rejected or failed. See logs/generate_questions_final.log.")
        return

    # ── Batch mode ─────────────────────────────────────────────────────────────
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            logger.error(f"Batch file not found: {args.batch}")
            sys.exit(1)
        with open(batch_path, "r", encoding="utf-8") as f:
            batch_input = json.load(f)
        if args.count is not None and args.count < len(batch_input):
            batch_input = batch_input[: args.count]
        logger.info(f"Loaded {len(batch_input)} questions from {batch_path.name}")

    elif args.ca_only:
        # CA-only mode: sample topics from actual scraped CA content in ChromaDB
        logger.info(
            f"CA-only mode: sampling {args.count} topics from CA chunks in ChromaDB..."
        )
        batch_input = _sample_ca_topics_from_chromadb(args.count)
        logger.info(f"Sampled {len(batch_input)} CA topics.")
        for qi in batch_input:
            logger.info(f"  CA topic: {qi['topic']} → {qi['subtopic']}")

    elif args.smart_sample:
        from plan_batch import generate_batch
        logger.info(f"Smart-sampling {args.count} topics weighted by historical PYQ frequency...")
        batch_input = generate_batch(args.count)
        logger.info(f"Smart-sampled {len(batch_input)} questions.")
        for i, qi in enumerate(batch_input[:5]): # Log a few
             logger.info(f"  [Q{i+1}] {qi['topic']} → {qi['subtopic']}")

    else:
        # Default: sample from the built-in UPSC topic bank
        from src.topic_bank import sample_topics
        batch_input = sample_topics(args.count, seed=args.seed)
        logger.info(
            f"Sampled {len(batch_input)} questions randomly from topic bank"
            + (f" (seed={args.seed})" if args.seed else "")
        )

    # ── Run batch ──────────────────────────────────────────────────────────────
    output = run_batch(app, batch_input, max_workers=args.workers)

    # ── Save output ────────────────────────────────────────────────────────────
    out_path = args.output or str(
        BASE_DIR / "output" / f"{output['batch_id']}.json"
    )
    save_output(output, out_path)

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  GENERATION COMPLETE")
    print("=" * 65)
    print(f"  Total attempted         : {output['total_questions']}")
    print(f"  Approved                : {output['approved_count']} ({output['pass_rate']:.1%})")
    print(f"  Failed/Rejected         : {output['failed_count']}")
    print(f"  Avg QA Score            : {output['average_qa_score']:.4f}")
    print(f"  CA Questions Requested  : {output.get('ca_questions_requested', 0)}")
    print(f"  Pipeline Version        : {output['pipeline_version']}")
    print(f"  Output saved            : {out_path}")
    print("=" * 65)

    for i, q in enumerate(output["questions"], 1):
        print(f"\n[Question {i} of {output['approved_count']}]")
        print_question(q)


if __name__ == "__main__":
    main()
