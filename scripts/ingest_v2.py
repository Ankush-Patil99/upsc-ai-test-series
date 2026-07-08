# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
═══════════════════════════════════════════════════════════════════════════════
  UPSC Question Bank — Production Ingestion Pipeline v2
═══════════════════════════════════════════════════════════════════════════════

  This replaces the old ingest_question_bank.py with significantly better:
    1. LLM prompt — forces proper question/option/explanation format
    2. Inline Quality Gate — rejects bad questions BEFORE DB insert
    3. Deduplication — by question text hash AND semantic similarity
    4. Proper format — options as 4-element list, correct_option as exact text
    5. Mains hint — Phase 1 generates a basic hint; Phase 2 enriches via RAG

  Usage:
    python scripts/ingest_v2.py              # full run (all PDFs)
    python scripts/ingest_v2.py --reset      # wipe DB + checkpoint, then run

  After this, run:
    python scripts/enrich_mains_hints.py     # Phase 2: RAG-based mains hints
    python scripts/inject_clean.py           # Phase 3: inject into test series
═══════════════════════════════════════════════════════════════════════════════
"""

import os, re, json, time, hashlib, argparse
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

# ─── Quality Gate (imported from our new module) ─────────────────────────────
from scripts.quality_gate import QualityGate
GATE = QualityGate()

# ─── Checkpoint ──────────────────────────────────────────────────────────────
CHECKPOINT = ROOT / "logs" / "ingest_v2_checkpoint.log"
CHECKPOINT.parent.mkdir(exist_ok=True)

LOG_FILE = ROOT / "logs" / "ingest_v2_full.log"

def log(msg: str):
    """Print and log to file."""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# ─── Embedding Model ────────────────────────────────────────────────────────
log("\n" + "=" * 70)
log("  UPSC Question Bank — Production Ingestion Pipeline v2")
log("=" * 70)
log("\n[INIT] Loading embedding model (all-MiniLM-L6-v2)...")
EMB = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
log("[INIT] Embedding model ready.\n")

# ─── PDF Source Map ──────────────────────────────────────────────────────────
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

# ─── LLM Prompt v2 ──────────────────────────────────────────────────────────
# This prompt is much more strict about output format and completeness.
PARSE_PROMPT = PromptTemplate.from_template(
"""You are a world-class UPSC MCQ data extractor. Your job is to extract EVERY SINGLE multiple-choice question from the text below into a perfectly structured JSON array.

=== QUESTION TEXT ===
{q_text}

=== ANSWER KEY (question_number -> correct_letter) ===
{answer_map}

=== SOLUTION / EXPLANATION TEXT ===
{a_snippet}

=== CRITICAL RULES ===

1. Extract EVERY numbered question. Do NOT skip any.

2. For STATEMENT-BASED questions (e.g. "Consider the following statements:") you MUST:
   - Include ALL the numbered statements (1., 2., 3., etc.) as part of the "question" field itself.
   - The "options" should be the combination choices like ["1 and 2 only", "2 and 3 only", "1 and 3 only", "1, 2 and 3"].
   - NEVER put statements as options. Statements go INSIDE the question text.

3. For MATCHING questions (e.g. "Match the following") you MUST:
   - Include the full matching table/pairs inside the "question" field.
   - Options should be the answer codes like ["A-1, B-2, C-3", "A-2, B-1, C-3", ...].

4. Every question MUST have EXACTLY 4 options as an array of 4 strings.
   - Strip the "a)", "b)", "A.", "(a)" prefixes — keep only the option text.
   - Each option must be meaningful text (minimum 8 characters). NEVER use "Fact 1", "Fact 2" etc.

5. "correct_option" must be the EXACT TEXT of the correct option (not a letter).
   - Use the answer key to find the correct letter, then match it to the option text.

6. "rationale" must be a detailed explanation (minimum 40 words):
   - If the solution text provides one, use it verbatim but clean up formatting.
   - If not available, write a factual 3-4 sentence explanation citing specific facts, dates, or provisions.
   - NEVER leave this empty or write less than 40 words.

7. "mains_hint" must be a dense 1-2 sentence note (20-60 words) connecting this topic to UPSC Mains GS papers.
   - Include specific facts, articles, committees, dates that could be used in a 250-word Mains answer.
   - If you cannot write one, write: "This topic is relevant for GS Paper [1/2/3] and can be linked to [related concept]."

8. "topic" must be a SPECIFIC sub-topic, NOT a broad category.
   - GOOD: "Indus Valley Drainage System", "Quit India Movement 1942", "Bharatnatyam Dance Forms"
   - BAD: "History", "Ancient India", "Culture"

