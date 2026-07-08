import json, re

# ─────────────────────────────────────────────────────────────────────────────
# Load columns and answer data
# ─────────────────────────────────────────────────────────────────────────────
with open(r"d:\upsc test series\paper1_cols_left.txt", encoding="utf-8") as f:
    left_raw = f.read()
with open(r"d:\upsc test series\paper1_cols_right.txt", encoding="utf-8") as f:
    right_raw = f.read()
with open(r"d:\upsc test series\paper1_parsed.json", encoding="utf-8") as f:
    existing = json.load(f)   # has good answers/explanations already

# Build lookup by qno for answers & explanations
ans_map  = {q["questionNumber"]: q["correctAnswer"]  for q in existing}
exp_map  = {q["questionNumber"]: q["explanation"]    for q in existing}
subj_map = {q["questionNumber"]: q["subject"]        for q in existing}

# ─────────────────────────────────────────────────────────────────────────────
# Strip instruction header (everything before "1. Consider")
# ─────────────────────────────────────────────────────────────────────────────
def strip_header(text):
    m = re.search(r'(?m)^\s*1\.\s+', text)
    return text[m.start():] if m else text

left_text  = strip_header(left_raw)
right_text = strip_header(right_raw)

# ─────────────────────────────────────────────────────────────────────────────
# Parse question blocks from each column
# Strategy: split on lines that START with a bare question number "N."
# ─────────────────────────────────────────────────────────────────────────────
def parse_columns(text, max_qno=100):
    """Split text into {qno: block_text} using line-start numbered markers."""
    blocks = {}
    # Match lines like "1." "12." "100." at the very start of a line
    pattern = re.compile(r'(?m)^(\d{1,3})\.\s+')
    matches = list(pattern.finditer(text))
    for idx, m in enumerate(matches):
        qno = int(m.group(1))
        if not (1 <= qno <= max_qno):
            continue
        start = m.start()
        end   = matches[idx+1].start() if idx+1 < len(matches) else len(text)
        block = text[start:end]
        # Remove the leading "N. " prefix
        block = re.sub(r'^\d{1,3}\.\s+', '', block, count=1).strip()
        if qno not in blocks:
            blocks[qno] = block
    return blocks

left_blocks  = parse_columns(left_text)
right_blocks = parse_columns(right_text)

# Merge: right fills gaps, left wins where both present
merged = {}
merged.update(right_blocks)
merged.update(left_blocks)
print(f"Blocks: left={len(left_blocks)} right={len(right_blocks)} merged={len(merged)}")

# ─────────────────────────────────────────────────────────────────────────────
# Parse options from each block
# ─────────────────────────────────────────────────────────────────────────────
def extract_options(block):
    """Return (question_text, [optA, optB, optC, optD])."""
    # Options are marked (a), (b), (c), (d) — case-insensitive
    opt_pat = re.compile(r'\(([abcdABCD])\)\s+')
    parts   = opt_pat.split(block)
    
    q_txt = re.sub(r'\s{2,}', ' ', parts[0]).strip()
    opts  = {'a': '', 'b': '', 'c': '', 'd': ''}
    i = 1
    while i + 1 < len(parts):
        lbl = parts[i].lower()
        if lbl in opts:
            val = parts[i+1]
            # Cut off at next question number leak
            val = re.split(r'\n\s*\d{1,3}\.\s+[A-Z]', val)[0]
            opts[lbl] = re.sub(r'\s{2,}', ' ', val).strip()
        i += 2
    return q_txt, [opts['a'], opts['b'], opts['c'], opts['d']]

# ─────────────────────────────────────────────────────────────────────────────
# Build final JSON
# ─────────────────────────────────────────────────────────────────────────────
final = []
bad   = []
for qno in range(1, 101):
    block = merged.get(qno, "")
    q_txt, opts = extract_options(block)
    
    correct_letter = ans_map.get(qno, "A")
    correct_idx    = ord(correct_letter) - ord('A')
    correct_text   = opts[correct_idx] if correct_idx < 4 else ""
    explanation    = exp_map.get(qno, "")
    subject        = subj_map.get(qno, "General Studies")
    
    if len(q_txt) < 15 or len(opts[0]) < 5:
        bad.append(qno)
    
    final.append({
        "id":                f"visionias_pt13843_q{qno}",
        "question":          q_txt,
        "options":           opts,
        "correctAnswer":     correct_letter,
        "correctAnswerText": correct_text,
        "explanation":       explanation,
        "subject":           subject,
        "questionNumber":    qno
    })

print(f"Questions with parsing issues: {bad}")

with open(r"d:\upsc test series\paper1_parsed.json", "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)
print(f"Saved {len(final)} questions")

# ─────────────────────────────────────────────────────────────────────────────
# Show samples
# ─────────────────────────────────────────────────────────────────────────────
for qno in [1, 11, 21, 51, 100]:
    q = final[qno-1]
    print(f"\nQ{qno} [{q['subject']}]:")
    print(f"  Q: {q['question'][:120]}")
    print(f"  A: {q['options'][0][:60]} | B: {q['options'][1][:60]}")
    print(f"  Correct: {q['correctAnswer']} — {q['correctAnswerText'][:60]}")
