
new_css = """
/* ======================== STREAK CALENDAR CELL CONTENT ======================== */
.streak-cal-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}
.cal-day-num {
    font-size: 0.65rem;
    font-weight: 700;
    color: rgba(255,255,255,0.9);
    line-height: 1;
}
.cal-day-num-muted {
    font-size: 0.6rem;
    font-weight: 400;
    color: var(--text-faint);
    line-height: 1;
}
.cal-q-count {
    font-size: 0.52rem;
    color: rgba(255,255,255,0.75);
    margin-top: 1px;
    line-height: 1;
}
.streak-cal-cell.streak-inactive {
    background: rgba(255,255,255,0.02);
}
"""

with open('frontend/style.css', 'a', encoding='utf-8') as f:
    f.write(new_css)

print("CSS appended!")
