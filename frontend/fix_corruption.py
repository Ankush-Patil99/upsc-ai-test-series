
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = 'frontend/app.js'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines before: {len(lines)}")

# Line 985 (0-indexed: 984) is corrupted garbage after the closing brace
# Remove lines 985-993 (0-indexed 984-992), keeping everything through line 984 and from line 994 on
# But line 985 should be just '}\n'

# The good end of renderExamReport ends at line 984 (1-idx) with the solList.appendChild
# Line 985 should be '}' (closing brace of renderExamReport)  
# Lines 986-994 are the garbage dup

new_lines = lines[:984] + ['}\n'] + lines[994:]

print(f"Total lines after: {len(new_lines)}")

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Done!")
