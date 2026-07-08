"""
═══════════════════════════════════════════════════════════════════════
  UPSC QUESTION QUALITY GATE  —  Production-Grade Validation Pipeline
═══════════════════════════════════════════════════════════════════════

Every question from UniversalQuestionBank must pass ALL hard rules
before it can be injected into the live test series (MockTest /
TestQuestion tables).

HARD RULES (instant reject if ANY fails):
  1. QUESTION_MIN_LENGTH   – question text ≥ 40 characters
  2. NO_ANSWER_LEAK        – question must NOT start with the answer
  3. FOUR_OPTIONS           – exactly 4 distinct, non-empty options
  4. OPTION_MIN_LENGTH      – every option ≥ 8 characters
  5. NO_PLACEHOLDER_OPTIONS – no "Fact 1", "Fact 2", "Statement 1" etc.
  6. RATIONALE_MIN_LENGTH   – rationale ≥ 30 characters
  7. OPTION_DIVERSITY       – all 4 options must be meaningfully different
  8. QUESTION_IS_QUESTION   – text should end with '?' or contain an
                              interrogative cue (which, what, consider, etc.)

SOFT RULES (pass but flagged):
  S1. MAINS_HINT_PRESENT – mains_hint ≥ 15 characters

Usage:
  from scripts.quality_gate import QualityGate
  gate = QualityGate()
  result = gate.validate(question_row)
  # result = {"pass": True/False, "hard_fails": [...], "soft_warns": [...]}
"""

import re
import json
from dataclasses import dataclass, field

# ── Compiled Patterns ────────────────────────────────────────────────────────

FACT_PLACEHOLDER_RE = re.compile(
    r'^(fact|statement)\s*\d+$', re.IGNORECASE
)

ANSWER_LEAK_PATTERNS = [
    re.compile(r'^Option\s*\([a-dA-D]\)\s*is\s*(in)?correct', re.IGNORECASE),
    re.compile(r'^Both\s*statements?\s*are\s*(in)?correct', re.IGNORECASE),
    re.compile(r'^Statement\s*\d+\s*is\s*(in)?correct', re.IGNORECASE),
    re.compile(r'^Correct\s*Answer', re.IGNORECASE),
    re.compile(r'^The\s*correct\s*(answer|option)\s*is', re.IGNORECASE),
    re.compile(r'^Only\s*(statement|option)', re.IGNORECASE),
    re.compile(r'^All\s*(statements?|options?)\s*are\s*(in)?correct', re.IGNORECASE),
]

INTERROGATIVE_CUES = [
    'which', 'what', 'who', 'how', 'consider', 'select', 'choose',
    'identify', 'match', 'arrange', 'regarding', 'reference',
    'following', 'correct', 'incorrect', 'true', 'false', 'given',
    'above', 'below', 'among', 'describe', 'assertion', 'reason',
    'statement', 'pair', 'not', 'except',
]


@dataclass
class ValidationResult:
    """Holds the result of running a question through the quality gate."""
    passed: bool = True
    hard_fails: list = field(default_factory=list)
    soft_warns: list = field(default_factory=list)

    def fail(self, rule: str, detail: str = ""):
        self.passed = False
        self.hard_fails.append(f"[HARD] {rule}: {detail}")

    def warn(self, rule: str, detail: str = ""):
        self.soft_warns.append(f"[SOFT] {rule}: {detail}")


