import re, json

# ─── Load column texts ────────────────────────────────────────────────────────
with open(r"d:\upsc test series\paper1_cols_left.txt", encoding="utf-8") as f:
    left_raw = f.read()
with open(r"d:\upsc test series\paper1_cols_right.txt", encoding="utf-8") as f:
    right_raw = f.read()

# ─── Load existing answer/explanation data ────────────────────────────────────
with open(r"d:\upsc test series\paper1_parsed.json", encoding="utf-8") as f:
    existing = json.load(f)
ans_map  = {q["questionNumber"]: q["correctAnswer"]  for q in existing}
exp_map  = {q["questionNumber"]: q["explanation"]    for q in existing}
subj_map = {q["questionNumber"]: q["subject"]        for q in existing}

# ─── Strip everything before actual Q1 (instructions header) ─────────────────
def strip_to_q1(text):
    m = re.search(r'(?m)^\s*1\.\s+', text)
    return text[m.start():] if m else text

# For right column, strip to Q3 since Q1/Q2 appear in left
def strip_to_q3(text):
    m = re.search(r'(?m)^\s*3\.\s+', text)
    return text[m.start():] if m else text

left_clean  = strip_to_q1(left_raw)
right_clean = strip_to_q3(right_raw)   # right col page1 starts at Q3

# ─── Parse blocks ─────────────────────────────────────────────────────────────
def parse_blocks(text):
    blocks = {}
    pat = re.compile(r'(?m)^(\d{1,3})\.\s+')
    matches = list(pat.finditer(text))
    for idx, m in enumerate(matches):
        qno = int(m.group(1))
        if not (1 <= qno <= 100):
            continue
        start = m.start()
        end   = matches[idx+1].start() if idx+1 < len(matches) else len(text)
        block = text[start:end]
        block = re.sub(r'^\d{1,3}\.\s+', '', block, count=1).strip()
        if qno not in blocks:
            blocks[qno] = block
    return blocks

left_blocks  = parse_blocks(left_clean)
right_blocks = parse_blocks(right_clean)

# Merge: left wins (it has Q1, Q2 etc); right fills Q3,Q4,Q5,Q8 etc from page1
merged = {}
merged.update(right_blocks)
merged.update(left_blocks)

# ─── Extract question text + 4 options from a block ──────────────────────────
def extract_options(block):
    opt_pat = re.compile(r'\(([abcdABCD])\)\s+')
    parts   = opt_pat.split(block)
    q_txt   = re.sub(r'\s{2,}', ' ', parts[0]).strip()
    opts    = {'a': '', 'b': '', 'c': '', 'd': ''}
    i = 1
    while i + 1 < len(parts):
        lbl = parts[i].lower()
        if lbl in opts:
            val = parts[i+1]
            val = re.split(r'\n\s*\d{1,3}\.\s+[A-Z]', val)[0]
            opts[lbl] = re.sub(r'\s{2,}', ' ', val).strip()
        i += 2
    return q_txt, [opts['a'], opts['b'], opts['c'], opts['d']]

