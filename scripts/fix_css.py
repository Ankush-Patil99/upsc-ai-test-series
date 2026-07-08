
import sys

with open('frontend/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

missing_css = """
/* ======================== STREAK CALENDAR POPUP ======================== */
.streak-calendar-popup {
    position: fixed;
    top: 70px; right: 16px;
    width: 360px;
    background: #141420; /* Fully opaque background */
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.6);
    padding: 16px;
    z-index: 1000;
    animation: dropdown-in 0.2s ease;
}
.streak-cal-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px;
}
.streak-cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-top: 4px;
}
.streak-cal-day-label {
    text-align: center; font-size: 0.7rem;
    color: var(--text-faint); font-weight: 600;
    padding-bottom: 4px;
}
.streak-cal-cell {
    aspect-ratio: 1;
    border-radius: 4px;
    background: rgba(255,255,255,0.04);
    border: 1px solid transparent;
    transition: transform 0.1s;
}
.streak-cal-cell:hover { transform: scale(1.2); }
.streak-cal-cell.streak-active {
    background: rgba(249, 115, 22, 0.25); /* Translucent orange */
    border: 1px solid rgba(249, 115, 22, 0.8);
    box-shadow: inset 0 0 6px rgba(249, 115, 22, 0.15);
}
.streak-cal-cell.streak-today {
    background: var(--teal);
    box-shadow: 0 0 8px rgba(29,158,117,0.6);
    border-color: rgba(255,255,255,0.3);
}
"""

if '.streak-calendar-popup {' not in content:
    idx = content.find('.streak-cal-cell.streak-future {')
    if idx != -1:
        new_content = content[:idx] + missing_css + content[idx:]
        with open('frontend/style.css', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("CSS fixed!")
    else:
        print("Marker not found.")
else:
    print("Already exists.")
