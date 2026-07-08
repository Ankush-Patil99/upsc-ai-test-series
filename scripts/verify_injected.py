import sys, io, json
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.models import SessionLocal, TestQuestion

db = SessionLocal()

for test_id, label in [(101, 'HISTORY'), (102, 'ART & CULTURE')]:
    qs = db.query(TestQuestion).filter(TestQuestion.test_id == test_id).all()
    sep = "=" * 60
    print()
    print(sep)
    print("  {} TEST (ID {}) - {} questions".format(label, test_id, len(qs)))
    print(sep)
    for i, q in enumerate(qs[:3], 1):
        opts = json.loads(q.options_json)
        print()
        print("  Q{}. {}".format(i, q.question[:150]))
        for k in ['a','b','c','d']:
            if k in opts:
                print("      {}. {}".format(k.upper(), opts[k][:90]))
        print("      Correct: {}".format(q.correct_option.upper()))
        rat = (q.rationale or "")[:120]
        print("      Rationale: {}...".format(rat))
        mh = (q.mains_hint or "")[:100]
        print("      Mains: {}".format(mh))
        print("      Subject: {} | Difficulty: {}".format(q.subject, q.difficulty))

db.close()
