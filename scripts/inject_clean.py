"""
═══════════════════════════════════════════════════════════════════════
  CLEAN INJECTION PIPELINE
═══════════════════════════════════════════════════════════════════════
  1. Wipes any existing MockTest ID 100 + its TestQuestion children.
  2. Runs every UniversalQuestionBank row through QualityGate.
  3. Injects ONLY the rows that PASS all 8 hard rules.
  4. Sanitises the question text (strips answer leaks).
  5. Creates separate MockTest entries for History and Art & Culture.
═══════════════════════════════════════════════════════════════════════
"""
import sys, io, json, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.models import SessionLocal, UniversalQuestionBank, MockTest, TestQuestion
from scripts.quality_gate import QualityGate

# ── Sanitise question text ───────────────────────────────────────────────────
ANSWER_LEAK_STRIP = re.compile(
    r'^(?:Option\s*\([a-d]\)\s*is\s*(?:in)?correct[^:]*:\s*)|'
    r'^(?:Both\s*statements?\s*are\s*(?:in)?correct\s*:\s*)|'
    r'^(?:Statement\s*\d+\s*is\s*(?:in)?correct\s*:\s*)|'
    r'^(?:Correct\s*Answer[^:]*:\s*Option\s*\([a-d]\)[^.]*\.\s*)|'
    r'^(?:The\s*correct\s*(?:answer|option)\s*is[^:]*:\s*)',
    re.IGNORECASE
)

# Strips "Q5:", "Q10.", "Question 3:" etc. from the start of question text
Q_NUMBER_PREFIX = re.compile(
    r'^(?:Q(?:uestion)?\s*\d+\s*[.:]\s*)', re.IGNORECASE
)

def sanitise_question(text: str) -> str:
    """Strip answer-leak prefixes and question-number prefixes from the question text."""
    text = ANSWER_LEAK_STRIP.sub('', text).strip()
    text = Q_NUMBER_PREFIX.sub('', text).strip()
    return text


def map_correct_option_to_letter(correct_text: str, options_dict: dict) -> str:
    """
    Given the correct option's full text and the {a: ..., b: ..., c: ..., d: ...}
    dict, return the matching letter key.  Falls back to 'a' if no match.
    """
    if not correct_text:
        return "a"
    ct = correct_text.strip().lower()
    for key, val in options_dict.items():
        if val.strip().lower() == ct:
            return key
    # Partial match fallback
    for key, val in options_dict.items():
        if ct in val.strip().lower() or val.strip().lower() in ct:
            return key
    return "a"


def run():
    gate = QualityGate()
    db = SessionLocal()

    # ── Step 1: Wipe old injected tests ──────────────────────────────────────
    for test_id in [100, 101, 102]:
        db.query(TestQuestion).filter(TestQuestion.test_id == test_id).delete()
        db.query(MockTest).filter(MockTest.id == test_id).delete()
    db.commit()
    print("[CLEANUP] Removed old MockTest 100/101/102 and their questions.")

    # ── Step 2: Validate everything ──────────────────────────────────────────
    all_rows = db.query(UniversalQuestionBank).all()
    
    history_qs = []
    artculture_qs = []
    
    pass_count = 0
    fail_count = 0
    
    for row in all_rows:
        result = gate.validate(row)
        if not result.passed:
            fail_count += 1
            continue
        pass_count += 1
        
        # Classify by subject
        subj = (row.subject or "").lower()
        if any(kw in subj for kw in ['art', 'culture']):
            artculture_qs.append(row)
        elif any(kw in subj for kw in ['history', 'ancient', 'medieval', 'modern']):
            history_qs.append(row)
        else:
            # If unclear, put in history as default for this batch
            history_qs.append(row)

    print(f"[QUALITY GATE] {pass_count} PASSED | {fail_count} FAILED")
    print(f"[CLASSIFY] History: {len(history_qs)} | Art & Culture: {len(artculture_qs)}")

    # ── Step 3: Inject History Test (ID 101) ─────────────────────────────────
    if history_qs:
        batch = history_qs[:50]  # cap at 50 per test
        test_h = MockTest(
            id=101,
            topic="History — Subject Wise Test",
            count=len(batch),
            paper_type="Subject-Wise"
        )
        db.add(test_h)
        db.commit()

        for q in batch:
            opts_list = json.loads(q.options_json)
            opts_dict = {}
            for i, opt in enumerate(opts_list[:4]):
                opts_dict[chr(97 + i)] = opt  # a, b, c, d

            correct_letter = map_correct_option_to_letter(q.correct_option, opts_dict)
            cleaned_q = sanitise_question(q.question)

            tq = TestQuestion(
                test_id=101,
                question=cleaned_q,
                options_json=json.dumps(opts_dict),
                correct_option=correct_letter,
                rationale=q.rationale or "",
                mains_hint=q.mains_hint or "Refer to standard NCERT and reference material for mains-level depth on this topic.",
                subject=q.subject,
                difficulty=q.difficulty or "medium"
            )
            db.add(tq)

        db.commit()
        print(f"[INJECT] ✅ History test (ID 101) created with {len(batch)} verified questions.")

    # ── Step 4: Inject Art & Culture Test (ID 102) ───────────────────────────
    if artculture_qs:
        batch = artculture_qs[:50]
        test_ac = MockTest(
            id=102,
            topic="Art & Culture — Subject Wise Test",
            count=len(batch),
            paper_type="Subject-Wise"
        )
        db.add(test_ac)
        db.commit()

        for q in batch:
            opts_list = json.loads(q.options_json)
            opts_dict = {}
            for i, opt in enumerate(opts_list[:4]):
                opts_dict[chr(97 + i)] = opt

            correct_letter = map_correct_option_to_letter(q.correct_option, opts_dict)
            cleaned_q = sanitise_question(q.question)

            tq = TestQuestion(
                test_id=102,
                question=cleaned_q,
                options_json=json.dumps(opts_dict),
                correct_option=correct_letter,
                rationale=q.rationale or "",
                mains_hint=q.mains_hint or "Refer to standard NCERT and reference material for mains-level depth on this topic.",
                subject=q.subject,
                difficulty=q.difficulty or "medium"
            )
            db.add(tq)

        db.commit()
        print(f"[INJECT] ✅ Art & Culture test (ID 102) created with {len(batch)} verified questions.")

    # ── Step 5: Also create combined test (ID 100) ───────────────────────────
    combined = (history_qs + artculture_qs)[:50]
    if combined:
        test_combo = MockTest(
            id=100,
            topic="History & Art and Culture — Combined Test",
            count=len(combined),
            paper_type="Subject-Wise"
        )
        db.add(test_combo)
        db.commit()

        for q in combined:
            opts_list = json.loads(q.options_json)
            opts_dict = {}
            for i, opt in enumerate(opts_list[:4]):
                opts_dict[chr(97 + i)] = opt

            correct_letter = map_correct_option_to_letter(q.correct_option, opts_dict)
            cleaned_q = sanitise_question(q.question)

            tq = TestQuestion(
                test_id=100,
                question=cleaned_q,
                options_json=json.dumps(opts_dict),
                correct_option=correct_letter,
                rationale=q.rationale or "",
                mains_hint=q.mains_hint or "Refer to standard NCERT and reference material for mains-level depth on this topic.",
                subject=q.subject,
                difficulty=q.difficulty or "medium"
            )
            db.add(tq)

        db.commit()
        print(f"[INJECT] ✅ Combined test (ID 100) created with {len(combined)} verified questions.")

    db.close()
    print("\n[DONE] Clean injection pipeline completed successfully.")


if __name__ == "__main__":
    run()
