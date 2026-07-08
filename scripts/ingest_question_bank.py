# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
=============================================================================
UPSC Universal Question Bank — FAST Question Ingestion (Phase 1)
=============================================================================
This script ONLY extracts MCQs from PDFs and stores them in the DB.
NO book RAG. NO mains hints. That happens in enrich_mains_hints.py (Phase 2).

Strategy: extract fast → store fast → bulk complete first, then enrich.

Run: python scripts/ingest_question_bank.py
Restart-safe: tracks completed PDFs in logs/qbank_ingestion_checkpoint.log
=============================================================================
"""

import os, re, json, time, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml
with open(ROOT / "configs" / "settings.yaml") as f:
    config = yaml.safe_load(f)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from api.models import SessionLocal, UniversalQuestionBank
from src.mcq_generation.generator import llm_cascade
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader

# ─────────────────────────────────────────────────────────────────────────────
CHECKPOINT = ROOT / "logs" / "qbank_ingestion_checkpoint.log"
CHECKPOINT.parent.mkdir(exist_ok=True)

print("=" * 70)
print("  UPSC Question Bank — Phase 1: Fast PDF Ingestion")
print("=" * 70)

print("\n[INIT] Loading embedding model (all-MiniLM-L6-v2)...")
EMB = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
print("[INIT] Ready.\n")

# ─────────────────────────────────────────────────────────────────────────────
# PDF SOURCE MAP
# ─────────────────────────────────────────────────────────────────────────────
H  = Path(r"C:\Users\ankus\OneDrive\Desktop\UPSC section wise papers\01 History")
AC = Path(r"C:\Users\ankus\OneDrive\Desktop\UPSC section wise papers\03 Art and culture")

ALL_PAIRS = [
    # ── Ancient & Medieval History ────────────────────────────────────────────
    dict(q=H/"PrayasAncient_and_Medieval_History_Question.pdf",
         a=H/"Prayas Ancient_and_Medieval_History_Answer.pdf",
         subject="Ancient and Medieval History", label="Prayas AMH"),
    dict(q=H/"Vision AMH 1.pdf", a=H/"Vision AMH 1 solution.pdf",
         subject="Ancient and Medieval History", label="Vision AMH-1"),
    dict(q=H/"Vision AMH 2.pdf", a=H/"Vision AMH 2 solution.pdf",
         subject="Ancient and Medieval History", label="Vision AMH-2"),
    # ── Modern History ────────────────────────────────────────────────────────
    dict(q=H/"Vision MH 1.pdf", a=H/"Vision MH 1 solution.pdf",
         subject="Modern History", label="Vision MH-1"),
    dict(q=H/"Vision MH 2.pdf", a=H/"Vision MH 2 solution.pdf",
         subject="Modern History", label="Vision MH-2"),
    dict(q=H/"Vision MH 3.pdf", a=H/"Vision MH 3 solution.pdf",
         subject="Modern History", label="Vision MH-3"),
    # ── PYQ Workbook (self-contained) ─────────────────────────────────────────
    dict(q=H/"1704193186-HISTORY_PYQ_WORKBOOK.pdf", a=None,
         subject="History PYQ", label="History PYQ Workbook"),
    # ── Art & Culture ─────────────────────────────────────────────────────────
    dict(q=AC/"Prayas Art and cult Questions.pdf",
         a=AC/"Prayas Art and culture Answes.pdf",
         subject="Art and Culture", label="Prayas Art & Culture"),
    dict(q=AC/"NCERT MCQs.pdf", a=None,
         subject="Art and Culture", label="Art NCERT MCQs"),
]

# ─────────────────────────────────────────────────────────────────────────────
# LLM PARSE PROMPT — granular topics, accurate correct_option
# ─────────────────────────────────────────────────────────────────────────────
PARSE_PROMPT = PromptTemplate.from_template(
"""You are a precise UPSC MCQ data extractor. Extract EVERY question from the QUESTION TEXT below.

QUESTION TEXT:
{q_text}

ANSWER KEY MAP (question_number -> correct option letter, pre-extracted from answer PDF):
{answer_map}

SOLUTION TEXT (use for rationale; contains explanations after each Q number):
{a_snippet}

OUTPUT RULES — strictly follow:
1. Extract EVERY numbered question present. Never skip.
2. Return a JSON array only. No markdown. No preamble. No extra keys.
3. Each object must have EXACTLY these keys:
   "question"      - full question text, no truncation
   "options"       - array of 4 strings (strip A/B/C/D labels, keep text only)
   "correct_option"- EXACT text of the correct option (use answer_map to find letter, then match to option text)
   "rationale"     - explanation from solution text if present; else write 2-3 dense factual sentences. Min 40 words.
   "topic"         - VERY specific sub-topic: e.g. "Chalukya Dynasty", "Harappan Drainage System", "Quit India Movement 1942", "Bharatnatyam - Adavus". NEVER use broad labels.
   "difficulty"    - "easy" | "medium" | "hard"
