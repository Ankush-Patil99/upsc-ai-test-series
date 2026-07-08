import pdfplumber

def extract_pdf_text(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n\n"
    return text

q_text = extract_pdf_text(r"d:\upsc test series\data\pyqs\Other test series\1.pdf")
a_text = extract_pdf_text(r"d:\upsc test series\data\pyqs\Other test series\1.1.pdf")

with open(r"d:\upsc test series\paper1_questions_raw.txt", "w", encoding="utf-8") as f:
    f.write(q_text)

with open(r"d:\upsc test series\paper1_answers_raw.txt", "w", encoding="utf-8") as f:
    f.write(a_text)

print("Done! Lines in Q:", len(q_text.splitlines()), "Lines in A:", len(a_text.splitlines()))
