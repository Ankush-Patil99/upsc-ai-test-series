import re
import json
from api.models import SessionLocal, MockTest, TestQuestion, create_analytics_tables

def ingest():
    create_analytics_tables()
    q_text = open('questions.txt', 'r', encoding='utf-8', errors='ignore').read()
    a_text = open('answers.txt', 'r', encoding='utf-8', errors='ignore').read()

    # Clean headers and footers from pages
    q_text = re.sub(r'\[TEST SERIES.*?\]\s*\[KSG:.*?\][^\n]*?(\d+\.)', r'\n\1', q_text)
    q_text = re.sub(r'\[TEST SERIES.*?\]\s*\[KSG:.*?\][^\n]*?\n', '\n', q_text)
    q_text = re.sub(r'KSG: MEMBER’S COPY\s*', '\n', q_text)
    
    a_text = re.sub(r'\[TEST SERIES.*?\]\s*\[KSG:.*?\][^\n]*?(\d+\.)', r'\n\1', a_text)
    a_text = re.sub(r'\[TEST SERIES.*?\]\s*\[KSG:.*?\][^\n]*?\n', '\n', a_text)
    a_text = re.sub(r'KSG: MEMBER’S COPY\s*', '\n', a_text)
    a_text = re.sub(r'TEST – \d+ \(EXPLANATION & SOURCE\).*?\n.*?\n.*?\n.*?\n.*?\n.*?\n', '', a_text, flags=re.IGNORECASE|re.DOTALL)

    q_dict = {}
    for i in range(1, 101):
        start_pattern = rf'(?:^|\n)\s*{i}\.\s+'
        match_start = re.search(start_pattern, q_text)
        
        if not match_start:
            q_dict[i] = {
                'question': f"Question {i} (Parse Error)",
                'options': {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}
            }
            continue
            
        start_idx = match_start.end()
        
        if i < 100:
            end_pattern = rf'(?:^|\n)\s*{i+1}\.\s+'
            match_end = re.search(end_pattern, q_text[start_idx:])
            if match_end:
                end_idx = start_idx + match_end.start()
            else:
                end_idx = len(q_text)
        else:
            end_idx = len(q_text)
            
        q_chunk = q_text[start_idx:end_idx].strip()
        
        opt_a = re.search(r'\([aA]\)\s*(.*?)(?=\([bB]\))', q_chunk, re.DOTALL)
        opt_b = re.search(r'\([bB]\)\s*(.*?)(?=\([cC]\))', q_chunk, re.DOTALL)
        opt_c = re.search(r'\([cC]\)\s*(.*?)(?=\([dD]\))', q_chunk, re.DOTALL)
        opt_d = re.search(r'\([dD]\)\s*(.*)', q_chunk, re.DOTALL)
        
        q_only = re.sub(r'\n?\([aA]\).*', '', q_chunk, flags=re.DOTALL).strip()
        
        q_dict[i] = {
            'question': q_only,
            'options': {
                'a': opt_a.group(1).strip().replace('\n', ' ') if opt_a else 'Unknown',
                'b': opt_b.group(1).strip().replace('\n', ' ') if opt_b else 'Unknown',
                'c': opt_c.group(1).strip().replace('\n', ' ') if opt_c else 'Unknown',
                'd': opt_d.group(1).strip().replace('\n', ' ') if opt_d else 'Unknown'
            }
        }

    a_dict = {}
    for i in range(1, 101):
        start_pattern = rf'(?:^|\n)\s*{i}\.\s*.*?\(([a-d])\)'
        match_start = re.search(start_pattern, a_text, flags=re.IGNORECASE)
        if not match_start:
            a_dict[i] = {
                'correct': 'a',
                'explanation': "Explanation parsing failed for this question."
            }
            continue
            
        correct_ans = match_start.group(1).lower()
        start_idx = match_start.end()
        
        if i < 100:
            end_pattern = rf'(?:^|\n)\s*{i+1}\.\s*.*?\([a-d]\)'
            match_end = re.search(end_pattern, a_text[start_idx:], flags=re.IGNORECASE)
            if match_end:
                end_idx = start_idx + match_end.start()
            else:
                end_idx = len(a_text)
        else:
            end_idx = len(a_text)
            
        a_chunk = a_text[start_idx:end_idx].strip()
        a_chunk = re.sub(r'^Explanation:?\s*', '', a_chunk, flags=re.IGNORECASE).strip()
        
        a_dict[i] = {
            'correct': correct_ans,
            'explanation': a_chunk
        }

    db = SessionLocal()
    existing = db.query(MockTest).filter(MockTest.topic == "Prototype Paper").first()
    if existing:
        db.query(TestQuestion).filter(TestQuestion.test_id == existing.id).delete()
        db.delete(existing)
        db.commit()

    test = MockTest(topic="Prototype Paper", count=100)
    db.add(test)
    db.commit()
    
    valid_count = 0
    for i in range(1, 101):
        q = TestQuestion(
            test_id=test.id,
            question=q_dict[i]['question'],
            options_json=json.dumps(q_dict[i]['options']),
            correct_option=a_dict[i]['correct'],
            rationale=a_dict[i]['explanation'],
            subject="General Studies"
        )
        db.add(q)
        valid_count += 1
            
    db.commit()
    print(f"Successfully ingested Prototype Paper with {valid_count} questions into DB. MockTest ID = {test.id}")

if __name__ == "__main__":
    ingest()