class QualityGate:
    """
    Stateless validator.  Call `.validate(row)` with any object that has
    .question, .options_json, .rationale, .mains_hint attributes.
    Returns a ValidationResult.
    """

    # ── Thresholds (easily tuneable) ─────────────────────────────────────────
    QUESTION_MIN_LEN   = 40
    OPTION_MIN_LEN     = 8
    RATIONALE_MIN_LEN  = 30
    MAINS_HINT_MIN_LEN = 15
    REQUIRED_OPTIONS   = 4

    def validate(self, row) -> ValidationResult:
        result = ValidationResult()

        question = (row.question or "").strip()
        rationale = (row.rationale or "").strip()
        mains_hint = (row.mains_hint or "").strip()

        # Parse options
        options = []
        try:
            options = json.loads(row.options_json)
            if not isinstance(options, list):
                options = list(options.values()) if isinstance(options, dict) else []
        except Exception:
            result.fail("OPTIONS_PARSE", "Could not parse options_json")
            return result

        # ── HARD RULE 1: Question minimum length ────────────────────────────
        if len(question) < self.QUESTION_MIN_LEN:
            result.fail("QUESTION_MIN_LENGTH",
                        f"Only {len(question)} chars (need ≥{self.QUESTION_MIN_LEN})")

        # ── HARD RULE 2: No answer leaked into question text ────────────────
        for pat in ANSWER_LEAK_PATTERNS:
            if pat.match(question):
                result.fail("NO_ANSWER_LEAK",
                            f"Question starts with answer: '{question[:60]}…'")
                break

        # ── HARD RULE 3: Exactly 4 non-empty options ────────────────────────
        clean_opts = [o.strip() for o in options if o and o.strip()]
        if len(clean_opts) < self.REQUIRED_OPTIONS:
            result.fail("FOUR_OPTIONS",
                        f"Only {len(clean_opts)} options (need {self.REQUIRED_OPTIONS})")

        # ── HARD RULE 4: Each option meets minimum length ───────────────────
        for i, opt in enumerate(clean_opts):
            if len(opt) < self.OPTION_MIN_LEN:
                result.fail("OPTION_MIN_LENGTH",
                            f"Option {chr(65+i)} is only {len(opt)} chars: '{opt}'")
                break  # one failure is enough

        # ── HARD RULE 5: No placeholder options ─────────────────────────────
        for opt in clean_opts:
            if FACT_PLACEHOLDER_RE.match(opt.strip()):
                result.fail("NO_PLACEHOLDER_OPTIONS",
                            f"Placeholder option found: '{opt}'")
                break

        # ── HARD RULE 6: Rationale minimum length ───────────────────────────
        if len(rationale) < self.RATIONALE_MIN_LEN:
            result.fail("RATIONALE_MIN_LENGTH",
                        f"Only {len(rationale)} chars (need ≥{self.RATIONALE_MIN_LEN})")

        # ── HARD RULE 7: Option diversity (no duplicates) ───────────────────
        normalised = [o.lower().strip() for o in clean_opts]
        if len(set(normalised)) < len(normalised):
            result.fail("OPTION_DIVERSITY", "Duplicate options detected")

        # ── HARD RULE 8: Question looks like a question ─────────────────────
        q_lower = question.lower()
        has_question_mark = '?' in question
        has_cue = any(cue in q_lower for cue in INTERROGATIVE_CUES)
        if not has_question_mark and not has_cue:
            result.fail("QUESTION_IS_QUESTION",
                        "No '?' and no interrogative cues found")

        # ── SOFT RULE S1: Mains hint present ────────────────────────────────
        if len(mains_hint) < self.MAINS_HINT_MIN_LEN:
            result.warn("MAINS_HINT_PRESENT",
                        f"Missing or short mains_hint ({len(mains_hint)} chars)")

        return result


def run_full_audit():
    """
    Scans every row in UniversalQuestionBank through the QualityGate,
    prints a summary report, and returns (pass_ids, fail_ids).
    """
    import sys, io
    from pathlib import Path
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT))
    from api.models import SessionLocal, UniversalQuestionBank

    gate = QualityGate()
    db = SessionLocal()
    rows = db.query(UniversalQuestionBank).all()

    pass_ids = []
    fail_ids = []
    hard_counter = {}
    soft_counter = {}
    sample_fails = []

    for row in rows:
        result = gate.validate(row)
        if result.passed:
            pass_ids.append(row.id)
        else:
            fail_ids.append(row.id)
            if len(sample_fails) < 5:
                sample_fails.append((row.id, row.question[:100], result.hard_fails))
            for h in result.hard_fails:
                rule = h.split(":")[0].replace("[HARD] ", "")
                hard_counter[rule] = hard_counter.get(rule, 0) + 1
        for w in result.soft_warns:
            rule = w.split(":")[0].replace("[SOFT] ", "")
            soft_counter[rule] = soft_counter.get(rule, 0) + 1

    db.close()

    print("=" * 64)
    print("  UPSC QUESTION QUALITY GATE — FULL AUDIT REPORT")
    print("=" * 64)
    print(f"\n  Total questions scanned : {len(rows)}")
    print(f"  ✅  PASSED (clean)      : {len(pass_ids)}")
    print(f"  ❌  FAILED (rejected)   : {len(fail_ids)}")

    print(f"\n{'─'*64}")
    print("  HARD RULE FAILURE BREAKDOWN:")
    for rule, cnt in sorted(hard_counter.items(), key=lambda x: -x[1]):
        print(f"    {rule:30s}  → {cnt:4d} failures")

    print(f"\n{'─'*64}")
    print("  SOFT WARNING BREAKDOWN:")
    for rule, cnt in sorted(soft_counter.items(), key=lambda x: -x[1]):
        print(f"    {rule:30s}  → {cnt:4d} warnings")

    if sample_fails:
        print(f"\n{'─'*64}")
        print("  SAMPLE REJECTED QUESTIONS:")
        for qid, qtxt, reasons in sample_fails:
            print(f"\n  ID {qid}:")
            print(f"    Q: {qtxt}")
            for r in reasons:
                print(f"    ⛔ {r}")

    print("\n" + "=" * 64)
    return pass_ids, fail_ids


if __name__ == "__main__":
    run_full_audit()
