import json

with open(r'd:\upsc test series\paper1_parsed.json', encoding='utf-8') as f:
    data = json.load(f)

bad = [(q['questionNumber'], q['question'][:80]) for q in data if len(q['question']) < 20 or len(q['options'][0]) < 3]
print(f'Questions with issues: {len(bad)}')
for qno, qt in bad[:20]:
    print(f'  Q{qno}: [{qt}]')

good = [q for q in data if len(q['question']) > 50]
print(f'\nGood questions: {len(good)}')
q5 = good[5]
print(f'Q{q5["questionNumber"]}: {q5["question"][:100]}')
print(f'Options: {q5["options"]}')
print(f'Correct: {q5["correctAnswer"]}')
