"""
Quality Audit Script — scans every question in UniversalQuestionBank
and reports how many fail each validation rule.
"""
import sys, io, json, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.models import SessionLocal, UniversalQuestionBank

db = SessionLocal()
qs = db.query(UniversalQuestionBank).all()

issues = {
    'fact_placeholder_options': 0,
    'short_question': 0,
    'no_rationale': 0,
    'no_mains_hint': 0,
    'fewer_than_4_options': 0,
    'option_too_short': 0,
    'question_is_answer': 0,
    'total': len(qs),
}
sample_bad = []

FACT_RE = re.compile(r'^fact\s*\d+$', re.IGNORECASE)
STMT_PLACEHOLDER_RE = re.compile(r'^statement\s*\d+$', re.IGNORECASE)
ANSWER_LEAK_RE = re.compile(
    r'^(Option\s*\([a-d]\)\s*is\s*(in)?correct|'
    r'Both\s*statements?\s*are\s*(in)?correct|'
    r'Statement\s*\d+\s*is\s*(in)?correct|'
    r'Correct\s*Answer)',
    re.IGNORECASE
)

for q in qs:
    reasons = []

    # ── Parse options ──
    opts = []
    try:
        opts = json.loads(q.options_json)
    except Exception:
        reasons.append('bad_json')

    # 1. Placeholder options like "Fact 1", "Fact 2"
    for opt in opts:
        stripped = opt.strip()
        if FACT_RE.match(stripped) or STMT_PLACEHOLDER_RE.match(stripped):
            issues['fact_placeholder_options'] += 1
            reasons.append('fact_placeholder')
            break

    # 2. Fewer than 4 options
    if len(opts) < 4:
        issues['fewer_than_4_options'] += 1
        reasons.append('few_opts')

    # 3. Any option is too short (less than 5 chars)
    for opt in opts:
        if len(opt.strip()) < 5:
            issues['option_too_short'] += 1
            reasons.append('opt_short')
            break

    # 4. Short / empty question
    if len(q.question.strip()) < 30:
        issues['short_question'] += 1
        reasons.append('short_q')

    # 5. Question text starts with an answer leak
    if ANSWER_LEAK_RE.match(q.question.strip()):
        issues['question_is_answer'] += 1
        reasons.append('answer_leak')

    # 6. Missing or too-short rationale
    if not q.rationale or len(q.rationale.strip()) < 20:
        issues['no_rationale'] += 1
        reasons.append('no_rationale')

    # 7. Missing or too-short mains hint
    if not q.mains_hint or len(q.mains_hint.strip()) < 10:
        issues['no_mains_hint'] += 1
        reasons.append('no_mains')

    if reasons and len(sample_bad) < 10:
        sample_bad.append({
            'id': q.id,
            'q': q.question[:120],
            'opts': [o[:80] for o in opts[:4]],
            'reasons': reasons,
        })

db.close()

print("=" * 60)
print(" QUALITY AUDIT REPORT")
print("=" * 60)
print(json.dumps(issues, indent=2))
passing = issues['total'] - len(set(
    s['id'] for s in sample_bad  # approximate; real count below
))
# Re-count properly
fail_ids = set()
db2 = SessionLocal()
for q in db2.query(UniversalQuestionBank).all():
    opts = []
    try:
        opts = json.loads(q.options_json)
    except:
        fail_ids.add(q.id); continue
    for opt in opts:
        s = opt.strip()
        if FACT_RE.match(s) or STMT_PLACEHOLDER_RE.match(s):
            fail_ids.add(q.id); break
    if len(opts) < 4:
        fail_ids.add(q.id)
    for opt in opts:
        if len(opt.strip()) < 5:
            fail_ids.add(q.id); break
    if len(q.question.strip()) < 30:
        fail_ids.add(q.id)
    if ANSWER_LEAK_RE.match(q.question.strip()):
        fail_ids.add(q.id)
    if not q.rationale or len(q.rationale.strip()) < 20:
        fail_ids.add(q.id)
    if not q.mains_hint or len(q.mains_hint.strip()) < 10:
        fail_ids.add(q.id)
db2.close()

print(f"\nTotal questions : {issues['total']}")
print(f"FAIL (any rule) : {len(fail_ids)}")
print(f"PASS (clean)    : {issues['total'] - len(fail_ids)}")

print("\n--- SAMPLE BAD QUESTIONS ---")
for s in sample_bad:
    print(f"\nID {s['id']} | {s['reasons']}")
    print(f"  Q: {s['q']}")
    for i, o in enumerate(s['opts']):
        print(f"  {chr(65+i)}: {o}")
