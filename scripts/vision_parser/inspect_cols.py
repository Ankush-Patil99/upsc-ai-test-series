import re, json

with open(r"d:\upsc test series\paper1_cols_right.txt", encoding="utf-8") as f:
    right = f.read()
with open(r"d:\upsc test series\paper1_cols_left.txt", encoding="utf-8") as f:
    left = f.read()

# Show first 120 lines of right column (should have Q3,Q4 etc from page 1)
lines = right.splitlines()
print("=== RIGHT COLUMN first 80 lines ===")
for i, l in enumerate(lines[:80]):
    print(f"{i:3}: {l}")
