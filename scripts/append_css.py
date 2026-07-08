
# Appends new CSS to style.css
new_css = """
/* ======================== QUESTION TAGGING ======================== */
.q-tag-row {
    display: flex; gap: 8px; margin-top: 14px;
    align-items: center; flex-wrap: wrap;
    border-top: 1px solid var(--border);
    padding-top: 12px;
}
.q-tag-label {
    font-size: 0.78rem; color: var(--text-faint);
    margin-right: 2px;
}
.q-tag-btn {
    padding: 4px 12px; border-radius: 20px;
    border: 1px solid var(--border);
    background: rgba(255,255,255,0.04);
    color: var(--text-muted); font-size: 0.78rem;
    cursor: pointer; transition: all 0.2s;
    font-family: inherit;
}
.q-tag-btn:hover { border-color: var(--accent); color: var(--text); }
.q-tag-btn.active-doubt  { background: rgba(239,68,68,0.15);  border-color: #ef4444; color: #ef4444; font-weight: 600; }
.q-tag-btn.active-guess  { background: rgba(234,179,8,0.15);  border-color: #eab308; color: #eab308; font-weight: 600; }
.q-tag-btn.active-revise { background: rgba(59,130,246,0.15); border-color: #3b82f6; color: #3b82f6; font-weight: 600; }

/* ======================== RETRY BUTTONS ======================== */
.btn-retry-wrong {
    padding: 0.55rem 1.2rem; border-radius: 6px;
    background: rgba(239,68,68,0.15); border: 1px solid #ef4444;
    color: #ef4444; font-size: 0.88rem; font-family: inherit;
    cursor: pointer; transition: all 0.2s; font-weight: 600;
}
.btn-retry-wrong:hover { background: rgba(239,68,68,0.3); }
.btn-retry-skip {
    padding: 0.55rem 1.2rem; border-radius: 6px;
    background: rgba(59,130,246,0.12); border: 1px solid #3b82f6;
    color: #3b82f6; font-size: 0.88rem; font-family: inherit;
    cursor: pointer; transition: all 0.2s; font-weight: 600;
}
.btn-retry-skip:hover { background: rgba(59,130,246,0.25); }

/* ======================== REVIEW ZONE CARDS ======================== */
.review-zone-card {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 20px; border-radius: 10px;
    border: 1px solid var(--border); flex: 1; min-width: 160px;
    transition: all 0.2s;
}
.review-zone-card:hover { transform: translateY(-2px); }
.zone-doubt  { background: rgba(239,68,68,0.07);  border-color: rgba(239,68,68,0.3); }
.zone-guess  { background: rgba(234,179,8,0.07);  border-color: rgba(234,179,8,0.3); }
.zone-revise { background: rgba(59,130,246,0.07); border-color: rgba(59,130,246,0.3); }
.zone-icon { font-size: 1.6rem; }
.zone-title { font-size: 0.9rem; font-weight: 700; color: var(--text); margin-bottom: 2px; }
.zone-sub   { font-size: 0.77rem; color: var(--text-muted); }

/* ======================== BADGE SHELF (SIDEBAR) ======================== */
.badge-shelf-wrapper {
    padding: 10px 16px 0;
    margin-top: auto;
}
.badge-shelf-label {
    font-size: 0.7rem; color: var(--text-faint);
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.badge-shelf { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
.badge-icon-pill {
    font-size: 1.2rem; padding: 4px 6px;
    border-radius: 8px; cursor: default;
    transition: transform 0.2s;
    display: inline-flex;
}
.badge-icon-pill.earned { filter: none; }
.badge-icon-pill.earned:hover { transform: scale(1.25); }
.badge-icon-pill.locked {
    background: rgba(255,255,255,0.05); border: 1px solid var(--border);
    color: var(--text-faint); font-size: 0.72rem; padding: 4px 8px;
    border-radius: 10px;
}

/* ======================== BADGE TOAST (ANIMATION) ======================== */
.badge-toast {
    position: fixed; bottom: -120px; right: 24px;
    z-index: 9999;
    display: flex; align-items: center; gap: 16px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid rgba(255,215,0,0.4);
    border-radius: 16px; padding: 18px 24px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.6), 0 0 30px rgba(255,215,0,0.15);
    transition: bottom 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.5s;
    min-width: 280px; max-width: 340px;
    opacity: 0;
}
.badge-toast-visible {
    bottom: 32px;
    opacity: 1;
}
.badge-toast-glow {
    position: absolute; inset: -2px; border-radius: 18px;
    background: linear-gradient(135deg, rgba(255,215,0,0.3), rgba(255,150,0,0.1));
    z-index: -1; animation: badge-glow-pulse 1.5s ease-in-out infinite alternate;
}
@keyframes badge-glow-pulse {
    from { opacity: 0.4; }
    to   { opacity: 1; }
}
.badge-toast-icon {
    font-size: 2.8rem;
    animation: badge-icon-bounce 0.6s ease-out 0.3s both;
}
@keyframes badge-icon-bounce {
    0%   { transform: scale(0) rotate(-20deg); }
    60%  { transform: scale(1.3) rotate(5deg); }
    100% { transform: scale(1) rotate(0); }
}
.badge-toast-body { flex: 1; }
.badge-toast-title {
    font-size: 0.7rem; color: #fbbf24;
    text-transform: uppercase; letter-spacing: 0.1em;
    font-weight: 700; margin-bottom: 2px;
}
.badge-toast-name {
    font-size: 1.05rem; color: #fff;
    font-weight: 700; margin-bottom: 2px;
}
.badge-toast-desc {
    font-size: 0.78rem; color: rgba(255,255,255,0.6);
}

/* ======================== REPORT ACTIONS (UPDATED) ======================== */
.report-actions {
    display: flex; gap: 10px; flex-wrap: wrap; margin-top: 1.2rem;
}
"""

with open('frontend/style.css', 'a', encoding='utf-8') as f:
    f.write(new_css)

print("CSS appended successfully!")
