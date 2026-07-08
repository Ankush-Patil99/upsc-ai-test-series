import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.models import SessionLocal, UniversalQuestionBank

def view_database():
    print("============================================================")
    print(" 📚 UPSC QUESTION BANK - RECENTLY INJECTED QUESTIONS")
    print("============================================================\n")

    db = SessionLocal()
    
    # Get total count
    total = db.query(UniversalQuestionBank).count()
    print(f"📊 Total Questions in Database: {total}\n")

    if total == 0:
        print("The database is currently empty.")
        db.close()
        return

    # Fetch the 3 most recently added questions
    recent_qs = db.query(UniversalQuestionBank).order_by(UniversalQuestionBank.id.desc()).limit(3).all()

    for idx, q in enumerate(recent_qs, 1):
        print(f"--- Question {idx} ---")
        print(f"🏷️  Subject : {q.subject}")
        print(f"📌 Topic   : {q.topic}")
        print(f"❓ Q       : {q.question}")
        
        try:
            options = json.loads(q.options_json)
            print(f"📋 Options :")
            for i, opt in enumerate(options):
                print(f"   {chr(65+i)}. {opt}")
        except:
            print(f"📋 Options : {q.options_json}")
            
        print(f"✅ Correct : {q.correct_option}")
        print(f"🧠 Rationale : {q.rationale[:150]}...\n")

    db.close()

if __name__ == "__main__":
    view_database()
