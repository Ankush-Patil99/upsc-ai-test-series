# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
=============================================================================
UPSC Question Bank — Phase 2: Mains Hints Enrichment
=============================================================================
Loads ONLY the lightweight books (NCERTs) into FAISS, then fetches every
question in DB with empty mains_hint and enriches it in batches.

Run AFTER Phase 1 is complete:
    python scripts/enrich_mains_hints.py

Books used (smaller, most impactful):
  - History NCERTs 6-12 + Spectrum Modern History
  - Art NCERTs 11-12 + Nitin Singhania
=============================================================================
"""

import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml
with open(ROOT / "configs" / "settings.yaml") as f:
    config = yaml.safe_load(f)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from api.models import SessionLocal, UniversalQuestionBank
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from src.mcq_generation.generator import llm_cascade

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

BOOKS   = ROOT / "data" / "books"
MAINS   = Path(r"C:\Users\ankus\OneDrive\Desktop\UPSC section wise papers\Mains centric")

# Use ONLY lightweight, high-signal books for RAG (avoids memory blow-up)
HISTORY_BOOKS = [
    BOOKS / "History NCERT" / "10-History.pdf",
    BOOKS / "History NCERT" / "11-History.pdf",
    BOOKS / "History NCERT" / "12-History-Part-1.pdf",
    BOOKS / "History NCERT" / "12-History-Part-2.pdf",
    BOOKS / "A-Brief-History-of-Modern-India-2019-2020-Edition-by-Spectrum-Books-Rajiv-Ahir-Kalpana-Rajaram-z-lib.org_.pdf",
]
ART_BOOKS = [
    BOOKS / "ART NCERT" / "11.pdf",
    BOOKS / "ART NCERT" / "12.pdf",
    BOOKS / "Indian Art and Culture-Nitin Singhania.pdf",
]

HINT_PROMPT = PromptTemplate.from_template(
"""You are an expert UPSC Mains answer-writing coach.
Write a mains_hint (strictly under 65 words) for this Prelims question that:
- Contains specific facts, dates, constitutional articles, statistics, or names directly relevant to the topic
- Is written for Mains GS answer enrichment (no fluff, dense information)
- Does NOT repeat the question text

Question: {question}
Topic: {topic}
Book Context:
{context}

Return ONLY the mains_hint. No labels, no markdown, no preamble."""
)

BATCH_SIZE = 50  # enrich N questions per RAG session


def build_rag(book_paths: list, label: str):
    print(f"\n[RAG] Building {label} index from {len(book_paths)} books...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    emb      = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
    docs     = []
    for p in book_paths:
        if not Path(p).exists():
            print(f"   [SKIP] {Path(p).name}")
            continue
        try:
            pages  = PyPDFLoader(str(p)).load()
            chunks = splitter.split_documents(pages)
            docs.extend(chunks)
            print(f"   [OK] {Path(p).name} → {len(chunks)} chunks")
        except Exception as e:
            print(f"   [ERR] {Path(p).name}: {e}")
    if not docs:
        return None, emb
    print(f"[RAG] Embedding {len(docs)} chunks...")
    index = FAISS.from_documents(docs, emb)
    print(f"[RAG] {label} index ready.")
    return index, emb


def generate_hint(question: str, topic: str, rag) -> str:
    try:
        docs    = rag.similarity_search(f"{topic} {question}", k=3)
        context = "\n---\n".join(d.page_content[:400] for d in docs)
        for llm in llm_cascade:
            if llm is None:
                continue
            try:
                result = (HINT_PROMPT | llm).invoke({
                    "question": question,
                    "topic": topic,
                    "context": context
                })
                hint = result.content if hasattr(result, "content") else str(result)
                return hint.strip()[:600]
            except Exception as e:
                print(f"   [LLM] Failed: {str(e)[:60]}. Trying next...")
                time.sleep(2)
    except Exception as e:
        print(f"   [RAG] Error: {e}")
    return ""


def enrich_subject(subject_filter: str, rag):
    db = SessionLocal()
    # Get questions with empty mains_hint for this subject
    rows = (
        db.query(UniversalQuestionBank)
        .filter(
            UniversalQuestionBank.subject.like(f"%{subject_filter}%"),
            (UniversalQuestionBank.mains_hint == "") |
            (UniversalQuestionBank.mains_hint == None)
        )
        .limit(BATCH_SIZE)
        .all()
    )
    db.close()

    if not rows:
        print(f"   [OK] All '{subject_filter}' questions already enriched.")
        return 0

    print(f"   [ENRICH] Processing {len(rows)} questions for '{subject_filter}'...")
    enriched = 0
    for row in rows:
        hint = generate_hint(row.question, row.topic, rag)
        if hint:
            db2 = SessionLocal()
            try:
                q = db2.query(UniversalQuestionBank).filter(UniversalQuestionBank.id == row.id).first()
                if q:
                    q.mains_hint = hint
                    db2.commit()
                    enriched += 1
            except Exception as e:
                db2.rollback()
                print(f"   [DB] Update error: {e}")
            finally:
                db2.close()
        time.sleep(1)

    print(f"   [ENRICH] Done → {enriched}/{len(rows)} enriched.")
    return enriched


def main():
    print("=" * 65)
    print("  UPSC Question Bank — Phase 2: Mains Hints Enrichment")
    print("=" * 65)

    db = SessionLocal()
    total = db.query(UniversalQuestionBank).count()
    empty = db.query(UniversalQuestionBank).filter(
        (UniversalQuestionBank.mains_hint == "") |
        (UniversalQuestionBank.mains_hint == None)
    ).count()
    db.close()
    print(f"\n  Total questions in DB : {total}")
    print(f"  Without mains hint    : {empty}")

    if empty == 0:
        print("\n  All questions already have mains hints. Nothing to do.")
        return

    # ── History ──────────────────────────────────────────────────────────────
    print("\n[PHASE 2A] History RAG")
    h_rag, _ = build_rag(HISTORY_BOOKS, "History")
    if h_rag:
        for subj in ["Ancient and Medieval History", "Modern History", "History PYQ"]:
            enrich_subject(subj, h_rag)
    del h_rag  # free RAM before loading art books

    # ── Art & Culture ─────────────────────────────────────────────────────────
    print("\n[PHASE 2B] Art & Culture RAG")
    a_rag, _ = build_rag(ART_BOOKS, "Art_Culture")
    if a_rag:
        enrich_subject("Art and Culture", a_rag)
    del a_rag

    db = SessionLocal()
    remaining = db.query(UniversalQuestionBank).filter(
        (UniversalQuestionBank.mains_hint == "") |
        (UniversalQuestionBank.mains_hint == None)
    ).count()
    db.close()

    print("\n" + "=" * 65)
    print("  ✅  PHASE 2 COMPLETE")
    print(f"     Questions still needing hints : {remaining}")
    if remaining > 0:
        print(f"     Re-run this script to process next batch of {BATCH_SIZE}.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
