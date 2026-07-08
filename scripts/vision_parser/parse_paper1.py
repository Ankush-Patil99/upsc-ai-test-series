import re
import json

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Parse answer key from the solutions PDF
# ─────────────────────────────────────────────────────────────────────────────
with open(r"d:\upsc test series\paper1_answers_raw.txt", encoding="utf-8") as f:
    ans_text = f.read()

# Find all "Q N. X" patterns  e.g. "Q 1. C" or "Q1. C"
answer_pattern = re.compile(r'Q\s*(\d+)\.\s*([A-D])')
answers = {}
for m in answer_pattern.finditer(ans_text):
    qno = int(m.group(1))
    ans = m.group(2)
    if qno not in answers:          # take first occurrence only
        answers[qno] = ans
print(f"✅ Found {len(answers)} answer keys")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Parse explanations from solutions PDF
# ─────────────────────────────────────────────────────────────────────────────
# Split explanations block by question boundaries
# Each block starts with "Q N. X  <explanation text>"
exp_pattern = re.compile(r'Q\s*(\d+)\.\s*[A-D]\s+(.*?)(?=Q\s*\d+\.\s*[A-D]\s+|\Z)', re.DOTALL)
explanations = {}
for m in exp_pattern.finditer(ans_text):
    qno = int(m.group(1))
    raw = m.group(2).strip()
    # Clean up watermark single chars like "S\nA\nI\nN\nO"  and page numbers
    clean = re.sub(r'\n\s*[SAINO]\s*\n', '\n', raw)
    clean = re.sub(r'\d+\s+www\.visionias\.in\s+©Vision IAS', '', clean)
    clean = re.sub(r'www\.visionias\.in\s+©Vision IAS', '', clean)
    clean = re.sub(r'\s{2,}', ' ', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    clean = clean.strip()
    if qno not in explanations:
        explanations[qno] = clean
print(f"✅ Found {len(explanations)} explanations")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Parse questions from the questions PDF (2-column layout)
# We rely on numbered markers "1.", "2." ... "100." to split
# ─────────────────────────────────────────────────────────────────────────────
with open(r"d:\upsc test series\paper1_questions_raw.txt", encoding="utf-8") as f:
    q_text = f.read()

# Remove instruction header (everything before question 1)
# Find first "1." that starts a line (or near start of text after removing header)
header_end = re.search(r'\n\s*1\.\s+Consider', q_text)
if header_end:
    q_text = q_text[header_end.start():]

# ─────────────────────────────────────────────────────────────────────────────
# Because the PDF is 2-column, lines from both columns are interleaved.
# Strategy: extract ALL numbered question blocks one-at-a-time using
# a lookahead for the NEXT question number.
# ─────────────────────────────────────────────────────────────────────────────
question_blocks = {}
for i in range(1, 101):
    next_i = i + 1
    if next_i <= 100:
        pattern = re.compile(
            rf'(?<!\d){i}\.\s+(.*?)(?=(?<!\d){next_i}\.\s+[A-Z])',
            re.DOTALL
        )
    else:
        pattern = re.compile(rf'(?<!\d){i}\.\s+(.*?)$', re.DOTALL)

    m = pattern.search(q_text)
    if m:
        question_blocks[i] = m.group(1).strip()

print(f"✅ Extracted {len(question_blocks)} question blocks")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Parse each block into question text + 4 options
# ─────────────────────────────────────────────────────────────────────────────
def parse_block(block):
    """Extract question text and options (a)(b)(c)(d) from a raw block."""
    # Regex for options: (a) ... (b) ... (c) ... (d) ...
    opt_re = re.compile(r'\(([abcd])\)\s+', re.IGNORECASE)
    parts = opt_re.split(block)
    # parts[0] = question text, then alternating label / text
    question_text = parts[0].strip()
    options = {}
    i = 1
    while i + 1 < len(parts):
        label = parts[i].lower()
        text = parts[i + 1].strip()
        # Clean stray text that belongs to the next question
        options[label] = re.sub(r'\s{2,}', ' ', text).strip()
        i += 2
    return question_text, options

def subject_tag(qno):
    """
    Heuristic subject tagging based on question ranges.
    Adjust ranges after reviewing the paper if needed.
    """
    if 1 <= qno <= 10:
        return "Economy"
    elif 11 <= qno <= 20:
        return "History & Art"
    elif 21 <= qno <= 26:
        return "International Relations"
    elif 27 <= qno <= 34:
        return "Geography"
    elif 35 <= qno <= 40:
        return "Current Affairs"
    elif 41 <= qno <= 50:
        return "Polity"
    elif 51 <= qno <= 57:
        return "Environment & Ecology"
    elif 58 <= qno <= 65:
        return "Science & Technology"
    elif 66 <= qno <= 70:
        return "Economy"
    elif 71 <= qno <= 76:
        return "History & Art"
    elif 77 <= qno <= 85:
        return "Geography"
    elif 86 <= qno <= 90:
        return "Polity"
    elif 91 <= qno <= 96:
        return "Current Affairs"
    elif 97 <= qno <= 100:
        return "Science & Technology"
    return "General Studies"

OPTION_LABELS = {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}

questions_json = []
for qno in range(1, 101):
    block = question_blocks.get(qno, "")
    q_text_clean, options = parse_block(block)

    # Clean question text
    q_text_clean = re.sub(r'\s{2,}', ' ', q_text_clean).strip()

    # Build options array in order A B C D
    opts_ordered = []
    for lbl in ['a', 'b', 'c', 'd']:
        opts_ordered.append(options.get(lbl, "").strip())

    # Correct answer letter from answers dict
    correct_letter = answers.get(qno, "A")  # fallback A
    correct_index = ord(correct_letter) - ord('A')  # 0-3
    correct_text = opts_ordered[correct_index] if correct_index < len(opts_ordered) else ""

    explanation = explanations.get(qno, "")

    questions_json.append({
        "id": f"visionias_pt13843_q{qno}",
        "question": q_text_clean,
        "options": opts_ordered,
        "correctAnswer": correct_letter,
        "correctAnswerText": correct_text,
        "explanation": explanation,
        "subject": subject_tag(qno),
        "questionNumber": qno
    })

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Save JSON
# ─────────────────────────────────────────────────────────────────────────────
out_path = r"d:\upsc test series\paper1_parsed.json"
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(questions_json, f, ensure_ascii=False, indent=2)

print(f"\n✅ Done! Saved {len(questions_json)} questions to paper1_parsed.json")
print("\nSample Q1:")
q = questions_json[0]
print(f"  Q: {q['question'][:100]}...")
print(f"  Options: {q['options']}")
print(f"  Correct: {q['correctAnswer']} — {q['correctAnswerText'][:60]}")
print(f"  Subject: {q['subject']}")
print(f"  Explanation snippet: {q['explanation'][:120]}...")
