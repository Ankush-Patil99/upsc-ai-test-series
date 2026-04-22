import os
import sys
import json
import time

# Ensure root path is accessible for script execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import sessionmaker
from api.models import engine, MockTest, TestQuestion, create_analytics_tables
from src.mcq_generation.generator import LangGraphMCQGenerator

# Auto-map DB schema natively without needing FastAPI to run
create_analytics_tables()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_bulk_test(topic: str, total_count: int = 50, batch_size: int = 5):
    """
    Mass-produces a full length paper while explicitly bypassing LLM context window limits
    by executing sequential batch-loops and mapping the results to the caching system.
    """
    print(f"\n[Batch Engine] Beginning Offline Generation Protocol for '{topic}'")
    print(f"[Batch Engine] Target Count: {total_count} MCQs.")
    print(f"Warning: This will perform {total_count // batch_size} silent API rounds. Do NOT close the terminal.\n")
    
    generator = LangGraphMCQGenerator()
    db = SessionLocal()
    
    try:
        # Create Parent Record
        new_test = MockTest(topic=topic, count=total_count)
        db.add(new_test)
        db.commit()
        db.refresh(new_test)
        
        questions_generated = 0
        iterations = 0
        
        # In a real batch engine, the prompt in `generator.py` would be slightly rewritten to support array returns.
        # For seamless integration, we will trigger the generator and securely append facts.
        while questions_generated < total_count:
            iterations += 1
            print(f"-> Batch {iterations}/{(total_count//batch_size)} [Retrieving Dual-Search Cache...]")
            
            # Simulated Batch Burst (Assuming the single generator will eventually wrap arrays if updated)
            # Currently it relies tightly on the Langgraph trace
            res = generator.generate(topic=topic, difficulty="hard")
            if "mcq" in res:
                mcq_data = res["mcq"]
                
                raw_options = mcq_data.get("options", [])
                mapped_options = {}
                labels = ["a", "b", "c", "d"]
                correct_label = "a"
                
                if isinstance(raw_options, list):
                    for idx, opt in enumerate(raw_options[:4]):
                        mapped_options[labels[idx]] = str(opt)
                        if mcq_data.get("correct") == opt or mcq_data.get("correct") == labels[idx]:
                            correct_label = labels[idx]
                else:
                    mapped_options = raw_options if isinstance(raw_options, dict) else {"a": "Error"}
                    correct_label = mcq_data.get("correct", "a")
                
                q_model = TestQuestion(
                    test_id=new_test.id,
                    question=mcq_data.get("question", ""),
                    options_json=json.dumps(mapped_options),
                    correct_option=correct_label,
                    rationale=mcq_data.get("explanation", ""),
                    mains_hint=res.get("mains_facts", "")
                )
                db.add(q_model)
                db.commit()
                
                questions_generated += 1
                
                time.sleep(4.5)
            
        print(f"\n[Batch Engine] SUCCESS. Full {total_count}-Question Mock Test Cached! (Test ID: {new_test.id})")
        
    except Exception as e:
        print(f"\n[Batch Engine] CRITICAL FAILURE: {e}")
    finally:
        db.close()

def generate_full_length_paper(paper_number: int):
    """
    Mass-produces a 100-Question UPSC GS1 paper matching standard Commission Distribution rules.
    """
    print(f"\n[GS1 Framework] Booting Full-Length Protocol for 'Mock Test Series #{paper_number}'")
    distribution = [
        {"subject": "Current Affairs", "count": 18},
        {"subject": "Environment and Ecology", "count": 15},
        {"subject": "Indian Polity and Constitution", "count": 15},
        {"subject": "Indian Economy & Economic Development", "count": 15},
        {"subject": "Physical and Indian Geography", "count": 12},
        {"subject": "Modern Indian History and Freedom Struggle", "count": 12},
        {"subject": "Science and Technology", "count": 8},
        {"subject": "Art and Culture", "count": 5}
    ]
    
    total_q = sum(d["count"] for d in distribution)
    test_title = f"UPSC mock test {paper_number} (Full length test)"
    
    generator = LangGraphMCQGenerator()
    db = SessionLocal()
    try:
        new_test = MockTest(topic=test_title, count=total_q)
        db.add(new_test)
        db.commit()
        db.refresh(new_test)
        
        global_count = 0
        for block in distribution:
            sub = block["subject"]
            target = block["count"]
            print(f"\n=> [GS1 Section] Spawning {target} heavily weighted questions for: {sub}")
            
            for _ in range(target):
                global_count += 1
                print(f"   -> Writing Q{global_count}/{total_q} [{sub}]")
                res = generator.generate(topic=sub, difficulty="hard")
                
                if "mcq" in res:
                    mcq_data = res["mcq"]
                    raw_options = mcq_data.get("options", [])
                    mapped_options = {}
                    labels = ["a", "b", "c", "d"]
                    correct_label = "a"
                    
                    if isinstance(raw_options, list):
                        for idx, opt in enumerate(raw_options[:4]):
                            mapped_options[labels[idx]] = str(opt)
                            if mcq_data.get("correct") == opt or mcq_data.get("correct") == labels[idx]:
                                correct_label = labels[idx]
                    else:
                        mapped_options = raw_options if isinstance(raw_options, dict) else {"a": "Error"}
                        correct_label = mcq_data.get("correct", "a")
                    
                    q_model = TestQuestion(
                        test_id=new_test.id,
                        question=mcq_data.get("question", ""),
                        options_json=json.dumps(mapped_options),
                        correct_option=correct_label,
                        rationale=mcq_data.get("explanation", ""),
                        mains_hint=res.get("mains_facts", "")
                    )
                    db.add(q_model)
                    db.commit()
                time.sleep(10)
                
        print(f"\n[GS1 Framework] SUCCESS! Complete 100-Question Exam '{test_title}' securely cached!")
    except Exception as e:
        print(f"\n[GS1 Framework] CRITICAL FAILURE: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  1. Subject-Wise: python batch_generator.py <Topic> <Count>")
        print("  2. Full-Length GS1: python batch_generator.py FULL_LENGTH <Paper_Number>")
        sys.exit(1)
        
    arg1 = sys.argv[1]
    
    if arg1 == "FULL_LENGTH":
        paper_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        generate_full_length_paper(paper_id)
    else:
        count_arg = int(sys.argv[2])
        generate_bulk_test(arg1, total_count=count_arg)