# ─── Manual fixes for questions that cannot be auto-parsed ────────────────────
MANUAL = {
    1: {
        "question": "Consider the following situations related to Indian economy.\nI. An IT services export company sees its revenue rise in rupee terms.\nII. An Indian student studying abroad pays more in rupee terms for tuition.\nIII. An Indian airline with high external debt in dollars sees its interest burden decrease.\nIV. An oil refinery importing crude sees its input costs increase.\nHow many of the situations imply the depreciation of the Indian Rupee?",
        "options": ["Only one", "Only two", "Only three", "All four"]
    },
    2: {
        "question": "Consider the following statements about coconut production in India:\nI. India is the world's largest producer of coconuts.\nII. Nearly 100 million farmers in India depend on coconuts for their livelihood.\nIII. Currently, Kerala is the largest producer of coconuts in India.\nIV. Currently, coconut growers cannot benefit from the MSP support promoted by the Government.\nWhich of the statements given above are correct?",
        "options": ["II, III and IV only", "I and II only", "I only", "II and III only"]
    },
    3: {
        "question": "States receive funds from the Centre for various purposes and through different channels. In this context, arrange the following transfers from Centre to States in the decreasing order of their values.\nI. Finance Commission Grants\nII. Centrally Sponsored Schemes\nIII. States' share in Central taxes\nSelect the correct answer using the code given below.",
        "options": ["III-II-I", "II-I-III", "II-III-I", "I-II-III"]
    },
    4: {
        "question": "If for a particular year, a country's primary deficit is zero that means",
        "options": ["It has to make zero interest payments.", "Its revenue receipts are just enough to meet all its revenue expenditure.", "Its entire borrowing is to service its past debt.", "Its total income is due to direct taxes."]
    },
    5: {
        "question": "Consider the following statements regarding the situation of liquidity trap:\nStatement-I: Open Market Operations (OMO) to buy securities becomes highly effective in stimulating investment.\nStatement-II: The demand for money becomes perfectly elastic with respect to the interest rate.\nWhich one of the following is correct in respect of the above statements?",
        "options": ["Both Statement-I and Statement-II are correct and Statement-II is the correct explanation for Statement-I.", "Both Statement-I and Statement-II are correct but Statement-II is not the correct explanation for Statement-I.", "Statement-I is correct but Statement-II is incorrect.", "Statement-I is incorrect but Statement-II is correct."]
    },
    6: {
        "question": "Consider the following statements with reference to GDP calculations in India:\nStatement-I: The year 2022-23 has been chosen in place of 2011-12 as the new base year.\nStatement-II: It represents a recent normal year (after COVID), with availability of robust and comprehensive data across sectors of the economy.\nWhich one of the following is correct in respect of the above statements?",
        "options": ["Both Statement-I and Statement-II are correct and Statement-II is the correct explanation for Statement-I.", "Both Statement-I and Statement-II are correct but Statement-II is not the correct explanation for Statement-I.", "Statement-I is correct but Statement-II is incorrect.", "Statement-I is incorrect but Statement-II is correct."]
    },
    7: {
        "question": "Consider the following instruments:\nI. Commercial Paper\nII. Infrastructure Investment Trusts (InvITs)\nIII. Exchange Traded Funds\nIV. Certificates of deposits\nV. State Development Loans\nHow many of the above given instruments are classified as capital market instruments?",
        "options": ["Only two", "Only three", "Only four", "All five"]
    },
    8: {
        "question": "In the context of finance, the term 'Book Building' refers to:",
        "options": ["A process used to determine the price of securities during a public issue based on investor bids.", "A process by which a company maintains a record of its physical share certificates in a ledger.", "A mechanism where the Reserve Bank of India (RBI) manages the public debt of the Central Government.", "A regulatory process through which market regulators monitor large share transactions."]
    },
    9: {
        "question": "Consider the following statements:\nI. India's agricultural exports have consistently increased in the last five years.\nII. The percentage of agricultural exports in the total merchandise exports has consistently increased in the last five years.\nWhich of the statements given above is/are correct?",
        "options": ["I only", "II only", "Both I and II", "Neither I nor II"]
    },
    67: {
        "question": "Consider the following statements:\n1. If an economy is facing 'bottleneck inflation', the most appropriate response from the government should be to increase the repo rate to reduce the money supply.\n2. A 'positive output gap' in an economy is most likely to lead to demand-pull inflation.\nWhich of the statements given above is/are correct?",
        "options": ["1 only", "2 only", "Both 1 and 2", "Neither 1 nor 2"]
    }
}

# ─── Build final JSON ─────────────────────────────────────────────────────────
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

final = []
bad   = []
for qno in range(1, 101):
    if qno in MANUAL:
        q_txt = MANUAL[qno]["question"]
        opts  = MANUAL[qno]["options"]
    else:
        block = merged.get(qno, "")
        q_txt, opts = extract_options(block)

    correct_letter = ans_map.get(qno, "A")
    correct_idx    = ord(correct_letter) - ord('A')
    correct_text   = opts[correct_idx] if correct_idx < 4 else ""
    explanation    = exp_map.get(qno, "")
    subject        = subject_tag(qno)

    if len(q_txt) < 15 or len(opts[0]) < 3:
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

print(f"Questions still needing review: {bad}")
print(f"Total questions: {len(final)}")

with open(r"d:\upsc test series\paper1_parsed.json", "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

# Show sample of key questions
for qno in [1, 4, 7, 21, 51, 100]:
    q = final[qno-1]
    print(f"\nQ{qno} [{q['subject']}]: {q['question'][:80].strip()}")
    print(f"  A) {q['options'][0][:55]}  B) {q['options'][1][:55]}")
    print(f"  Correct: ({q['correctAnswer']}) {q['correctAnswerText'][:60]}")