4. Ignore headers, footers, page numbers, watermarks, instruction paragraphs.
5. Do NOT hallucinate. Only return questions actually present in the text.

JSON array:"""
)


def extract_answer_map(a_text: str) -> dict:
    """Extract Q-number -> letter from answer PDFs using multiple patterns."""
    m = {}
    # Pattern: Q 1.C  or  Q1.C  or  Q 1.(C)
    for x in re.finditer(r'Q\s*\.?\s*(\d+)\s*[\.\-\:]+\s*\(?([A-Da-d])\)?', a_text):
        m[x.group(1)] = x.group(2).upper()
    # Pattern: standalone line "1. (b)" or "1.(b)" or "1 b"
    for x in re.finditer(r'^\s*(\d+)[\.\)]\s*\(?([A-Da-d])\)?\s*$', a_text, re.MULTILINE):
        if x.group(1) not in m:
            m[x.group(1)] = x.group(2).upper()
    # Pattern: Ans/Answer: 5 - D
    for x in re.finditer(r'[Aa]ns(?:wer)?[\s\.\:]+(\d+)[\s\=\-\→]+([A-Da-d])', a_text):
        if x.group(1) not in m:
            m[x.group(1)] = x.group(2).upper()
    return m


def extract_text(path: Path) -> str:
    """Load PDF and return all text."""
    try:
        pages = PyPDFLoader(str(path)).load()
        return "\n".join(p.page_content for p in pages)
    except Exception as e:
        print(f"   [ERR] Cannot read {path.name}: {e}")
        return ""


def call_llm(vars: dict) -> str | None:
    attempt = 1
    while True:
        for llm in llm_cascade:
            if llm is None:
                continue
            try:
                result = (PARSE_PROMPT | llm).invoke(vars)
                return result.content if hasattr(result, "content") else str(result)
            except Exception as e:
                err_str = str(e)
                print(f"   [LLM] Failed ({type(llm).__name__}): {err_str[:80]}...")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print("   [LLM] Severe Rate limit hit! Sleeping for 60 seconds...")
                    time.sleep(60)
                else:
                    time.sleep(2)
        print(f"   [LLM] All engines failed on attempt {attempt}. Retrying indefinitely to prevent data loss (waiting 30s)...")
        time.sleep(30)
        attempt += 1


def parse_pdf_pair(q_text: str, a_text: str, subject: str, label: str) -> list[dict]:
    """Send chunked Q text + answer context to LLM. Returns list of question dicts."""
    answer_map     = extract_answer_map(a_text) if a_text else {}
    answer_map_str = json.dumps(answer_map) if answer_map else "Not available — infer from solution text."
    print(f"   [KEY] Answer map: {len(answer_map)} entries extracted")

    # 4000-char sliding window with 300-char overlap to fit in strict LLM token limits (like Groq)
    CHUNK  = 4000
    OVERLAP= 300
    chunks = []
    start  = 0
    while start < len(q_text):
        chunks.append(q_text[start:start + CHUNK])
        start += CHUNK - OVERLAP

    # Reduce a_snippet to 5000 chars to prevent 413 Payload Too Large
    a_snippet = a_text[:5000] if a_text else "No answer PDF provided."
    all_qs    = []
    seen      = set()

    print(f"   [PARSE] {len(chunks)} text batches to process for '{label}'")
    for i, chunk in enumerate(chunks):
        print(f"   [PARSE] Batch {i+1}/{len(chunks)}...")
        raw = call_llm({"q_text": chunk, "answer_map": answer_map_str, "a_snippet": a_snippet})
        if not raw:
            print("   [PARSE] No LLM response. Skipping.")
            continue
        try:
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            match = re.search(r"\[.*\]", clean, re.DOTALL)
            if not match:
                print(f"   [PARSE] No JSON array in batch {i+1}.")
                continue
            
            json_str = match.group(0)
            # Basic sanitization for common LLM JSON trailing comma errors
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            
            parsed = json.loads(json_str)
            added  = 0
            for q in parsed:
                qtext = q.get("question", "").strip()
                if not qtext or len(qtext) < 20:
                    continue
                key = qtext.lower()[:100]
                if key in seen:
                    continue
                seen.add(key)
                q["subject"] = subject
                all_qs.append(q)
                added += 1
            print(f"   [PARSE] Got {added} new questions (running total: {len(all_qs)})")
        except json.JSONDecodeError as e:
            print(f"   [PARSE] JSON error in batch {i+1}: {e}. Retrying this batch once...")
            # Fallback retry for malformed JSON
            raw_retry = call_llm({"q_text": chunk, "answer_map": answer_map_str, "a_snippet": a_snippet})
            if raw_retry:
                try:
                    clean_r = re.sub(r"```(?:json)?|```", "", raw_retry).strip()
                    match_r = re.search(r"\[.*\]", clean_r, re.DOTALL)
                    if match_r:
                        parsed_r = json.loads(re.sub(r',\s*]', ']', match_r.group(0)))
                        for q in parsed_r:
                            qtext = q.get("question", "").strip()
                            if qtext and len(qtext) >= 20 and qtext.lower()[:100] not in seen:
                                seen.add(qtext.lower()[:100])
                                q["subject"] = subject
                                all_qs.append(q)
                        print(f"   [PARSE] Retry successful for batch {i+1}.")
                except Exception:
                    print(f"   [PARSE] Retry also failed. Skipping batch {i+1}.")
        
        # Base sleep between batches to prevent rate limits
        time.sleep(5)

    return all_qs


def load_checkpoint() -> set:
    return set(CHECKPOINT.read_text().splitlines()) if CHECKPOINT.exists() else set()

def mark_done(h: str):
    with open(CHECKPOINT, "a") as f:
        f.write(h + "\n")

def q_hash(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


def upsert(questions: list[dict], label: str) -> int:
    db         = SessionLocal()
    checkpoint = load_checkpoint()
    inserted   = 0
    skipped    = 0

    print(f"\n[DB] Storing {len(questions)} parsed questions for '{label}'...")
    for q in questions:
        qtext = q.get("question", "").strip()
        if not qtext:
            skipped += 1; continue

        qh = q_hash(qtext)
        if qh in checkpoint:
            skipped += 1; continue

        options = q.get("options", [])
        if not isinstance(options, list) or len(options) < 2:
            skipped += 1; continue

        # Build rich embed text for semantic + keyword search
        embed_text = (
            f"Subject: {q.get('subject', '')}. "
            f"Topic: {q.get('topic', '')}. "
            f"Question: {qtext}. "
            f"Options: {' | '.join(str(o) for o in options)}. "
            f"Answer: {q.get('correct_option', '')}."
        )
        try:
            vector = EMB.embed_query(embed_text)
        except Exception as e:
            print(f"   [EMBED] Error: {e}")
            skipped += 1; continue

        try:
            entry = UniversalQuestionBank(
                subject        = q.get("subject", label),
                topic          = q.get("topic", "General"),
                question       = qtext,
                options_json   = json.dumps(options, ensure_ascii=False),
                correct_option = str(q.get("correct_option", "")),
                rationale      = q.get("rationale", ""),
                mains_hint     = "",   # filled by Phase 2 enrichment script
                difficulty     = q.get("difficulty", "medium"),
                embedding      = vector,
            )
            db.add(entry)
            db.commit()
            mark_done(qh)
            inserted += 1
            if inserted % 20 == 0:
                print(f"   [DB] ✓ {inserted} inserted...")
        except Exception as e:
            db.rollback()
            print(f"   [DB] Insert error: {e}")
            skipped += 1

    db.close()
    print(f"   [DB] Done → Inserted: {inserted} | Skipped/Dup: {skipped}")
    return inserted


def process_pair(pair: dict) -> int:
    label   = pair["label"]
    subject = pair["subject"]
    q_path  = pair["q"]
    a_path  = pair.get("a")

    print(f"\n{'─'*65}")
    print(f"  {label}  [{subject}]")
    print(f"{'─'*65}")

    if not q_path.exists():
        print(f"  [SKIP] Not found: {q_path.name}")
        return 0

    print(f"  [READ] {q_path.name}")
    q_text = extract_text(q_path)
    a_text = ""
    if a_path and a_path.exists():
        print(f"  [READ] {a_path.name}")
        a_text = extract_text(a_path)
    elif a_path:
        print(f"  [WARN] Answer PDF not found: {a_path.name}")

    if not q_text.strip():
        print("  [SKIP] Empty text extracted.")
        return 0

    print(f"  [TEXT] Q={len(q_text):,} chars | A={len(a_text):,} chars")

    parsed = parse_pdf_pair(q_text, a_text, subject, label)
    print(f"  [TOTAL] Parsed {len(parsed)} questions from '{label}'")

    if not parsed:
        print("  [WARN] Nothing parsed. Skipping DB insert.")
        return 0

    return upsert(parsed, label)


def main():
    total = 0
    print(f"\nProcessing {len(ALL_PAIRS)} PDF pairs...\n")
    for pair in ALL_PAIRS:
        n = process_pair(pair)
        total += n

    db = SessionLocal()
    in_db = db.query(UniversalQuestionBank).count()
    db.close()

    print("\n" + "=" * 70)
    print(f"  ✅  PHASE 1 COMPLETE")
    print(f"     Inserted this run : {total}")
    print(f"     Total in database : {in_db}")
    print("=" * 70)
    print("\nNext: run  python scripts/enrich_mains_hints.py  to add mains hints from books.\n")


if __name__ == "__main__":
    main()
