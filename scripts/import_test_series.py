import json
import os
import sys

# Add project root to sys.path so we can import api.models
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from api.models import SessionLocal, MockTest, TestQuestion

def import_test_series(json_path: str):
    print(f"Loading JSON file from: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        topic_name = "Full Length GS Test 1"
        count = data.get("total_questions", 100)
        
        # Create the MockTest entry
        mock_test = MockTest(
            topic=topic_name,
            count=count,
            paper_type="GS-1"  # Defaulting to GS-1 for full length
        )
        db.add(mock_test)
        db.commit()
        db.refresh(mock_test)
        
        print(f"Created MockTest ID: {mock_test.id} for topic: {topic_name}")
        
        questions_to_add = []
        for q_data in data.get("questions", []):
            # Convert options to lowercase keys (a, b, c, d)
            original_options = q_data.get("options", {})
            options_json_dict = {k.lower(): v for k, v in original_options.items()}
            
            correct_option = q_data.get("correct_option", "A").lower()
            
            # Use full_explanation if available, otherwise explanation
            rationale = q_data.get("full_explanation") or q_data.get("explanation", "")
            mains_hint = q_data.get("mains_fact", "")
            
            subject = q_data.get("analytics_subject", "General")
            difficulty = q_data.get("difficulty", "medium").lower()
            
            test_question = TestQuestion(
                test_id=mock_test.id,
                question=q_data.get("question", ""),
                options_json=json.dumps(options_json_dict),
                correct_option=correct_option,
                rationale=rationale,
                mains_hint=mains_hint,
                subject=subject,
                difficulty=difficulty
            )
            questions_to_add.append(test_question)
            
        db.bulk_save_objects(questions_to_add)
        db.commit()
        print(f"Successfully imported {len(questions_to_add)} questions into the database!")
        
    except Exception as e:
        print(f"Error during import: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    json_file_path = r"C:\Users\ankus\OneDrive\Desktop\Full lenth test series 1.json"
    import_test_series(json_file_path)
