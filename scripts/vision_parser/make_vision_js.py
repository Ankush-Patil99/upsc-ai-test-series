import json

with open(r"d:\upsc test series\paper1_parsed.json", encoding="utf-8") as f:
    data = json.load(f)

js_lines = ["const VISION_TEST_QUESTIONS = ["]

for q in data:
    opts = q['options']
    correct = q['correctAnswer'].lower()
    
    # Format options nicely
    options_str = f"{{ a: {repr(opts[0])}, b: {repr(opts[1])}, c: {repr(opts[2])}, d: {repr(opts[3])} }}"
    
    js_lines.append("    {")
    js_lines.append(f"        question: {repr(q['question'])},")
    js_lines.append(f"        options: {options_str},")
    js_lines.append(f"        correct: {repr(correct)},")
    js_lines.append(f"        explanation: {repr(q['explanation'])},")
    js_lines.append(f"        subject: {repr(q['subject'])}")
    js_lines.append("    },")

js_lines.append("];")

with open(r"d:\upsc test series\frontend\vision_test.js", "w", encoding="utf-8") as f:
    f.write("\n".join(js_lines))

print("Created vision_test.js")
