import pdfplumber
import json
import re

PDF_Q  = r"d:\upsc test series\data\pyqs\Other test series\1.pdf"
PDF_A  = r"d:\upsc test series\data\pyqs\Other test series\1.1.pdf"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Column-aware extraction for the 2-column question paper
# ─────────────────────────────────────────────────────────────────────────────
def extract_columns(pdf_path):
    """Extract text from a 2-column PDF, returning left_text + right_text per page."""
    full_left = ""
    full_right = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            w = page.width
            midpoint = w * 0.52           # split at ~52% width
            
            left_page = page.crop((0, 0, midpoint, page.height))
            right_page = page.crop((midpoint, 0, w, page.height))
            
            lt = left_page.extract_text() or ""
            rt = right_page.extract_text() or ""
            full_left  += lt + "\n"
            full_right += rt + "\n"
    return full_left, full_right

print("Extracting columns from questions PDF...")
left_text, right_text = extract_columns(PDF_Q)

# Combine: left column first (Q1,2,...~50), then right (~50..100)
combined = left_text + "\n" + right_text

# Save for inspection
with open(r"d:\upsc test series\paper1_cols_left.txt", "w", encoding="utf-8") as f:
    f.write(left_text)
with open(r"d:\upsc test series\paper1_cols_right.txt", "w", encoding="utf-8") as f:
    f.write(right_text)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Parse answer keys from the solutions PDF (single column)
# ─────────────────────────────────────────────────────────────────────────────
ans_text = ""
exp_text = ""
with pdfplumber.open(PDF_A) as pdf:
    for page in pdf.pages:
        t = page.extract_text() or ""
        ans_text += t + "\n"

# Answer key: Q N. X
answers = {}
for m in re.finditer(r'Q\s*(\d+)\.\s*([A-D])', ans_text):
    qno = int(m.group(1))
    if qno not in answers:
        answers[qno] = m.group(2)
print(f"Found {len(answers)} answer keys")

# Explanations
exp_blocks = {}
exp_pat = re.compile(r'Q\s*(\d+)\.\s*[A-D]\s+(.*?)(?=Q\s*\d+\.\s*[A-D]\s+|\Z)', re.DOTALL)
for m in exp_pat.finditer(ans_text):
    qno = int(m.group(1))
    raw = m.group(2).strip()
    # Remove watermark artifacts
    raw = re.sub(r'\b[SAINOV]\b', '', raw)
    raw = re.sub(r'\d+\s*www\.visionias\.in\s*[©]?\s*Vision IAS', '', raw)
    raw = re.sub(r'\s{3,}', ' ', raw)
    raw = raw.strip()
    if qno not in exp_blocks:
        exp_blocks[qno] = raw
print(f"Found {len(exp_blocks)} explanations")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Parse questions from column-aware text
# ─────────────────────────────────────────────────────────────────────────────
def parse_questions_from_text(text):
    """Parse numbered questions from clean single-column text."""
    blocks = {}
    # Split on question numbers at start of content
    parts = re.split(r'\n(?=\d{1,3}\.\s+[A-Z])', text)
    for part in parts:
        part = part.strip()
        m = re.match(r'^(\d+)\.\s+(.*)', part, re.DOTALL)
        if m:
            qno = int(m.group(1))
            if 1 <= qno <= 100 and qno not in blocks:
                blocks[qno] = m.group(2).strip()
    return blocks

q_blocks_left  = parse_questions_from_text(left_text)
q_blocks_right = parse_questions_from_text(right_text)

# Merge (right-column questions fill gaps left by left column)
q_blocks = {}
q_blocks.update(q_blocks_right)
q_blocks.update(q_blocks_left)      # left wins if both have same key
print(f"Parsed question blocks: left={len(q_blocks_left)}, right={len(q_blocks_right)}, total={len(q_blocks)}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Parse each block into question text + options
# ─────────────────────────────────────────────────────────────────────────────
def parse_block(block):
    opt_re = re.compile(r'\(([abcd])\)\s+', re.IGNORECASE)
    parts = opt_re.split(block)
    q_txt = re.sub(r'\s{2,}', ' ', parts[0]).strip()
    opts = {}
    i = 1
    while i + 1 < len(parts):
        lbl = parts[i].lower()
        val = re.sub(r'\s{2,}', ' ', parts[i+1]).strip()
        # Stop at next question number leak
        val = re.split(r'\n\d{1,3}\.\s+[A-Z]', val)[0].strip()
        opts[lbl] = val
        i += 2
    return q_txt, opts

def subject_tag(qno):
    if   1  <= qno <= 10:  return "Economy"
    elif 11 <= qno <= 20:  return "History & Art"
    elif 21 <= qno <= 26:  return "International Relations"
    elif 27 <= qno <= 34:  return "Geography"
    elif 35 <= qno <= 40:  return "Current Affairs"
    elif 41 <= qno <= 50:  return "Polity"
    elif 51 <= qno <= 57:  return "Environment & Ecology"
    elif 58 <= qno <= 65:  return "Science & Technology"
    elif 66 <= qno <= 70:  return "Economy"
    elif 71 <= qno <= 76:  return "History & Art"
    elif 77 <= qno <= 85:  return "Geography"
    elif 86 <= qno <= 90:  return "Polity"
    elif 91 <= qno <= 96:  return "Current Affairs"
    else:                   return "Science & Technology"

final_questions = []
issues = []
for qno in range(1, 101):
    block = q_blocks.get(qno, "")
    q_txt, opts = parse_block(block)
    
    opts_list = [opts.get(l, "").strip() for l in ['a','b','c','d']]
    correct_letter = answers.get(qno, "A")
    correct_idx = ord(correct_letter) - ord('A')
    correct_text = opts_list[correct_idx] if correct_idx < len(opts_list) else ""
    explanation = exp_blocks.get(qno, "")

    if len(q_txt) < 15 or len(opts_list[0]) < 5:
        issues.append(qno)

    final_questions.append({
        "id": f"visionias_pt13843_q{qno}",
        "question": q_txt,
        "options": opts_list,
        "correctAnswer": correct_letter,
        "correctAnswerText": correct_text,
        "explanation": explanation,
        "subject": subject_tag(qno),
        "questionNumber": qno
    })

print(f"\nQuestions with possible issues: {issues}")

# Save final JSON
out = r"d:\upsc test series\paper1_parsed.json"
with open(out, 'w', encoding='utf-8') as f:
    json.dump(final_questions, f, ensure_ascii=False, indent=2)
print(f"Saved {len(final_questions)} questions to paper1_parsed.json")

# Show sample
q = final_questions[0]
print(f"\nSample Q1:\n  Q: {q['question'][:120]}")
print(f"  Opts: {q['options']}")
print(f"  Ans: {q['correctAnswer']} -> {q['correctAnswerText'][:60]}")
print(f"  Subj: {q['subject']}")