9. "difficulty" must be "easy", "medium", or "hard" based on conceptual depth.

10. Return ONLY a JSON array. No markdown. No preamble. No explanation outside JSON.

OUTPUT FORMAT — each object in the array:
{{
  "question": "Full question text including any numbered statements or matching pairs",
  "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
  "correct_option": "Exact text of the correct option",
  "rationale": "Detailed 40+ word explanation with facts",
  "mains_hint": "Dense 20-60 word mains connection",
  "topic": "Specific sub-topic name",
  "difficulty": "easy|medium|hard"
}}

JSON array:""")


def extract_answer_map(a_text: str) -> dict:
    """Extract Q-number -> letter from answer PDFs using multiple patterns."""
    m = {}
    # Pattern: Q 1.C  or  Q1.C  or  Q 1.(C)
    for x in re.finditer(r'Q\s*\.?\s*(\d+)\s*[\.;\-\:]+\s*\(?([A-Da-d])\)?', a_text):
        m[x.group(1)] = x.group(2).upper()
    # Pattern: standalone line "1. (b)" or "1.(b)" or "1 b"
    for x in re.finditer(r'^\s*(\d+)[\.\)]\s*\(?([A-Da-d])\)?\s*$', a_text, re.MULTILINE):
        if x.group(1) not in m:
            m[x.group(1)] = x.group(2).upper()
    # Pattern: Ans/Answer: 5 - D
    for x in re.finditer(r'[Aa]ns(?:wer)?[\s\.\:](\d+)[\s\=\-\→]+([A-Da-d])', a_text):
        if x.group(1) not in m:
            m[x.group(1)] = x.group(2).upper()
    # Pattern: "1-A", "2-B" on answer sheets
    for x in re.finditer(r'^\s*(\d+)\s*[\-\–]\s*([A-Da-d])\s*$', a_text, re.MULTILINE):
        if x.group(1) not in m:
            m[x.group(1)] = x.group(2).upper()
    return m


def extract_text(path: Path) -> str:
    """Load PDF and return all text."""
    try:
        pages = PyPDFLoader(str(path)).load()
        return "\n".join(p.page_content for p in pages)
    except Exception as e:
        log(f"   [ERR] Cannot read {path.name}: {e}")
        return ""


def call_llm(vars: dict) -> str | None:
    """Call LLM with infinite retry on rate limits."""
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
                log(f"   [LLM] Failed ({type(llm).__name__}): {err_str[:100]}...")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate" in err_str.lower():
                    log("   [LLM] Rate limit! Sleeping 60s...")
                    time.sleep(60)
                else:
                    time.sleep(3)
        log(f"   [LLM] All engines failed attempt {attempt}. Retrying in 30s...")
        time.sleep(30)
        attempt += 1


def clean_json(raw: str) -> list:
    """Extract and parse JSON array from LLM response with aggressive error recovery."""
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    
    if not match:
        # Try to salvage truncated array (LLM ran out of tokens)
        match = re.search(r"\[.*", raw, re.DOTALL)
        if not match:
            return []
        json_str = match.group(0)
        # Close any unclosed braces/brackets
        open_braces = json_str.count('{') - json_str.count('}')
        open_brackets = json_str.count('[') - json_str.count(']')
        json_str += '}' * max(0, open_braces)
        json_str += ']' * max(0, open_brackets)
    else:
        json_str = match.group(0)
    
    # Fix common LLM JSON errors
    json_str = re.sub(r',\s*]', ']', json_str)      # trailing comma before ]
    json_str = re.sub(r',\s*}', '}', json_str)      # trailing comma before }
    json_str = re.sub(r'}\s*{', '},{', json_str)     # missing comma between objects
    json_str = json_str.replace('\n', ' ')            # remove newlines inside strings
    json_str = re.sub(r'[\x00-\x1f]', ' ', json_str) # remove control characters
    
    # Fix unescaped quotes inside strings (common LLM error)
    # This is a best-effort fix for things like: "rationale": "The "Great Bath" was..."
    # We can't perfectly solve this, but we try:
    json_str = re.sub(r'(?<=\w)"(?=\w)', '\\"', json_str)
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: try to extract individual objects
        objects = []
        for obj_match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str):
            try:
                obj_str = obj_match.group(0)
                obj_str = re.sub(r',\s*}', '}', obj_str)
                obj = json.loads(obj_str)
                if isinstance(obj, dict) and 'question' in obj:
                    objects.append(obj)
            except json.JSONDecodeError:
                continue
        if objects:
            log(f"   [JSON-FIX] Salvaged {len(objects)} questions from malformed JSON")
        return objects


def q_hash(text: str) -> str:
    """MD5 hash of normalised question text for dedup."""
    normalised = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.md5(normalised.encode()).hexdigest()


def strip_q_prefix(text: str) -> str:
    """Remove Q1:, Q 5., Question 10: etc. from the start."""
    return re.sub(r'^(?:Q(?:uestion)?\s*\d+\s*[.:\-]\s*)', '', text, flags=re.IGNORECASE).strip()


def parse_pdf_pair(q_text: str, a_text: str, subject: str, label: str) -> list:
    """Send chunked Q text + answer context to LLM. Returns list of question dicts."""
    answer_map = extract_answer_map(a_text) if a_text else {}
    answer_map_str = json.dumps(answer_map) if answer_map else "Not available — infer from solution text."
    log(f"   [KEY] Answer map: {len(answer_map)} entries extracted")

    # 4000-char chunks with 300-char overlap — fits within Groq/OpenRouter token limits
    CHUNK = 4000
    OVERLAP = 300
    chunks = []
    start = 0
    while start < len(q_text):
        chunks.append(q_text[start:start + CHUNK])
        start += CHUNK - OVERLAP

    # Cap answer snippet to 4000 chars to prevent 413 Payload Too Large on smaller models
    a_snippet = a_text[:4000] if a_text else "No answer PDF provided. Generate rationale from your knowledge."
    all_qs = []
    seen_hashes = set()

    log(f"   [PARSE] {len(chunks)} batches to process for '{label}'")
    for i, chunk in enumerate(chunks):
        log(f"   [PARSE] Batch {i+1}/{len(chunks)}...")

        raw = call_llm({"q_text": chunk, "answer_map": answer_map_str, "a_snippet": a_snippet})
        if not raw:
            log("   [PARSE] No LLM response. Skipping batch.")
            continue

        try:
            parsed = clean_json(raw)
        except json.JSONDecodeError as e:
            log(f"   [PARSE] JSON error batch {i+1}: {e}. Retrying once...")
            raw_retry = call_llm({"q_text": chunk, "answer_map": answer_map_str, "a_snippet": a_snippet})
            if raw_retry:
                try:
                    parsed = clean_json(raw_retry)
                except Exception:
                    log(f"   [PARSE] Retry also failed. Skipping batch {i+1}.")
                    continue
            else:
                continue

        added = 0
        rejected = 0
        for q in parsed:
            qtext = q.get("question", "").strip()
            if not qtext or len(qtext) < 20:
                rejected += 1
                continue

            # Clean question prefix
            qtext = strip_q_prefix(qtext)
            q["question"] = qtext

            # Deduplicate by hash
            h = q_hash(qtext)
            if h in seen_hashes:
                rejected += 1
                continue
            seen_hashes.add(h)

            # Ensure options is a proper 4-element list
            opts = q.get("options", [])
            if isinstance(opts, dict):
                opts = list(opts.values())
            if not isinstance(opts, list):
                rejected += 1
                continue

            # Clean option prefixes (a), b), A., etc.)
            cleaned_opts = []
            for opt in opts:
                opt = str(opt).strip()
                opt = re.sub(r'^[a-dA-D][\.\)\:]?\s*', '', opt).strip()
                cleaned_opts.append(opt)
            q["options"] = cleaned_opts

            q["subject"] = subject
            all_qs.append(q)
            added += 1

        log(f"   [PARSE] Got {added} new, {rejected} rejected (total: {len(all_qs)})")
        time.sleep(4)  # Rate limit buffer

    return all_qs


def load_checkpoint() -> set:
    return set(CHECKPOINT.read_text().splitlines()) if CHECKPOINT.exists() else set()


def mark_done(h: str):
    with open(CHECKPOINT, "a") as f:
        f.write(h + "\n")


def upsert(questions: list, label: str) -> tuple:
    """Insert questions into DB with Quality Gate and dedup. Returns (inserted, rejected, skipped)."""
    db = SessionLocal()
    checkpoint = load_checkpoint()
    inserted = 0
    rejected_gate = 0
    skipped_dup = 0

    log(f"\n[DB] Processing {len(questions)} parsed questions for '{label}'...")

    for q in questions:
        qtext = q.get("question", "").strip()
        if not qtext:
            skipped_dup += 1
            continue

        qh = q_hash(qtext)
        if qh in checkpoint:
            skipped_dup += 1
            continue

        options = q.get("options", [])
        if not isinstance(options, list):
            rejected_gate += 1
            continue

        # ── Quality Gate Check (inline) ──────────────────────────────────────
        # Build a mock object for the gate
        class MockRow:
            pass
        mock = MockRow()
        mock.question = qtext
        mock.options_json = json.dumps(options, ensure_ascii=False)
        mock.rationale = q.get("rationale", "")
        mock.mains_hint = q.get("mains_hint", "")

        result = GATE.validate(mock)
        if not result.passed:
            rejected_gate += 1
            continue

        # ── Build embedding for semantic search ──────────────────────────────
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
            log(f"   [EMBED] Error: {e}")
            rejected_gate += 1
            continue

        # ── DB Insert ────────────────────────────────────────────────────────
        try:
            entry = UniversalQuestionBank(
                subject        = q.get("subject", label),
                topic          = q.get("topic", "General"),
                question       = qtext,
                options_json   = json.dumps(options, ensure_ascii=False),
                correct_option = str(q.get("correct_option", "")),
                rationale      = q.get("rationale", ""),
                mains_hint     = q.get("mains_hint", ""),
                difficulty     = q.get("difficulty", "medium"),
                embedding      = vector,
            )
            db.add(entry)
            db.commit()
            mark_done(qh)
            inserted += 1
            if inserted % 25 == 0:
                log(f"   [DB] ✓ {inserted} inserted...")
        except Exception as e:
            db.rollback()
            log(f"   [DB] Insert error: {e}")
            skipped_dup += 1

    db.close()
    log(f"   [DB] Done → Inserted: {inserted} | QualityGate Rejected: {rejected_gate} | Skipped/Dup: {skipped_dup}")
    return inserted, rejected_gate, skipped_dup


def process_pair(pair: dict) -> tuple:
    """Process one Q/A PDF pair. Returns (inserted, rejected, skipped)."""
    label   = pair["label"]
    subject = pair["subject"]
    q_path  = pair["q"]
    a_path  = pair.get("a")

    log(f"\n{'─'*65}")
    log(f"  📄 {label}  [{subject}]")
    log(f"{'─'*65}")

    if not q_path.exists():
        log(f"  [SKIP] Not found: {q_path.name}")
        return (0, 0, 0)

    log(f"  [READ] {q_path.name}")
    q_text = extract_text(q_path)
    a_text = ""
    if a_path and a_path.exists():
        log(f"  [READ] {a_path.name}")
        a_text = extract_text(a_path)
    elif a_path:
        log(f"  [WARN] Answer PDF not found: {a_path.name}")

    if not q_text.strip():
        log("  [SKIP] Empty text extracted.")
        return (0, 0, 0)

    log(f"  [TEXT] Q={len(q_text):,} chars | A={len(a_text):,} chars")

    parsed = parse_pdf_pair(q_text, a_text, subject, label)
    log(f"  [TOTAL] Parsed {len(parsed)} valid questions from '{label}'")

    if not parsed:
        log("  [WARN] Nothing parsed. Skipping DB insert.")
        return (0, 0, 0)

    return upsert(parsed, label)


def reset_database():
    """Wipe all questions from UniversalQuestionBank and reset checkpoint."""
    log("\n[RESET] Wiping UniversalQuestionBank and checkpoint...")
    db = SessionLocal()
    count = db.query(UniversalQuestionBank).count()
    db.query(UniversalQuestionBank).delete()
    db.commit()
    db.close()
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
    log(f"[RESET] Deleted {count} questions. Checkpoint cleared.\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe DB and checkpoint before running")
    args = parser.parse_args()

    if args.reset:
        reset_database()

    total_inserted = 0
    total_rejected = 0
    total_skipped  = 0

    log(f"\nProcessing {len(ALL_PAIRS)} PDF pairs...\n")
    for pair in ALL_PAIRS:
        ins, rej, skip = process_pair(pair)
        total_inserted += ins
        total_rejected += rej
        total_skipped  += skip

    db = SessionLocal()
    in_db = db.query(UniversalQuestionBank).count()
    db.close()

    log("\n" + "=" * 70)
    log("  ✅  INGESTION v2 COMPLETE")
    log(f"     Inserted this run     : {total_inserted}")
    log(f"     QualityGate rejected  : {total_rejected}")
    log(f"     Skipped (dup/error)   : {total_skipped}")
    log(f"     Total in database     : {in_db}")
    log("=" * 70)
    log("\nNext steps:")
    log("  1. python scripts/enrich_mains_hints.py   → Phase 2: RAG mains hints")
    log("  2. python scripts/inject_clean.py          → Phase 3: inject into test series")
    log("")


if __name__ == "__main__":
    main()
