import sys, os
from pathlib import Path

# Add root folder to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import sessionmaker
from api.models import SessionLocal, UniversalQuestionBank, MockTest, TestQuestion
import json

def inject_test():
    db = SessionLocal()
    
    # Try to get up to 50 questions
    questions = db.query(UniversalQuestionBank).limit(50).all()
    
    if not questions:
        print("No questions found in UniversalQuestionBank.")
        return
        
    print(f"Found {len(questions)} questions.")
    
    test = MockTest(
        topic="History and Art & Culture (Subject Wise Test)",
        count=len(questions),
        paper_type="Subject-Wise"
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    
    for q in questions:
        # Convert list of options to dict format expected by the frontend
        # UniversalQuestionBank: ["Option A", "Option B", ...]
        # TestQuestion: {"a": "Option A", "b": "Option B", ...}
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
                
        # Fix format if "Option (a) is correct: " is in question
        cleaned_question = q.question
        if "Option" in cleaned_question and "is correct:" in cleaned_question:
            # We already have rationale and correct option, let's try to just keep the question part
            # It's actually safer to just keep it as is, but we could try to clean it
            pass

        tq = TestQuestion(
            test_id=test.id,
            question=cleaned_question,
            options_json=json.dumps(options_dict),
            correct_option=correct_letter,
            rationale=q.rationale,
            mains_hint=q.mains_hint,
            subject=q.subject,
            difficulty=q.difficulty
        )
        db.add(tq)
    
    db.commit()
    print(f"Successfully created MockTest ID: {test.id} with {len(questions)} questions.")

if __name__ == '__main__':
    inject_test()
