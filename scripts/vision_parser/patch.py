with open('frontend/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = '''                <div class="sol-rationale">
                    <div class="sol-rationale-label">✦ AI Explanation</div>
                    ${q.explanation}
                </div>'''

repl = '''                <div class="sol-rationale">
                    <div class="sol-rationale-label">✦ AI Explanation</div>
                    ${q.explanation}
                    ${q.mains_hint ? `<br><br><div style="background:var(--bg);padding:10px;border-left:3px solid var(--primary-light);border-radius:4px;"><strong style="color:var(--primary-light);">Mains Connection:</strong> ${q.mains_hint}</div>` : ''}
                </div>'''

if target in c:
    c = c.replace(target, repl)
    with open('frontend/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Replaced')
else:
    print('Target not found')
