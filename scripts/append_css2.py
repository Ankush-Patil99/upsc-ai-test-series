
new_css = """
/* ======================== PROFILE DROPDOWN ======================== */
.user-badge {
    background: none;
    border: 2px solid var(--accent);
    cursor: pointer;
    font-family: inherit;
}
.user-badge:hover { transform: scale(1.08); box-shadow: 0 0 12px rgba(83,74,183,0.5); }

.profile-dropdown {
    position: absolute;
    top: calc(100% + 10px);
    right: 0;
    width: 280px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5);
    z-index: 1000;
    overflow: hidden;
    animation: dropdown-in 0.2s ease;
}
@keyframes dropdown-in {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.profile-dropdown-header {
    display: flex; align-items: center; gap: 12px;
    padding: 16px 14px;
    background: linear-gradient(135deg, rgba(83,74,183,0.12), rgba(29,158,117,0.06));
}
.profile-dropdown-avatar {
    width: 44px; height: 44px;
    border-radius: 50%; background: var(--accent);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1rem; color: #fff;
    flex-shrink: 0;
}

/* ======================== STREAK CALENDAR POPUP ======================== */
.streak-calendar-popup {
    position: fixed;
    top: 70px; right: 16px;
    width: 340px;
    background: var(--card-bg);
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
    background: #f97316;
    box-shadow: 0 0 6px rgba(249,115,22,0.5);
}
.streak-cal-cell.streak-today {
    background: var(--teal);
    box-shadow: 0 0 8px rgba(29,158,117,0.6);
    border-color: rgba(255,255,255,0.3);
}
.streak-cal-cell.streak-future {
    background: rgba(255,255,255,0.02);
    opacity: 0.3;
}
"""

with open('frontend/style.css', 'a', encoding='utf-8') as f:
    f.write(new_css)

print("CSS appended!")
