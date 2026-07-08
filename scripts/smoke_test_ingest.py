# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
Smoke test — validates the extraction pipeline on ONE small PDF pair
before running the full overnight job.
Run: python scripts/smoke_test_ingest.py
"""
import os, sys, json, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import yaml
with open(ROOT / "configs" / "settings.yaml") as f:
    config = yaml.safe_load(f)

from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from src.mcq_generation.generator import llm_cascade
from api.models import SessionLocal, UniversalQuestionBank
import json, hashlib

print("=" * 60)
print(" SMOKE TEST — Single PDF Pair Extraction")
print("=" * 60)

# ── Load 1 small PDF: Vision AMH 1 (Q + Solution) ───────────────────────────
Q_PDF = Path(r"C:\Users\ankus\OneDrive\Desktop\UPSC section wise papers\01 History\Vision AMH 1.pdf")
A_PDF = Path(r"C:\Users\ankus\OneDrive\Desktop\UPSC section wise papers\01 History\Vision AMH 1 solution.pdf")

print(f"\n[1] Loading PDFs...")
q_pages = PyPDFLoader(str(Q_PDF)).load()
a_pages = PyPDFLoader(str(A_PDF)).load()

q_text = "\n".join(p.page_content for p in q_pages)
a_text = "\n".join(p.page_content for p in a_pages)

print(f"    Q-PDF pages: {len(q_pages)} | chars: {len(q_text)}")
print(f"    A-PDF pages: {len(a_pages)} | chars: {len(a_text)}")
print(f"\n[2] Q-text PREVIEW (first 1000 chars):\n")
print(q_text[:1000].encode('ascii', errors='replace').decode('ascii'))
print(f"\n[3] A-text PREVIEW (first 1000 chars):\n")
print(a_text[:1000].encode('ascii', errors='replace').decode('ascii'))

# ── Run LLM on first 4000 chars only ────────────────────────────────────────
PARSE_PROMPT = PromptTemplate.from_template("""
You are a highly precise UPSC MCQ data extractor.

Below is raw text extracted from a UPSC test paper (questions section) and its answer/solution section.
Your task is to extract ALL valid multiple-choice questions as a clean JSON array.

QUESTION TEXT:
{q_text}

ANSWER/SOLUTION TEXT (may contain correct answers and explanations):
{a_text}

EXTRACTION RULES:
1. Extract EVERY question you find. Do NOT skip any.
2. Each entry must have: "question", "options" (array of 4 strings), "correct_option" (the exact text of the correct answer), "rationale" (explanation if available, else derive from context), "topic" (specific sub-topic), "difficulty" ("easy"/"medium"/"hard").
3. For options, use EXACTLY as written in the text (no labels like A/B/C/D - just the text).
4. Return ONLY a valid JSON array. No markdown fences, no extra text.
""")

print(f"\n[4] Sending first 4000 chars to LLM for parsing...")

raw = None
for llm in llm_cascade:
    if llm is None:
        continue
    try:
        chain  = PARSE_PROMPT | llm
        result = chain.invoke({"q_text": q_text[:4000], "a_text": a_text[:3000]})
        raw    = result.content if hasattr(result, "content") else str(result)
        print(f"    LLM responded ({len(raw)} chars)")
        break
    except Exception as e:
        print(f"    LLM failed: {e}")
        time.sleep(3)

if not raw:
    print("[FAIL] No LLM response. Check API keys.")
    sys.exit(1)

print(f"\n[5] RAW LLM OUTPUT (first 2000 chars):\n")
print(raw[:2000].encode('ascii', errors='replace').decode('ascii'))

# ── Parse JSON ───────────────────────────────────────────────────────────────
raw_clean = re.sub(r"```(?:json)?|```", "", raw).strip()
match     = re.search(r"\[.*\]", raw_clean, re.DOTALL)

if not match:
    print("\n[FAIL] Could not find JSON array in LLM output. Check prompting.")
    sys.exit(1)

parsed = json.loads(match.group(0))
print(f"\n[6] Successfully parsed {len(parsed)} questions!")

for i, q in enumerate(parsed[:3]):
    print(f"\n  Q{i+1}: {q.get('question', '')[:100]}")
    print(f"       Options: {q.get('options', [])}")
    print(f"       Correct: {q.get('correct_option', '')}")
    print(f"       Topic:   {q.get('topic', '')}")

# ── Test Embedding ───────────────────────────────────────────────────────────
print(f"\n[7] Testing embedding on first question...")
embeddings_model = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
first_q  = parsed[0]
embed_text = f"Subject: Ancient History. Topic: {first_q.get('topic','general')}. Question: {first_q['question']}"
vector   = embeddings_model.embed_query(embed_text)
print(f"    Vector shape: {len(vector)} dims ✓")

# ── Test DB Insert ───────────────────────────────────────────────────────────
print(f"\n[8] Test-inserting first question into DB...")
db = SessionLocal()
q_hash = hashlib.md5(first_q["question"].strip().lower().encode()).hexdigest()
existing = db.query(UniversalQuestionBank).filter(UniversalQuestionBank.question == first_q["question"]).first()

if existing:
    print("    Question already exists in DB — dedup working ✓")
else:
    entry = UniversalQuestionBank(
        subject        = "Ancient and Medieval History",
        topic          = first_q.get("topic", "General"),
        question       = first_q["question"],
        options_json   = json.dumps(first_q.get("options", []), ensure_ascii=False),
        correct_option = str(first_q.get("correct_option", "")),
        rationale      = first_q.get("rationale", ""),
        mains_hint     = "",
        difficulty     = first_q.get("difficulty", "medium"),
        embedding      = vector,
    )
    db.add(entry)
    db.commit()
    print(f"    ✓ Question inserted into DB successfully!")

total = db.query(UniversalQuestionBank).count()
db.close()

print(f"\n[9] Total questions in DB now: {total}")
print(f"\n{'='*60}")
print(f" ✅ SMOKE TEST PASSED — Pipeline is working correctly!")
print(f"    Now run: python scripts/ingest_question_bank.py")
print(f"{'='*60}\n")
