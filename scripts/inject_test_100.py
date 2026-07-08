import sys, os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sqlalchemy.orm import sessionmaker
from api.models import SessionLocal, UniversalQuestionBank, MockTest, TestQuestion
import json

def clean_question(text):
    # Remove things like "Option (a) is correct: " or "Correct Answer: Option (A)"
    # Sometimes it's at the start.
    text = re.sub(r'^(?:Option\s*\([a-d]\)\s*is\s*correct[^\:]*\:\s*)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:Correct\s*Answer[^\:]*\:\s*Option\s*\([a-d]\)[^\.]*\.\s*)', '', text, flags=re.IGNORECASE)
    # Remove any leading "Both statements are correct:" etc
    text = re.sub(r'^(?:Both\s*statements\s*are\s*correct\:\s*)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:Statement\s*1\s*is\s*(?:in)?correct\:\s*)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:Option\s*[a-d]\s*is\s*the\s*correct\s*answer\.\s*)', '', text, flags=re.IGNORECASE)
    return text.strip()

def inject_test_100():
    db = SessionLocal()
    
    db.query(TestQuestion).filter(TestQuestion.test_id == 100).delete()
    db.query(MockTest).filter(MockTest.id == 100).delete()
    db.commit()

    questions = db.query(UniversalQuestionBank).limit(50).all()
    if not questions: return
    
    test = MockTest(
        id=100,
        topic="History and Art & Culture - DB Mix",
        count=len(questions),
        paper_type="Subject-Wise"
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    
    for q in questions:
        options_dict = {}
        try:
            options_list = json.loads(q.options_json)
            for i, opt in enumerate(options_list):
                if i == 0: options_dict["a"] = opt
                elif i == 1: options_dict["b"] = opt
                elif i == 2: options_dict["c"] = opt
                elif i == 3: options_dict["d"] = opt
        except:
            options_dict = {"a": "Error parsing options"}
            
        correct_letter = "a"
        if q.correct_option:
            try:
                for k, v in options_dict.items():
                    if v.strip() == q.correct_option.strip():
                        correct_letter = k
                        break
            except:
                pass

        cleaned_q = clean_question(q.question)
        
        # We append the original question string if it was an explanation, into rationale, just to be safe
        rationale = q.rationale
        if cleaned_q != q.question:
            rationale = q.question + "\n\n" + q.rationale

        tq = TestQuestion(
            test_id=test.id,
            question=cleaned_q,
            options_json=json.dumps(options_dict),
            correct_option=correct_letter,
            rationale=rationale,
            mains_hint=q.mains_hint,
            subject=q.subject,
            difficulty=q.difficulty
        )
        db.add(tq)
    
    db.commit()
    print(f"Successfully created MockTest ID: {test.id} with {len(questions)} sanitized questions.")

if __name__ == '__main__':
    inject_test_100()
