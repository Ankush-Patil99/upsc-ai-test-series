/* =========================================================
   UPSC PRELIMS AI — FRONTEND APPLICATION
   Covers: Auth, Test Series (CBT), Analytics, MCQ Generator
   ========================================================= */

'use strict';

// ======================== APP STATE ========================
const AppState = {
    user: null,
    currentSection: 'tests',
    sidebarCollapsed: false,
    panelStates: JSON.parse(localStorage.getItem('panelStates') || '{"full-length":true,"topic-wise":true}'),
    testAttempts: JSON.parse(localStorage.getItem('upsc_prototypeAttempts_v1') || '[]'),
    recentGenerations: JSON.parse(localStorage.getItem('recentGenerations') || '[]'),
    genTopic: '',
    genCount: 10,
    generatedQuestions: [],
    genAnswers: {},
    // CBT State
    cbtTest: null,
    cbtState: [],
    cbtCurrentQ: 0,
    cbtTimerInterval: null,
    cbtTimeRemaining: 0,
    cbtStartTime: null,
    // Charts
    subjectChart: null,
    trendChart: null,
    // Table
    historyData: [],
    historyFiltered: [],
    historyPage: 1,
    historyPageSize: 7,
    historySortKey: 'date',
    historySortDir: -1,
    // Topic dropdown
    dropdownFocusIndex: -1,
};

// ======================== MOCK DATA ========================
const MOCK_FULL_TESTS = [
    { id: 4, title: 'Vision IAS Full Length Test', questions: 100, duration: '2 hr', type: 'GS-1', status: 'new', paperType: 'General Studies I' }
];

const SUBJECTS = [
    { name: 'History', icon: '📜', tests: [
        { id: 101, title: 'History — Subject Wise Test', questions: 50, duration: '60 min', type: 'Subject-Wise', status: 'new' },
        { id: 100, title: 'History & Art and Culture — Combined', questions: 50, duration: '60 min', type: 'Subject-Wise', status: 'new' }
    ]},
    { name: 'Art and culture', icon: '🎭', tests: [
        { id: 102, title: 'Art & Culture — Subject Wise Test', questions: 31, duration: '40 min', type: 'Subject-Wise', status: 'new' },
        { id: 100, title: 'History & Art and Culture — Combined', questions: 50, duration: '60 min', type: 'Subject-Wise', status: 'new' }
    ]},
    { name: 'Geography', icon: '🌏', tests: [] },
    { name: 'Polity', icon: '⚖️', tests: [] },
    { name: 'International relations', icon: '🤝', tests: [] },
    { name: 'Economics', icon: '💹', tests: [] },
    { name: 'Science and technology', icon: '🔬', tests: [] },
    { name: 'Environment, agriculture and biodiversity', icon: '🌿', tests: [] }
];

const SUBJECT_ACCURACY = {};

const SCORE_TREND = {
    all: []
};

const MOCK_HISTORY = [];

const TOPIC_SUGGESTIONS_DB = [
    'Polity – Fundamental Rights', 'Polity – DPSP Directive Principles', 'Economy – RBI Monetary Policy',
    'History – Non-Cooperation Movement', 'History – Revolt of 1857', 'Geography – Monsoon System',
    'Geography – Indian Rivers', 'Environment – Ramsar Wetland Sites', 'Environment – IUCN Red List',
    'Science – ISRO Space Missions', 'Science – mRNA Vaccines', 'Current Affairs – G20 Summit',
    'Polity – Constitutional Amendments', 'Economy – Union Budget 2025', 'History – Mughal Empire',
    'Geography – Himalayas Formation', 'Environment – Climate Change CoP', 'Art – UNESCO Heritage Sites',
    'Ethics – Gandhian Ethics', 'Internal Security – LWE', 'Economy – GST & Tax Structure',
    'Polity – Emergency Provisions', 'Science – Quantum Computing', 'Current Affairs – India-China Relations',
];

const SEMANTIC_SUGGESTIONS_DB = [
    { q: 'fundamental', s: 'Constitutional Morality & Liberal Values' },
    { q: 'economy', s: 'Inclusive Growth & Sustainable Development' },
    { q: 'history', s: 'Subaltern Movements & Social Reform' },
    { q: 'environment', s: 'Ecosystem Services & Biodiversity Hotspots' },
    { q: 'science', s: 'Dual-use Technology & National Security' },
    { q: 'polity', s: 'Federalism & Centre-State Relations' },
];

// Sample questions for generator
function generateSampleQuestions(topic, count) {
    const questions = [
        {
            question: `Under which article of the Indian Constitution is the Right to Equality guaranteed to all citizens, particularly in context of ${topic}?`,
            options: { a: 'Article 14 – Equality before law', b: 'Article 19 – Freedom of speech', c: 'Article 21 – Right to life', d: 'Article 32 – Right to constitutional remedies' },
            correct: 'a',
            explanation: `Article 14 guarantees equality before law and equal protection of laws to all persons. This is particularly relevant in the context of ${topic} as it forms the foundational right. The Supreme Court has expanded this through the "reasonable classification" doctrine. Articles 15-18 further operationalize equality in specific domains.`
        },
        {
            question: `Which of the following international organizations is PRIMARILY responsible for setting global standards related to ${topic} at the multilateral level?`,
            options: { a: 'World Bank Group', b: 'United Nations Environment Programme (UNEP)', c: 'International Monetary Fund', d: 'World Trade Organization' },
            correct: 'b',
            explanation: `UNEP, established in 1972 after the Stockholm Conference, serves as the primary UN authority on ${topic}-related global standards. It coordinates international environmental agreements and provides technical assistance to developing nations. The Nairobi-based agency oversees major conventions relevant to environmental topics.`
        },
        {
            question: `In the context of ${topic}, the Comptroller and Auditor General (CAG) of India derives authority from which constitutional provision?`,
            options: { a: 'Article 148', b: 'Article 112', c: 'Article 280', d: 'Article 324' },
            correct: 'a',
            explanation: `Article 148 of the Indian Constitution establishes the CAG as a constitutional authority. The CAG audits accounts of the Union and all State governments. This is crucial in the context of ${topic} as financial accountability mechanisms are  central to governance. The CAG's reports are placed before Parliament and State Legislatures.`
        },
        {
            question: `With reference to ${topic}, which of the following statements is/are CORRECT?\n1. India ratified the Paris Agreement in 2016\n2. The Nationally Determined Contributions (NDCs) are legally binding\n3. Green Climate Fund was established under UNFCCC`,
            options: { a: '1 and 3 only', b: '2 and 3 only', c: '1 only', d: '1, 2 and 3' },
            correct: 'a',
            explanation: `Statements 1 and 3 are correct. India ratified the Paris Agreement in October 2016. NDCs are NOT legally binding — only the obligation to submit and regularly update them is binding. The Green Climate Fund (GCF) was established under UNFCCC's COP 17 in Durban (2011). This multi-statement format is classic UPSC Prelims structure.`
        },
        {
            question: `The discovery most closely associated with revolutionizing our understanding of ${topic} was made by which scientist and in which year?`,
            options: { a: 'Watson and Crick – 1953', b: 'Louis Pasteur – 1857', c: 'Marie Curie – 1898', d: 'Charles Darwin – 1859' },
            correct: 'a',
            explanation: `Watson and Crick's discovery of the double-helix structure of DNA in 1953 is considered a watershed moment. This is used as an analogy in the context of ${topic} to illustrate paradigm-shifting discoveries. The work was based on Rosalind Franklin's X-ray crystallography data (Photo 51), for which they won the Nobel Prize in 1962.`
        },
    ];
    const result = [];
    for (let i = 0; i < count; i++) {
        result.push({ ...questions[i % questions.length], id: i + 1 });
    }
    return result;
}

// ======================== AUTH ========================
function switchAuthTab(tab) {
    document.getElementById('tab-login').classList.toggle('active', tab === 'login');
    document.getElementById('tab-signup').classList.toggle('active', tab === 'signup');
    document.getElementById('form-login').classList.toggle('active', tab === 'login');
    document.getElementById('form-signup').classList.toggle('active', tab === 'signup');
}

// ======================== API HELPER ========================
// Attaches the JWT token from localStorage to every request automatically.
async function apiFetch(url, options = {}) {
    const token = localStorage.getItem('upsc_token');
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(url, { ...options, headers });
    return res;
}

// ======================== GOOGLE SIGN-IN ========================
function triggerGoogleSignIn() {
    // Get the Client ID from the meta tag in index.html
    const clientId = document.querySelector('meta[name="google-client-id"]')?.content;

    if (!clientId || clientId.startsWith('YOUR_GOOGLE')) {
        const errId = document.getElementById('form-login').classList.contains('active')
            ? 'google-login-error' : 'google-signup-error';
        const el = document.getElementById(errId);
        el.textContent = 'Google Sign-In is not configured. See setup instructions.';
        el.classList.remove('hidden');
        return;
    }

    // Use Google Identity Services to show the account picker popup
    if (window.google && window.google.accounts) {
        window.google.accounts.id.initialize({
            client_id: clientId,
            callback: onGoogleSignIn,
            ux_mode: 'popup',
            cancel_on_tap_outside: true,
        });
        window.google.accounts.id.prompt();  // show the One Tap / account picker
    } else {
        console.error('[Google] GSI library not loaded yet.');
    }
}

async function onGoogleSignIn(googleResponse) {
    // googleResponse.credential is the ID token from Google
    const errorEl = document.getElementById('google-login-error');
    errorEl.classList.add('hidden');

    try {
        const res  = await fetch('/api/auth/google', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ credential: googleResponse.credential }),
        });
        const data = await res.json();

        if (!res.ok) {
            errorEl.textContent = data.detail || 'Google Sign-In failed. Please try again.';
            errorEl.classList.remove('hidden');
            document.getElementById('google-signup-error').textContent = errorEl.textContent;
            document.getElementById('google-signup-error').classList.remove('hidden');
            return;
        }

        // Success — same flow as email login
        saveSession(data);
        enterApp();

    } catch (err) {
        errorEl.textContent = 'Cannot reach server. Is the backend running?';
        errorEl.classList.remove('hidden');
    }
}

// ======================== AUTH ========================
function switchAuthTab(tab) {
    document.getElementById('tab-login').classList.toggle('active', tab === 'login');
    document.getElementById('tab-signup').classList.toggle('active', tab === 'signup');
    document.getElementById('form-login').classList.toggle('active', tab === 'login');
    document.getElementById('form-signup').classList.toggle('active', tab === 'signup');
}

async function handleLogin(e) {
    e.preventDefault();
    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl  = document.getElementById('login-error');
    const btn      = document.getElementById('btn-login');

    errorEl.classList.add('hidden');

    if (!email || password.length < 6) {
        errorEl.textContent = 'Please enter a valid email and password (min 6 chars).';
        errorEl.classList.remove('hidden');
        return;
    }

    btn.textContent = 'Signing in...';
    btn.disabled = true;

    try {
        const res  = await fetch('/api/auth/login', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ email, password }),
        });
        const data = await res.json();

        if (!res.ok) {
            const detail = data.detail;

            // Lockout (429) — show countdown and disable button temporarily
            if (res.status === 429) {
                const resetIn = detail.reset_in || 60;
                const msg     = detail.message || `Too many attempts. Try again in ${resetIn}s.`;
                errorEl.innerHTML = `🔒 ${msg}`;
                errorEl.classList.remove('hidden');

                // Countdown on button
                let remaining = resetIn;
                const interval = setInterval(() => {
                    remaining--;
                    btn.textContent = `Locked (${remaining}s)`;
                    if (remaining <= 0) {
                        clearInterval(interval);
                        btn.textContent = 'Sign In →';
                        btn.disabled = false;
                        errorEl.classList.add('hidden');
                    }
                }, 1000);
                return;   // keep button disabled during countdown
            }

            // Wrong password (401) — show remaining attempts
            if (res.status === 401 && detail.remaining !== undefined) {
                const left = detail.remaining;
                errorEl.innerHTML = left > 0
                    ? `❌ Incorrect email or password. &nbsp;<strong>${left} attempt${left === 1 ? '' : 's'} remaining.</strong>`
                    : `🔒 Too many failed attempts. Please wait and try again.`;
            } else {
                errorEl.textContent = (typeof detail === 'string' ? detail : detail.message) || 'Login failed.';
            }
            errorEl.classList.remove('hidden');
            return;
        }

        saveSession(data);
        enterApp();

    } catch (err) {
        errorEl.textContent = 'Cannot reach server. Is the backend running?';
        errorEl.classList.remove('hidden');
    } finally {
        // Only re-enable if not in lockout countdown
        if (!btn.textContent.includes('Locked')) {
            btn.textContent = 'Sign In →';
            btn.disabled = false;
        }
    }
}   // end handleLogin

async function handleSignup(e) {

    e.preventDefault();
    const name     = document.getElementById('signup-name').value.trim();
    const email    = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const errorEl  = document.getElementById('signup-error');
    const btn      = document.getElementById('btn-signup');

    errorEl.classList.add('hidden');

    if (!name || !email || password.length < 6) {
        errorEl.textContent = 'All fields required. Password must be 6+ characters.';
        errorEl.classList.remove('hidden');
        return;
    }

    btn.textContent = 'Creating account...';
    btn.disabled = true;

    try {
        const res  = await fetch('/api/auth/register', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ name, email, password }),
        });
        const data = await res.json();

        if (!res.ok) {
            errorEl.textContent = data.detail || 'Registration failed. Please try again.';
            errorEl.classList.remove('hidden');
            return;
        }

        // Success — token returned immediately, log user in
        saveSession(data);
        enterApp();

    } catch (err) {
        errorEl.textContent = 'Cannot reach server. Is the backend running?';
        errorEl.classList.remove('hidden');
    } finally {
        btn.textContent = 'Create Account →';
        btn.disabled = false;
    }
}

// ── Google Identity Services Integration ──────────────────────────────────────────

// ── Google Identity Services Integration ──────────────────────────────────────────

function initGoogleLogin() {
    const clientId = document.querySelector('meta[name="google-client-id"]').content;
    
    google.accounts.id.initialize({
        client_id: clientId,
        callback: window.handleGoogleResponse,
        auto_select: false,
        cancel_on_tap_outside: true
    });

    // Render the button in the login form
    const loginTarget = document.getElementById('google-btn-login-render');
    if (loginTarget) {
        google.accounts.id.renderButton(loginTarget, {
            theme: "outline",
            size: "large",
            width: "100%",
            text: "signin_with",
            shape: "pill"
        });
    }

    // Render the button in the signup form
    const signupTarget = document.getElementById('google-btn-signup-render');
    if (signupTarget) {
        google.accounts.id.renderButton(signupTarget, {
            theme: "outline",
            size: "large",
            width: "100%",
            text: "signup_with",
            shape: "pill"
        });
    }
}

// In case GSI script finishes loading AFTER app.js
window.onGoogleLibraryLoad = initGoogleLogin;

// In case GSI script finishes loading BEFORE app.js
if (typeof google === 'object' && google.accounts && google.accounts.id) {
    initGoogleLogin();
}


window.handleGoogleResponse = async (response) => {
    // This fires when Google successfully authenticates the user
    // The response.credential is the JWT Token given by Google
    const credential = response.credential;
    
    // Pick the currently active form's error element to show any backend errors
    const isLogin = document.getElementById('form-login').classList.contains('active');
    const errorEl = document.getElementById(isLogin ? 'google-login-error' : 'google-signup-error');
    errorEl.classList.add('hidden');

    try {
        const res = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            errorEl.textContent = data.detail || 'Google Sign-In failed.';
            errorEl.classList.remove('hidden');
            return;
        }

        // Backend successfully verified Google token and returned our own session token
        saveSession(data);
        enterApp();

    } catch (err) {
        errorEl.textContent = 'Cannot reach server. Is the backend running?';
        errorEl.classList.remove('hidden');
    }
};

function saveSession(data) {
    // data = { token, user_id, name, email, role }
    localStorage.setItem('upsc_token', data.token);
    const avatar = data.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
    AppState.user = { ...data, avatar };
    localStorage.setItem('upsc_user', JSON.stringify(AppState.user));
}


function handleLogout() {
    // Blacklist the token on the server first, then clear local state
    const token = localStorage.getItem('upsc_token');
    if (token) {
        fetch('/api/auth/logout', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        }).catch(() => { /* silent fail — still clear local storage */ });
    }
    localStorage.removeItem('upsc_token');
    localStorage.removeItem('upsc_user');
    AppState.user = null;
    document.getElementById('app').classList.add('hidden');
    document.getElementById('auth-overlay').classList.remove('hidden');
    document.getElementById('login-email').value    = '';
    document.getElementById('login-password').value = '';
}


function enterApp() {
    document.getElementById('auth-overlay').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    updateUserUI();
    initApp();
}

function updateUserUI() {
    const u = AppState.user;
    if (!u) return;

    const safeSet = (id, fn) => { const el = document.getElementById(id); if (el) fn(el); };

    // Sidebar avatar + name
    const avatarNode = document.getElementById('user-avatar');
    if (avatarNode) avatarNode.innerHTML = `<span id="user-avatar-text">${u.avatar}</span>`;
    safeSet('user-display-name', el => el.textContent = u.name);
    safeSet('topbar-user-badge', el => el.textContent = u.avatar);

    // Username from email prefix for uniqueness
    const username = '@' + (u.email
        ? u.email.split('@')[0].toLowerCase().replace(/[^a-z0-9_]/g, '_')
        : u.name.toLowerCase().replace(/\s+/g, '_'));
    safeSet('user-username', el => el.textContent = username);

    // Load saved DP image across all avatar elements
    const dpData = localStorage.getItem('upsc_dp_image');
    if (dpData) {
        ['profile-avatar', 'modal-dp'].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.style.backgroundImage = `url(${dpData})`; el.style.backgroundSize = 'cover'; }
        });
        ['profile-avatar-text', 'modal-dp-text', 'user-avatar-text'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        safeSet('topbar-user-badge', el => {
            el.style.backgroundImage = `url(${dpData})`;
            el.style.backgroundSize = 'cover';
            el.textContent = '';
        });
        if (avatarNode) { avatarNode.style.backgroundImage = `url(${dpData})`; avatarNode.style.backgroundSize = 'cover'; }
    }

    // Load saved cover image (only in profile modal, not AP dropdown)
    const coverData = localStorage.getItem('upsc_cover_image');
    if (coverData) {
        safeSet('modal-cover-bg', el => el.style.backgroundImage = `url(${coverData})`);
    }

    // Premium cosmetics and Features UI
    const goPremiumBtn = document.querySelector('.ppm-btn-premium');
    const premButtons = document.querySelectorAll('button[onclick="openRemedialConfigModal()"], button[onclick="startSmartReviewTest()"], button[onclick="startCustomRemedialTest()"], #notes-upload-btn, #gen-tab-notes, button[onclick="exportTestPDF()"]');

    if (u.isPremium) {
        safeSet('user-avatar', el => el.classList.add('premium-avatar'));
        safeSet('topbar-user-badge', el => el.classList.add('premium-avatar'));
        const roleEl = document.querySelector('.user-role');
        if (roleEl) roleEl.innerHTML = 'UPSC 2025 · <span style="color:var(--gold);font-weight:700;">PRO Member 👑</span>';
        const modalRoleEl = document.getElementById('modal-profile-role');
        if (modalRoleEl) modalRoleEl.innerHTML = 'UPSC 2025 · <span style="color:var(--gold);font-weight:700;">PRO Member 👑</span>';
        
        // Hide 'Go Premium' button if they are already premium
        if (goPremiumBtn) goPremiumBtn.style.display = 'none';

        // Style premium feature buttons as normal/native to the app for Premium users
        premButtons.forEach(btn => {
            btn.innerHTML = btn.innerHTML.replace(/👑/g, '').trim();
            if (btn.id === 'gen-tab-notes') return;
            if (btn.getAttribute('onclick') === 'exportTestPDF()' && btn.classList.contains('btn-ghost-sm')) {
                btn.style.color = 'var(--text)';
                btn.style.borderColor = 'var(--border)';
                return;
            }
            btn.style.background = 'var(--primary)';
            btn.style.color = 'white';
            btn.style.border = 'none';
            btn.style.boxShadow = '0 4px 14px var(--primary-glow)';
            btn.style.textShadow = 'none';
        });

        const safeStyle = (id, styles) => { const el = document.getElementById(id); if (el) Object.assign(el.style, styles); };
        safeSet('notes-promo-title', el => el.textContent = 'Upload Custom Material');
        safeStyle('notes-promo-title', { color: 'var(--text)', textShadow: 'none' });
        safeSet('notes-promo-desc', el => el.innerHTML = 'Upload your personal notes, coaching PDFs, standard books, or current affairs compilations to generate highly-targeted MCQs.');

        // Setup Sidebar Pro Timer
        const sidebarTimerEl = document.getElementById('sidebar-pro-timer');
        const sidebarUserEl = document.getElementById('sidebar-user');
        if (sidebarTimerEl && sidebarUserEl) {
            sidebarTimerEl.style.display = 'block';
            sidebarUserEl.style.background = 'linear-gradient(135deg, rgba(212,175,55,0.15), rgba(212,175,55,0.05))';
            sidebarUserEl.style.border = '1px solid rgba(212,175,55,0.3)';
            sidebarUserEl.style.borderRadius = '12px';
            
            if (!window._proTimerInterval) {
                let end = Date.now() + (30 * 24 * 60 * 60 * 1000);
                const updateT = () => {
                    let diff = end - Date.now();
                    if (diff < 0) diff = 0;
                    let d = Math.floor(diff / (1000 * 60 * 60 * 24));
                    let h = Math.floor((diff / (1000 * 60 * 60)) % 24);
                    let m = Math.floor((diff / (1000 * 60)) % 60);
                    sidebarTimerEl.textContent = `PRO EXPIRES: ${d}d ${h}h ${m}m`;
                };
                updateT();
                window._proTimerInterval = setInterval(updateT, 60000);
            }
        }

    } else {
        safeSet('user-avatar', el => el.classList.remove('premium-avatar'));
        safeSet('topbar-user-badge', el => el.classList.remove('premium-avatar'));
        
        if (goPremiumBtn) goPremiumBtn.style.display = 'flex';

        const sidebarTimerEl = document.getElementById('sidebar-pro-timer');
        const sidebarUserEl = document.getElementById('sidebar-user');
        if (sidebarTimerEl && sidebarUserEl) {
            sidebarTimerEl.style.display = 'none';
            sidebarUserEl.style.background = '';
            sidebarUserEl.style.border = '';
        }
        
        const safeStyle = (id, styles) => { const el = document.getElementById(id); if (el) Object.assign(el.style, styles); };
        safeSet('notes-promo-title', el => el.textContent = 'Unlock Limitless Generation');
        safeStyle('notes-promo-title', { color: 'var(--gold)', textShadow: '0 0 10px rgba(212,175,55,0.3)' });
        safeSet('notes-promo-desc', el => el.innerHTML = 'Upload <strong>ANY</strong> study material—personal notes, coaching PDFs, standard books, or current affairs compilations. The system will instantly analyze the document and generate highly-targeted MCQs specifically from your content!');

        // Style premium feature buttons as gold/premium for Free users
        premButtons.forEach(btn => {
            if (!btn.innerHTML.includes('👑')) {
                btn.innerHTML = btn.innerHTML + ' 👑';
            }
            if (btn.id === 'gen-tab-notes') return;
            if (btn.getAttribute('onclick') === 'exportTestPDF()' && btn.classList.contains('btn-ghost-sm')) {
                btn.style.color = 'var(--gold)';
                btn.style.borderColor = 'var(--gold)';
                return;
            }
            btn.style.background = 'linear-gradient(135deg, #FFDF00 0%, #D4AF37 100%)';
            btn.style.color = '#111';
            btn.style.border = '1px solid #B8860B';
            btn.style.boxShadow = '0 4px 15px rgba(212,175,55,0.3), inset 0 1px 1px rgba(255,255,255,0.6)';
            btn.style.textShadow = '0 1px 0 rgba(255,255,255,0.4)';
        });
    }
}


// ======================== APP INIT ========================
function initApp() {
    renderTestSeries();
    initAnalytics();
    renderRecentGenerations();
    updateTopbarStats();
    applyPanelStates();
    updateBadgeDisplay();
    initCountdown();
    // Show current streak in topbar
    const streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"count":0}');
    const streakEl = document.getElementById('topbar-streak');
    if (streakEl) streakEl.textContent = streakData.count + 'd streak';
    
    updateDailyQuotaUI();
    initMidnightCountdown();
    updateThemeLabel();
}

function updateTopbarStats() {
    // topbar-tests and topbar-avg removed per user request
}

// ======================== NAVIGATION ========================
function switchSection(section, el) {
    // Sections (including friends and profile)
    ['tests', 'analytics', 'generator', 'friends', 'profile'].forEach(s => {
        const sec = document.getElementById(`section-${s}`);
        if (sec) sec.classList.toggle('active', s === section);
    });

    // Sidebar nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.mob-nav-item').forEach(n => n.classList.remove('active'));
    if (el) {
        el.classList.add('active');
        const mobId = 'mob-nav-' + section;
        const mob = document.getElementById(mobId);
        if (mob) mob.classList.add('active');
    }

    // Page title
    const titles = { tests: 'Test Series', analytics: 'Analytics Dashboard', generator: 'Question Generator', friends: 'Friends & Network', profile: 'User Profile' };
    document.getElementById('page-title').textContent = titles[section] || section;
    AppState.currentSection = section;
    
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) dropdown.classList.add('hidden');

    // On analytics — init charts if not done
    if (section === 'analytics') {
        setTimeout(() => { initCharts(); initHistoryTable(); }, 50);
    }
    // On friends — render the tab
    if (section === 'friends') {
        setTimeout(() => { if (typeof switchFriendsTab === 'function') switchFriendsTab('network'); }, 50);
    }

    // Close mobile nav
    document.getElementById('sidebar').classList.remove('mobile-open');
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        sidebar.classList.toggle('mobile-open');
    } else {
        sidebar.classList.toggle('collapsed');
        AppState.sidebarCollapsed = !AppState.sidebarCollapsed;
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
    updateThemeLabel();
    // Re-init charts to match theme
    if (AppState.subjectChart) { AppState.subjectChart.destroy(); AppState.subjectChart = null; }
    if (AppState.trendChart) { AppState.trendChart.destroy(); AppState.trendChart = null; }
    if (AppState.currentSection === 'analytics') setTimeout(initCharts, 50);
}

function updateThemeLabel() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const label = document.getElementById('ppm-theme-label');
    const icon = document.getElementById('ppm-theme-icon');
    if (label) label.textContent = isDark ? 'Dark' : 'Light';
    if (icon) icon.textContent = isDark ? '🌙' : '☀️';
}

// ======================== TEST SERIES ========================
function renderTestSeries() {
    renderFullLengthTests();
    renderSubjectGrid();
}

async function renderFullLengthTests() {
    const grid = document.getElementById('full-length-grid');
    grid.innerHTML = '';

    // Update MOCK_FULL_TESTS with status from attempts history
    AppState.testAttempts.forEach(attempt => {
        if (attempt.id) {
            const mockTest = MOCK_FULL_TESTS.find(t => t.id == attempt.id || t.title === attempt.test);
            if (mockTest) {
                mockTest.status = 'attempted';
                mockTest.score = attempt.score;
            }
        }
    });

    // Always show MOCK_FULL_TESTS (includes locally injected papers like Vision IAS)
    const apiIds = new Set();

    try {
        const res = await apiFetch('/api/tests/');
        const data = await res.json();
        if (data.status === 'success' && data.tests && data.tests.length > 0) {
            AppState.fullTests = data.tests.map(test => {
                // Check if this API test was attempted
                const attempt = AppState.testAttempts.find(a => a.id == test.id || a.test === test.topic);
                return {
                    id: test.id,
                    title: test.topic,
                    questions: test.count,
                    duration: '2 hr',
                    type: test.paper_type,
                    status: attempt ? 'attempted' : 'new',
                    score: attempt ? attempt.score : undefined,
                    paperType: test.paper_type
                };
            });
            AppState.fullTests.forEach(test => {
                apiIds.add(test.id);
                grid.appendChild(buildTestCard(test, false));
            });
        }
    } catch(e) {
        console.error("Failed to load real tests", e);
    }

    // Always append any MOCK_FULL_TESTS not already shown from API
    MOCK_FULL_TESTS.forEach(test => {
        if (!apiIds.has(test.id)) {
            grid.appendChild(buildTestCard(test, false));
        }
    });
}

function buildTestCard(test, withDifficulty) {
    const card = document.createElement('div');
    card.className = 'test-card';

    let statusBadge = '';
    if (test.status === 'new') statusBadge = '<span class="badge-new">New</span>';
    else if (test.status === 'attempted') statusBadge = '<span class="badge-attempted">Attempted</span>';
    else if (test.status === 'inprogress') statusBadge = '<span class="badge-inprogress">In Progress</span>';

    let diffBadge = '';
    if (withDifficulty) {
        if (test.difficulty === 'easy') diffBadge = '<span class="badge-easy">Easy</span>';
        else if (test.difficulty === 'medium') diffBadge = '<span class="badge-medium">Medium</span>';
        else if (test.difficulty === 'hard') diffBadge = '<span class="badge-hard">Hard</span>';
    }

    let progressHTML = '';
    if ((test.status === 'attempted' || test.status === 'inprogress') && test.score !== undefined) {
        const pct = test.score;
        const cls = pct >= 70 ? 'green' : pct >= 50 ? 'amber' : 'red';
        progressHTML = `
            <div class="test-score-bar">
                <div class="test-score-label">Score: ${pct}%</div>
                <div class="progress-track"><div class="progress-fill ${cls}" style="width:${pct}%"></div></div>
            </div>`;
    }

    const paperInfo = test.paperType || test.type || '';
    card.innerHTML = `
        <div class="test-card-header">
            <div class="test-card-title">${test.title}</div>
        </div>
        <div class="test-card-meta">
            <span class="test-meta-item">📝 ${test.questions} Qs</span>
            <span class="test-meta-item">⏱ ${test.duration || '-- min'}</span>
            ${paperInfo ? `<span class="test-meta-item">📄 ${paperInfo}</span>` : ''}
        </div>
        <div class="test-card-badges">
            ${statusBadge}
            ${diffBadge}
        </div>
        <div class="test-card-footer" style="display:flex; flex-direction:column; gap:10px;">
            ${progressHTML}
            <div style="display:flex; gap: 8px; width:100%;">
                <button class="btn-attempt" onclick="startTest(${test.id})" style="flex:1;">
                    ${test.status === 'inprogress' ? 'Continue →' : 'Attempt →'}
                </button>
                ${test.status === 'attempted' ? `<button class="btn-retry-skip" onclick="startRetryFromView(${test.id}, 'both')" style="flex:1; padding: 8px 12px; font-size: 0.85rem;" title="Retry Unanswered & Wrong Questions">Retry Mistakes</button>` : ''}
            </div>
        </div>
    `;
    return card;
}

function renderSubjectGrid() {
    const grid = document.getElementById('subject-grid');
    grid.innerHTML = '';

    SUBJECTS.forEach((subj, idx) => {
        const div = document.createElement('div');
        div.className = 'subject-card';
        div.id = `subj-card-${idx}`;

        div.innerHTML = `
            <div class="subject-card-icon">${subj.icon}</div>
            <div class="subject-card-name">${subj.name}</div>
            <div class="subject-card-count">${subj.tests.length} tests available</div>
            <div class="subject-card-chevron">▼</div>
        `;

        // Tests list (hidden by default)
        const testsDiv = document.createElement('div');
        testsDiv.className = 'subject-tests-list';
        testsDiv.id = `subj-tests-${idx}`;
        subj.tests.forEach(t => testsDiv.appendChild(buildTestCard({ ...t, duration: `${Math.ceil(t.questions * 1.5)}m` }, true)));

        div.addEventListener('click', () => {
            const isExp = div.classList.contains('expanded');
            // Collapse all
            document.querySelectorAll('.subject-card').forEach(c => c.classList.remove('expanded'));
            document.querySelectorAll('.subject-tests-list').forEach(l => l.classList.remove('visible'));
            if (!isExp) {
                div.classList.add('expanded');
                testsDiv.classList.add('visible');
            }
        });

        const wrapper = document.createElement('div');
        wrapper.appendChild(div);
        wrapper.appendChild(testsDiv);
        grid.appendChild(wrapper);
    });
}

// Panel collapse/expand
function togglePanel(id) {
    const body = document.getElementById(`body-${id}`);
    const chevron = document.getElementById(`chevron-${id}`);
    const isCollapsed = body.classList.contains('collapsed');

    body.classList.toggle('collapsed', !isCollapsed);
    chevron.classList.toggle('rotated', isCollapsed);

    AppState.panelStates[id] = !isCollapsed;
    localStorage.setItem('panelStates', JSON.stringify(AppState.panelStates));
}

function applyPanelStates() {
    Object.keys(AppState.panelStates).forEach(id => {
        const isOpen = AppState.panelStates[id];
        const body = document.getElementById(`body-${id}`);
        const chevron = document.getElementById(`chevron-${id}`);
        if (body) body.classList.toggle('collapsed', !isOpen);
        if (chevron) chevron.classList.toggle('rotated', !isOpen);
    });
}

// ======================== CBT SIMULATOR ========================
async function startTest(testId) {
    // Find test in loaded API tests or mock data
    const fullTest = (AppState.fullTests || []).find(t => t.id === testId) || MOCK_FULL_TESTS.find(t => t.id === testId);
    const subjectTest = SUBJECTS.flatMap(s => s.tests).find(t => t.id === testId);
    const test = fullTest || subjectTest;
    if (!test) return;

    // Fetch questions from API, fallback to sample questions
    let questions;
    if (testId === 4 && typeof VISION_TEST_QUESTIONS !== 'undefined') {
        questions = VISION_TEST_QUESTIONS;
    } else {
        try {
            const res = await apiFetch(`/api/tests/${testId}`);
            const data = await res.json();
            if (data.status === 'success' && data.questions && data.questions.length > 0) {
                questions = data.questions.map(q => ({
                    ...q,
                    correct: q.correct_option || q.correct,
                    explanation: q.rationale || q.explanation
                }));
            } else {
                questions = generateSampleQuestions(test.title, Math.min(test.questions, 20)); // Cap to 20 for demo
            }
        } catch (e) {
            console.error('Failed to load real test questions, using demo', e);
            questions = generateSampleQuestions(test.title, Math.min(test.questions, 20));
        }
    }

    AppState.cbtTest = { ...test, questions };
    AppState.cbtState = questions.map(() => ({ status: 'unseen', selected: null }));
    AppState.cbtCurrentQ = 0;
    AppState.cbtStartTime = Date.now();

    // Persist questions to localStorage so retry/history/PDF/remedial all work
    try {
        localStorage.setItem('upsc_test_questions_' + test.id, JSON.stringify(questions));
    } catch(e) { console.warn('Could not save questions to localStorage', e); }

    // Timer: 2h for full tests, proportional for subject tests
    const secs = questions.length >= 100 ? 7200 : Math.ceil(questions.length * 72);
    AppState.cbtTimeRemaining = secs;

    // Set up UI
    document.getElementById('cbt-exam-title').textContent = test.title;
    buildCBTPalette(questions.length);
    renderCBTQuestion(0);
    startCBTTimer();

    // Show overlay
    document.getElementById('exam-report-overlay').classList.add('hidden');
    document.getElementById('cbt-overlay').classList.remove('hidden');
}

function buildCBTPalette(total) {
    const grid = document.getElementById('cbt-palette');
    grid.innerHTML = '';
    for (let i = 0; i < total; i++) {
        const box = document.createElement('div');
        box.className = 'pb unseen';
        box.id = `pb-${i}`;
        box.textContent = i + 1;
        box.addEventListener('click', () => { saveCBTState(); goToCBTQuestion(i); });
        grid.appendChild(box);
    }
}

function renderCBTQuestion(idx) {
    const q = AppState.cbtTest.questions[idx];
    const state = AppState.cbtState[idx];

    document.getElementById('cbt-q-num').textContent = `Question ${idx + 1} / ${AppState.cbtTest.questions.length}`;
    document.getElementById('cbt-question-text').textContent = q.question;

    const optionsEl = document.getElementById('cbt-options');
    optionsEl.innerHTML = '';

    Object.entries(q.options).forEach(([key, val]) => {
        const div = document.createElement('div');
        div.className = 'cbt-option' + (state.selected === key ? ' selected' : '');
        div.innerHTML = `<span class="option-label">${key.toUpperCase()}</span><span>${val}</span>`;
        div.addEventListener('click', () => {
            optionsEl.querySelectorAll('.cbt-option').forEach(o => o.classList.remove('selected'));
            div.classList.add('selected');
            AppState.cbtState[idx].selected = key;
        });
        optionsEl.appendChild(div);
    });

    if (state.status === 'unseen') {
        state.status = 'not-answered';
        updatePaletteBox(idx);
    }

    // Highlight current palette box
    document.querySelectorAll('.pb').forEach(b => b.style.outline = '');
    const pb = document.getElementById(`pb-${idx}`);
    if (pb) pb.style.outline = '2px solid var(--primary-light)';
}

function saveCBTState() {
    const idx = AppState.cbtCurrentQ;
    const state = AppState.cbtState[idx];
    const selected = AppState.cbtTest.questions[idx].options;
    const selectedEl = document.querySelector('#cbt-options .cbt-option.selected');

    if (selectedEl) {
        const key = Object.keys(selected).find((k, i) => i === Array.from(document.querySelectorAll('#cbt-options .cbt-option')).indexOf(selectedEl));
        if (state.selected) {
            // Use stored value
        }
        if (state.status !== 'marked' && state.status !== 'marked-answered') state.status = 'answered';
        else if (state.status === 'marked') state.status = 'marked-answered';
    } else {
        state.selected = null;
        if (state.status === 'answered' || state.status === 'marked-answered') state.status = 'not-answered';
    }
    updatePaletteBox(idx);
}

function updatePaletteBox(idx) {
    const pb = document.getElementById(`pb-${idx}`);
    if (pb) pb.className = `pb ${AppState.cbtState[idx].status}`;
}

function goToCBTQuestion(idx) {
    AppState.cbtCurrentQ = idx;
    renderCBTQuestion(idx);
}

function clearCBTResponse() {
    const idx = AppState.cbtCurrentQ;
    document.querySelectorAll('#cbt-options .cbt-option').forEach(o => o.classList.remove('selected'));
    AppState.cbtState[idx].selected = null;
    AppState.cbtState[idx].status = 'not-answered';
    updatePaletteBox(idx);
}

function markAndNext() {
    const idx = AppState.cbtCurrentQ;
    const state = AppState.cbtState[idx];
    state.status = state.selected ? 'marked-answered' : 'marked';
    updatePaletteBox(idx);
    if (idx < AppState.cbtTest.questions.length - 1) goToCBTQuestion(idx + 1);
}

function saveAndNext() {
    const idx = AppState.cbtCurrentQ;
    const state = AppState.cbtState[idx];
    if (state.selected && state.status !== 'marked' && state.status !== 'marked-answered') {
        state.status = 'answered';
    } else if (!state.selected) {
        state.status = 'not-answered';
    }
    updatePaletteBox(idx);
    if (idx < AppState.cbtTest.questions.length - 1) goToCBTQuestion(idx + 1);
}

function confirmSubmitExam() {
    if (confirm(`You have attempted ${AppState.cbtState.filter(s => s.selected).length} of ${AppState.cbtTest.questions.length} questions. Submit exam?`)) {
        submitExam();
    }
}

function confirmAbortExam() {
    if (confirm('Are you sure you want to abort the exam? Your progress will be lost.')) {
        clearInterval(AppState.cbtTimerInterval);
        document.getElementById('cbt-overlay').classList.add('hidden');
    }
}

function submitExam() {
    clearInterval(AppState.cbtTimerInterval);
    const questions = AppState.cbtTest.questions;
    const state = AppState.cbtState;
    const timeTaken = Math.floor((Date.now() - AppState.cbtStartTime) / 1000);

    let correct = 0, wrong = 0, skipped = 0;
    const subjStats = {};
    const wrongQIndices = [];
    const unattemptedIndices = [];

    questions.forEach((q, i) => {
        const subj = q.subject || inferSubject(q.question);
        if (!subjStats[subj]) subjStats[subj] = { correct: 0, total: 0 };
        subjStats[subj].total++;

        if (state[i].selected === null) {
            skipped++;
            unattemptedIndices.push(i);
        } else if (state[i].selected === q.correct) {
            correct++;
            subjStats[subj].correct++;
        } else {
            wrong++;
            wrongQIndices.push(i);
        }
    });

    const total = questions.length;
    const marks = ((correct * 2) - (wrong * 0.66)).toFixed(2);
    let pct = Math.round((marks / (total * 2)) * 100);
    if (pct < 0) pct = 0;
    const minsElapsed = Math.floor(timeTaken / 60);
    const secsElapsed = timeTaken % 60;
    const timeStr = `${minsElapsed}m ${secsElapsed}s`;

    const testRef = MOCK_FULL_TESTS.find(t => t.id === AppState.cbtTest.id) || SUBJECTS.flatMap(s => s.tests).find(t => t.id === AppState.cbtTest.id);
    if (testRef) {
        testRef.status = 'attempted';
        testRef.score = pct;
        renderTestSeries();
    }

    // Save wrong/unattempted for retry
    const reviewData = {
        wrongIndices: wrongQIndices,
        unattemptedIndices: unattemptedIndices,
        tags: {}, // question index -> 'doubt'|'guess'|'revise'
    };
    localStorage.setItem('upsc_review_' + AppState.cbtTest.id, JSON.stringify(reviewData));

    // Track attempted question count per date for streak calendar
    const today = new Date().toISOString().split('T')[0];
    let dailyStats = JSON.parse(localStorage.getItem('upsc_daily_stats') || '{}');
    const attempted = correct + wrong; // questions actually ticked (not skipped)
    dailyStats[today] = (dailyStats[today] || 0) + attempted;
    localStorage.setItem('upsc_daily_stats', JSON.stringify(dailyStats));

    const attempt = {
        test: AppState.cbtTest.title, date: new Date().toISOString().split('T')[0],
        score: pct, rank: Math.floor(Math.random() * 500) + 50,
        subject: 'General Studies', time: timeStr, id: AppState.cbtTest.id
    };
    AppState.testAttempts.unshift(attempt);
    localStorage.setItem('upsc_prototypeAttempts_v1', JSON.stringify(AppState.testAttempts));
    localStorage.setItem('upsc_test_state_' + AppState.cbtTest.id, JSON.stringify(state));
    localStorage.setItem('upsc_test_questions_' + AppState.cbtTest.id, JSON.stringify(questions));
    MOCK_HISTORY.unshift(attempt);

    // Update streak
    updateStreak();
    // Evaluate badges
    setTimeout(() => evaluateAndAwardBadges(pct, correct, total, AppState.testAttempts.length), 800);

    // Call API here to persist results
    if (AppState.user) {
        apiFetch('/api/tests/submit', {
            method: 'POST',
            body: JSON.stringify({
                topic_tested: attempt.test,
                score: pct,
                total_questions: total,
                time_taken_secs: timeTaken,
                subject_stats: subjStats
            })
        }).then(() => {
            initAnalytics();
        }).catch(err => console.error('Failed to sync test results:', err));
    }

    // Render report
    renderExamReport(correct, wrong, skipped, total, pct, timeStr, subjStats, questions, state, wrongQIndices, unattemptedIndices, marks);
    document.getElementById('cbt-overlay').classList.add('hidden');
    document.getElementById('exam-report-overlay').classList.remove('hidden');
}

function renderExamReport(correct, wrong, skipped, total, pct, timeStr, subjStats, questions, state, wrongQIndices = [], unattemptedIndices = [], marks = 0) {
    document.getElementById('report-score-text').textContent = `${marks} / ${total * 2}`;
    document.getElementById('report-pct-text').textContent = `${pct}%`;
    document.getElementById('rm-correct').textContent = correct;
    document.getElementById('rm-wrong').textContent = wrong;
    document.getElementById('rm-skip').textContent = skipped;
    document.getElementById('rm-time').textContent = timeStr;
    document.getElementById('report-exam-title').textContent = AppState.cbtTest.title;

    // Animate score ring
    const circumference = 314;
    const offset = circumference - (pct / 100) * circumference;
    const fill = document.getElementById('report-ring-fill');
    fill.style.stroke = pct >= 70 ? 'var(--teal)' : pct >= 50 ? 'var(--amber-light)' : 'var(--red)';
    setTimeout(() => { fill.style.strokeDashoffset = offset; }, 100);

    // Retry buttons — inject into report actions
    const actionsEl = document.querySelector('.report-actions');
    if (actionsEl) {
        actionsEl.innerHTML = `
            <button class="btn-amber" onclick="reattemptExam()">↻ Reattempt Full</button>
            ${wrongQIndices.length > 0 ? `<button class="btn-retry-wrong" onclick="startRetryTest('wrong')">⚡ Retry Wrong (${wrongQIndices.length})</button>` : ''}
            ${(wrongQIndices.length + unattemptedIndices.length) > 0 ? `<button class="btn-retry-skip" onclick="startRetryTest('both')">📝 Attempt Weak (${wrongQIndices.length + unattemptedIndices.length})</button>` : ''}
            <button class="btn-ghost" onclick="exitReport()">← Back to Hub</button>
        `;
    }

    // Subject bars
    const barsEl = document.getElementById('report-subject-bars');
    barsEl.innerHTML = '';
    Object.entries(subjStats).forEach(([subj, stats]) => {
        const p = Math.round((stats.correct / stats.total) * 100);
        const cls = p >= 70 ? 'green' : p >= 50 ? 'amber' : 'red';
        barsEl.innerHTML += `
            <div class="subject-report-bar">
                <div class="srb-header">
                    <span>${subj}</span>
                    <span class="${cls}">${stats.correct}/${stats.total} (${p}%)</span>
                </div>
                <div class="progress-track"><div class="progress-fill ${cls}" style="width:${p}%"></div></div>
            </div>`;
    });

    // Solutions with question tagging
    const solList = document.getElementById('report-solutions-list');
    solList.innerHTML = '';
    const reviewKey = 'upsc_review_' + AppState.cbtTest.id;
    let reviewData = JSON.parse(localStorage.getItem(reviewKey) || '{"tags":{}}');

    questions.forEach((q, i) => {
        const sel = state[i].selected;
        const isCor = sel === q.correct;
        const isSkip = sel === null;

        let tagHtml = '';
        if (isCor) tagHtml = '<span style="color:var(--teal);font-weight:700;">✓ Correct</span>';
        else if (isSkip) tagHtml = '<span style="color:var(--text-muted);">— Skipped</span>';
        else tagHtml = '<span style="color:var(--red);font-weight:700;">✗ Wrong</span>';

        const currentTag = reviewData.tags ? reviewData.tags[i] : null;
        const testIdSafe = AppState.cbtTest.id;
        const tagButtons = `
            <div class="q-tag-row">
                <span class="q-tag-label">Tag this question:</span>
                <button class="q-tag-btn ${currentTag==='doubt'?'active-doubt':''}" onclick="tagQuestion(${i},'doubt','${testIdSafe}',this.parentElement)" title="I didn't understand this">🔴 Doubt</button>
                <button class="q-tag-btn ${currentTag==='guess'?'active-guess':''}" onclick="tagQuestion(${i},'guess','${testIdSafe}',this.parentElement)" title="I guessed correctly">🟡 Guess</button>
                <button class="q-tag-btn ${currentTag==='revise'?'active-revise':''}" onclick="tagQuestion(${i},'revise','${testIdSafe}',this.parentElement)" title="Needs revision">🔵 Revise Later</button>
            </div>`;

        const acc = document.createElement('div');
        acc.className = 'sol-accordion';
        acc.innerHTML = `
            <div class="sol-header" onclick="this.nextElementSibling.classList.toggle('open')">
                <span>Q${i + 1}. ${q.question.substring(0, 65)}...</span>
                ${tagHtml}
            </div>
            <div class="sol-body">
                <p style="line-height:1.7;margin-bottom:1rem;">${q.question}</p>
                <div class="sol-answer-row">
                    <span>Your answer: <strong style="color:${isCor ? 'var(--teal)' : isSkip ? 'var(--text-muted)' : 'var(--red)'};"> ${sel ? sel.toUpperCase() : 'None'}</strong></span>
                    <span>Correct: <strong style="color:var(--teal);">${q.correct.toUpperCase()}</strong></span>
                </div>
                <div class="sol-rationale">
                    <div class="sol-rationale-label">✦ AI Explanation</div>
                    ${q.explanation}
                    ${q.mains_hint ? `<br><br><div style="background:var(--bg);padding:10px;border-left:3px solid var(--primary-light);border-radius:4px;"><strong style="color:var(--primary-light);">Mains Connection:</strong> ${q.mains_hint}</div>` : ''}
                </div>
                ${tagButtons}
            </div>`;
        solList.appendChild(acc);
    });
}

function reattemptExam() {
    document.getElementById('exam-report-overlay').classList.add('hidden');
    startTest(AppState.cbtTest.id);
}

function startRetryTest(mode) {
    // mode: 'wrong' = only wrong, 'both' = wrong + unattempted
    const reviewData = JSON.parse(localStorage.getItem('upsc_review_' + AppState.cbtTest.id) || '{}');
    const wrongIdx = reviewData.wrongIndices || [];
    const skipIdx = reviewData.unattemptedIndices || [];
    
    let indices = mode === 'wrong' ? wrongIdx : [...new Set([...wrongIdx, ...skipIdx])];
    if (indices.length === 0) { alert('No questions to retry!'); return; }

    const allQuestions = AppState.cbtTest.questions;
    const retryQuestions = indices.map(i => allQuestions[i]);

    const retryTest = {
        ...AppState.cbtTest,
        title: AppState.cbtTest.title + (mode === 'wrong' ? ' — Wrong Questions Retry' : ' — Weak Questions Retry'),
        questions: retryQuestions,
        isRetry: true,
    };

    AppState.cbtTest = retryTest;
    AppState.cbtState = retryQuestions.map(() => ({ status: 'unseen', selected: null }));
    AppState.cbtCurrentQ = 0;
    AppState.cbtStartTime = Date.now();

    const secs = Math.ceil(retryQuestions.length * 72);
    AppState.cbtTimeRemaining = secs;

    document.getElementById('cbt-exam-title').textContent = retryTest.title;
    buildCBTPalette(retryQuestions.length);
    renderCBTQuestion(0);
    startCBTTimer();

    document.getElementById('exam-report-overlay').classList.add('hidden');
    document.getElementById('cbt-overlay').classList.remove('hidden');
}

// Called from View modal — loads full question list from API then starts retry
async function startRetryFromView(testId, mode) {
    // Close the review modal first
    document.getElementById('review-modal').classList.add('hidden');

    const reviewData = JSON.parse(localStorage.getItem('upsc_review_' + testId) || '{}');
    const wrongIdx = reviewData.wrongIndices || [];
    const skipIdx = reviewData.unattemptedIndices || [];

    let indices = mode === 'wrong' ? wrongIdx : [...new Set([...wrongIdx, ...skipIdx])];
    if (indices.length === 0) { alert('No questions to retry!'); return; }

    try {
        let allQuestions = [];
        let baseTitle = 'Prototype Paper';

        if (String(testId).startsWith('ai_')) {
            const aiTests = JSON.parse(localStorage.getItem('upsc_ai_tests') || '{}');
            allQuestions = aiTests[testId] || [];
            baseTitle = 'AI Custom Test';
        } else {
            const storedQ = localStorage.getItem('upsc_test_questions_' + testId);
            if (storedQ) {
                allQuestions = JSON.parse(storedQ);
            } else {
                const res = await apiFetch(`/api/tests/${testId}`);
                const data = await res.json();
                allQuestions = data.questions || [];
            }
            const baseTest = MOCK_FULL_TESTS.find(t => t.id === testId);
            if (baseTest) baseTitle = baseTest.title;
        }

        const retryQuestions = indices.map(i => allQuestions[i]).filter(Boolean);

        if (retryQuestions.length === 0) { alert('Could not load questions for retry.'); return; }

        const retryTest = {
            id: testId + '_retry',
            title: baseTitle + (mode === 'wrong' ? ' — Wrong Questions Retry' : ' — Weak Questions Retry'),
            questions: retryQuestions,
            isRetry: true,
        };

        AppState.cbtTest = retryTest;
        AppState.cbtState = retryQuestions.map(() => ({ status: 'unseen', selected: null }));
        AppState.cbtCurrentQ = 0;
        AppState.cbtStartTime = Date.now();

        const secs = Math.ceil(retryQuestions.length * 72);
        AppState.cbtTimeRemaining = secs;

        document.getElementById('cbt-exam-title').textContent = retryTest.title;
        buildCBTPalette(retryQuestions.length);
        renderCBTQuestion(0);
        startCBTTimer();

        document.getElementById('exam-report-overlay').classList.add('hidden');
        document.getElementById('cbt-overlay').classList.remove('hidden');
    } catch(e) {
        console.error('Failed to load test for retry:', e);
        alert('Failed to load questions. Please try again.');
    }
}

function tagQuestion(qIndex, tag, testId, containerEl) {
    const key = 'upsc_review_' + testId;
    const reviewData = JSON.parse(localStorage.getItem(key) || '{"tags":{}}');
    if (!reviewData.tags) reviewData.tags = {};
    
    // Toggle off if same tag
    if (reviewData.tags[qIndex] === tag) {
        delete reviewData.tags[qIndex];
    } else {
        reviewData.tags[qIndex] = tag;
    }
    localStorage.setItem(key, JSON.stringify(reviewData));
    
    // Update button UI
    const buttons = containerEl.querySelectorAll('.q-tag-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active-doubt', 'active-guess', 'active-revise');
    });
    if (reviewData.tags[qIndex]) {
        const activeBtn = containerEl.querySelector(`[onclick*="'${tag}'"]`);
        if (activeBtn) activeBtn.classList.add('active-' + tag);
    }
}

function exitReport() {
    document.getElementById('exam-report-overlay').classList.add('hidden');
}

function startCBTTimer() {
    clearInterval(AppState.cbtTimerInterval);
    const timerEl = document.getElementById('cbt-timer');

    AppState.cbtTimerInterval = setInterval(() => {
        AppState.cbtTimeRemaining--;
        const h = Math.floor(AppState.cbtTimeRemaining / 3600);
        const m = Math.floor((AppState.cbtTimeRemaining % 3600) / 60);
        const s = AppState.cbtTimeRemaining % 60;
        timerEl.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

        if (AppState.cbtTimeRemaining <= 300) timerEl.className = 'cbt-timer danger';
        else if (AppState.cbtTimeRemaining <= 900) timerEl.className = 'cbt-timer warning';

        if (AppState.cbtTimeRemaining <= 0) {
            clearInterval(AppState.cbtTimerInterval);
            alert('Time up! Auto-submitting exam.');
            submitExam();
        }
    }, 1000);
}

function inferSubject(text) {
    const kw = {
        'History': ['history', 'revolt', 'dynasty', 'british', 'colonial', 'freedom', 'gandhi', 'empire', 'ancient', 'movement'],
        'Art and culture': ['art', 'culture', 'dance', 'music', 'temple', 'architecture', 'heritage'],
        'Geography': ['geography', 'river', 'monsoon', 'plateau', 'mountain', 'soil', 'cyclone', 'strait', 'earth', 'climate', 'ocean'],
        'Polity': ['polity', 'article', 'amendment', 'parliament', 'constitution', 'rights', 'court', 'lok sabha', 'act'],
        'International relations': ['international', 'treaty', 'bilateral', 'united nations', 'wto', 'who', 'summit'],
        'Economics': ['economy', 'economics', 'gdp', 'rbi', 'inflation', 'bank', 'trade', 'budget', 'fiscal'],
        'Science and technology': ['science', 'tech', 'space', 'isro', 'satellite', 'vaccine', 'quantum', 'dna'],
        'Environment, agriculture and biodiversity': ['environment', 'agriculture', 'biodiversity', 'iucn', 'climate change', 'carbon', 'wetland', 'species', 'forest', 'crop']
    };
    const lower = text.toLowerCase();
    for (const [subj, words] of Object.entries(kw)) {
        if (words.some(w => lower.includes(w))) return subj;
    }
    return 'Geography'; // Defaulting to Geography based on prototype
}

// ======================== ANALYTICS ========================
async function initAnalytics() {
    try {
        const res = await apiFetch('/api/analytics');
        const data = await res.json();
        
        if (data.status === 'success') {
            MOCK_HISTORY.length = 0;
            data.sessions.forEach(s => {
                const dateSplit = s.created_at.split('T')[0];
                const mins = Math.floor(s.time_taken_secs / 60);
                const secs = s.time_taken_secs % 60;
                MOCK_HISTORY.push({
                    test: s.topic_tested, date: dateSplit,
                    score: s.score, rank: '-', subject: s.subject || 'General Studies',
                    time: `${mins}m ${secs}s`, id: s.id
                });
            });

            // ── BUG FIX: Populate per-subject score trends for pill buttons ──
            const SUBJECT_KEYS = {
                'Polity': 'polity',
                'History': 'history',
                'Geography': 'geo',
                'Environment': 'env',
                'Economy': 'economy',
                'Science': 'science',
                'Current Affairs': 'current'
            };
            const subjectScoreBuckets = {};
            const subjectScoreHistory = {}; // for sparklines: { subject: [score, score, ...] }
            data.sessions.forEach(s => {
                if (s.topic_tested && s.topic_tested.includes('Remedial')) return;
                const sub = s.subject || s.topic_tested || '';
                const key = Object.keys(SUBJECT_KEYS).find(k => sub.toLowerCase().includes(k.toLowerCase()));
                if (key) {
                    const bucket = SUBJECT_KEYS[key];
                    if (!subjectScoreBuckets[bucket]) subjectScoreBuckets[bucket] = [];
                    subjectScoreBuckets[bucket].push(s.score);
                }
                // Per-subject history for sparklines (keyed by taxonomy category)
                const cat = s.subject || s.topic_tested;
                if (!subjectScoreHistory[cat]) subjectScoreHistory[cat] = [];
                subjectScoreHistory[cat].push(s.score);
            });
            // Store in global for chart access
            window._subjectScoreHistory = subjectScoreHistory;

            SCORE_TREND.all = [...data.sessions].filter(s => !(s.topic_tested && s.topic_tested.includes('Remedial'))).reverse().map(s => s.score);
            Object.keys(SUBJECT_KEYS).forEach(k => {
                const bucket = SUBJECT_KEYS[k];
                SCORE_TREND[bucket] = (subjectScoreBuckets[bucket] || []).slice().reverse();
            });

            Object.keys(SUBJECT_ACCURACY).forEach(k => delete SUBJECT_ACCURACY[k]);
            SUBJECTS.forEach(s => { SUBJECT_ACCURACY[s.name] = 0; });
            data.taxonomy.forEach(t => {
                if (t.category !== 'General Geography') {
                    SUBJECT_ACCURACY[t.category] = Math.round(t.mastery_percentage);
                }
            });

            const totalTests = data.sessions.length;
            const scores = data.sessions.map(s => s.score);
            const avgScore  = totalTests ? Math.round(scores.reduce((a,c)=>a+c,0)/totalTests) : 0;
            const bestScore = totalTests ? Math.max(...scores) : null;
            const worstScore= totalTests ? Math.min(...scores) : null;

            const sortedTax = [...data.taxonomy].filter(t => t.category !== 'General Geography').sort((a,b)=>a.mastery_percentage - b.mastery_percentage);
            const weakSubj  = sortedTax.length > 0 ? sortedTax[0] : null;

            // Populate stat cards (all guarded)
            const elRank = document.getElementById('stat-rank');
            if (elRank) elRank.textContent = '#--';
            const elAvg  = document.getElementById('stat-avg');
            if (elAvg)  elAvg.textContent = totalTests ? `${avgScore}%` : '--';
            const elTotal= document.getElementById('stat-total');
            if (elTotal) elTotal.textContent = totalTests;
            const elBest = document.getElementById('stat-best');
            if (elBest)  elBest.textContent = bestScore !== null ? `${bestScore}%` : '--';
            const elWorst= document.getElementById('stat-worst');
            if (elWorst) elWorst.textContent = worstScore !== null ? `${worstScore}%` : '--';
            const elWeak = document.getElementById('stat-weak');
            if (elWeak)  elWeak.textContent = weakSubj ? weakSubj.category : 'N/A';

            // ── Consistency Ring ──
            const activeDates = JSON.parse(localStorage.getItem('upsc_active_dates') || '[]');
            const now = new Date(); now.setHours(0,0,0,0);
            const thirtyDaysAgo = new Date(now); thirtyDaysAgo.setDate(now.getDate() - 29);
            const studiedDays = activeDates.filter(d => {
                const dt = new Date(d); dt.setHours(0,0,0,0);
                return dt >= thirtyDaysAgo && dt <= now;
            }).length;
            const consistencyPct = Math.round((studiedDays / 30) * 100);
            const ringEl  = document.getElementById('consistency-ring-fill');
            const pctEl   = document.getElementById('consistency-pct');
            const subEl   = document.getElementById('consistency-sub');
            if (ringEl) {
                const circumference = 138.2;
                const offset = circumference - (circumference * consistencyPct / 100);
                setTimeout(() => { ringEl.style.strokeDashoffset = offset; }, 200);
                ringEl.style.stroke = consistencyPct >= 70 ? 'var(--teal)' : consistencyPct >= 40 ? '#eab308' : 'var(--red)';
            }
            if (pctEl) { pctEl.textContent = `${consistencyPct}%`; pctEl.style.color = consistencyPct >= 70 ? 'var(--teal)' : consistencyPct >= 40 ? '#eab308' : 'var(--red)'; }
            if (subEl)  subEl.textContent = `${studiedDays}/30 days`;

            const breakdownEl = document.getElementById('stat-test-breakdown');
            if (breakdownEl) {
                const bCount = {};
                data.sessions.forEach(s => { bCount[s.topic_tested] = (bCount[s.topic_tested] || 0) + 1; });
                breakdownEl.innerHTML = Object.entries(bCount).map(([k,v]) => `<div style="padding:2px 0;">${k}: <strong>${v}</strong></div>`).join('');
            }

            const dynamicInsightsEl = document.getElementById('dynamic-ai-insights');
            if (dynamicInsightsEl) {
                if (data.sessions.length > 0) {
                    const topWeakness = weakSubj ? weakSubj.category : 'specific areas';
                    const timeTakenAvg = Math.round(data.sessions.reduce((a,c)=>a+c.time_taken_secs,0)/data.sessions.length / 60);
                    const streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"count":0}');
                    const strongSubj = sortedTax.length > 1 ? sortedTax[sortedTax.length-1].category : '';
                    const strongAcc  = sortedTax.length > 1 ? Math.round(sortedTax[sortedTax.length-1].mastery_percentage) : 0;
                    dynamicInsightsEl.innerHTML = `<strong>Study Pattern Analysis:</strong> Across your ${totalTests} test attempts, you maintain a ${streakData.count} day streak. You spend around ${timeTakenAvg} minutes per test on average. Consistency score: <strong>${consistencyPct}%</strong> (${studiedDays}/30 days studied).<br><br>
                    <strong>Subject Wise Basic Analysis:</strong><br>
                    • <strong>${topWeakness}</strong> is your weakest area. Focus on revising fundamental concepts to improve your overall score.<br>
                    ${strongSubj ? `• Your strongest area appears to be <strong>${strongSubj}</strong> with <strong>${strongAcc}%</strong> accuracy.<br>` : ''}
                    <br>Review the automatically generated tasks below or add your own custom goals to maintain momentum.`;
                } else {
                    dynamicInsightsEl.innerHTML = `Attempt your first mock test to unlock personalized performance diagnosis and peer benchmarking insights!`;
                }
            }

            const todoListEl = document.getElementById('ai-todo-list');
            if (todoListEl) {
                let currentTodos = JSON.parse(localStorage.getItem('upsc_todos') || 'null');
                if (!currentTodos || currentTodos.length === 0) {
                    currentTodos = sortedTax.slice(0, 3).map(t => ({
                        topic: `Revise: ${t.category}`, notes: '', subtopics: [], collapsed: false
                    }));
                    if (currentTodos.length === 0) currentTodos = [{ topic: "Complete 'Prototype Paper' mock test", notes: '', subtopics: [], collapsed: false }];
                    localStorage.setItem('upsc_todos', JSON.stringify(currentTodos));
                }
                renderTodos(currentTodos);
            }

            // ── Tier Engine ──
            const tierData = computeTierPoints();
            renderTierCard(tierData);
        }
    } catch(e) { console.error('Failed analytics fetch', e); }

    initCharts();
    if (typeof renderHistoryTable === 'function') renderHistoryTable();
    updateReviewZones();
}

function initCharts() {
    if (AppState.subjectChart) { AppState.subjectChart.destroy(); AppState.subjectChart = null; }
    if (AppState.trendChart) { AppState.trendChart.destroy(); AppState.trendChart = null; }
    if(Object.keys(SUBJECT_ACCURACY).length > 0) initSubjectAccuracyChart();
    if(SCORE_TREND.all.length > 0) initScoreTrendChart();
}

function getChartTextColor() {
    return getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#8892b0';
}

function getGridColor() {
    return getComputedStyle(document.documentElement).getPropertyValue('--border').trim() || 'rgba(255,255,255,0.08)';
}

function initSubjectAccuracyChart() {
    if (AppState.subjectChart) return;
    const ctx = document.getElementById('subject-accuracy-chart').getContext('2d');
    const labels = Object.keys(SUBJECT_ACCURACY);
    const values = Object.values(SUBJECT_ACCURACY);
    const colors = values.map(v => v >= 60 ? 'rgba(29,158,117,0.8)' : v >= 45 ? 'rgba(186,117,23,0.8)' : 'rgba(226,75,74,0.8)');
    const borderColors = values.map(v => v >= 60 ? '#1D9E75' : v >= 45 ? '#BA7517' : '#E24B4A');
    const history = window._subjectScoreHistory || {};

    AppState.subjectChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{ data: values, backgroundColor: colors, borderColor: borderColors, borderWidth: 2, borderRadius: 6, borderSkipped: false }]
        },
        options: {
            indexAxis: 'y',
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const subj = ctx.label;
                            const acc = ctx.parsed.x;
                            const hist = history[subj] || [];
                            const sparkStr = hist.length > 1
                                ? '  Trend: ' + hist.slice(-5).map(s => s + '%').join(' → ')
                                : '';
                            return ` ${acc}% accuracy${sparkStr}`;
                        },
                        afterLabel: ctx => {
                            const subj = ctx.label;
                            const hist = history[subj] || [];
                            if (hist.length < 2) return '';
                            const last = hist[hist.length - 1];
                            const prev = hist[hist.length - 2];
                            const delta = last - prev;
                            return delta > 0 ? ` ↑ +${delta}% since last test` : delta < 0 ? ` ↓ ${delta}% since last test` : ' → No change';
                        }
                    }
                }
            },
            scales: {
                x: { min: 0, max: 100, grid: { color: getGridColor() }, ticks: { color: getChartTextColor(), callback: v => v + '%' } },
                y: { grid: { display: false }, ticks: { color: getChartTextColor(), font: { size: 11 } } }
            },
            onClick: (evt, elements) => {
                if (elements.length > 0) {
                    const idx = elements[0].index;
                    openDrillDown(labels[idx], values[idx]);
                }
            },
            onHover: (evt, elements) => {
                evt.native.target.style.cursor = elements.length ? 'pointer' : 'default';
            }
        }
    });
}

function initScoreTrendChart() {
    if (AppState.trendChart) return;
    const ctx = document.getElementById('score-trend-chart').getContext('2d');
    const data = SCORE_TREND.all;
    const labels = data.map((_, i) => `Test ${i + 1}`);

    // Moving average
    const movAvg = data.map((_, i, arr) => {
        const window = arr.slice(Math.max(0, i - 2), i + 1);
        return Math.round(window.reduce((a, b) => a + b, 0) / window.length);
    });

    AppState.trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Score %',
                    data,
                    borderColor: '#534AB7',
                    backgroundColor: 'rgba(83,74,183,0.1)',
                    tension: 0.4, fill: true, pointRadius: 4,
                    pointBackgroundColor: '#534AB7', pointBorderColor: '#8b82e0',
                },
                {
                    label: 'Moving Avg',
                    data: movAvg,
                    borderColor: '#1D9E75', borderDash: [6, 3],
                    tension: 0.4, fill: false, pointRadius: 0,
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: getChartTextColor(), font: { size: 11 } } },
                tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y}%` } }
            },
            scales: {
                x: { grid: { color: getGridColor() }, ticks: { color: getChartTextColor(), font: { size: 10 } } },
                y: { min: 0, max: 100, grid: { color: getGridColor() }, ticks: { color: getChartTextColor(), callback: v => v + '%' } }
            }
        }
    });
}

function switchTrend(key) {
    if (typeof key === 'object' && key !== null && key.value) {
        key = key.value; // Handle if element itself was passed
    } else if (arguments.length > 1 && typeof arguments[1] === 'string') {
        key = arguments[1]; // Handle old pill-btn signature
    }
    
    // Clear old pill active states if any remain
    document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
    
    const data = SCORE_TREND[key] || SCORE_TREND.all;
    const movAvg = data.map((_, i, arr) => {
        const w = arr.slice(Math.max(0, i - 2), i + 1);
        return Math.round(w.reduce((a, b) => a + b, 0) / w.length);
    });

    if (AppState.trendChart) {
        AppState.trendChart.data.datasets[0].data = data;
        AppState.trendChart.data.datasets[1].data = movAvg;
        AppState.trendChart.update();
    }
}

function getWrongQuestionsForSubject(subject) {
    let wrongQs = [];
    AppState.testAttempts.forEach(attempt => {
        let qs    = JSON.parse(localStorage.getItem('upsc_test_questions_' + attempt.id) || '[]');
        let state = JSON.parse(localStorage.getItem('upsc_test_state_'     + attempt.id) || '[]');
        qs.forEach((q, i) => {
            // BUG FIX: use stricter subject match — check q.subject field first, only fall back to question text as last resort
            const qSubject = (q.subject || '').toLowerCase();
            const targetSub = subject.toLowerCase();
            const matches = qSubject === targetSub || qSubject.includes(targetSub);
            if (matches) {
                const answered = state[i] ? state[i].selected : null;
                if (answered !== q.correct_option && answered !== q.correct) {
                    wrongQs.push({
                        question: q.question,
                        correct: q.correct_option || q.correct,
                        userAnswer: answered,
                        options: q.options || {},
                        rationale: q.rationale || q.explanation || ''
                    });
                }
            }
        });
    });
    return wrongQs.slice(0, 5);
}

async function fetchDiagnosis(subject, accuracy) {
    const wrongQs = getWrongQuestionsForSubject(subject);
    const wrongQStrings = wrongQs.map(q => typeof q === 'string' ? q : q.question);
    // BUG FIX: Add timeout so the panel doesn't show "Generating..." indefinitely
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
        const res = await apiFetch('/api/analytics/diagnosis', {
            method: 'POST',
            body: JSON.stringify({ subject, accuracy, wrong_questions: wrongQStrings }),
            signal: controller.signal
        });
        clearTimeout(timeout);
        const data = await res.json();
        const el = document.getElementById('ai-diagnosis-content');
        if (el) {
            // Strip residual markdown bolding
            const clean = (data.diagnosis || 'Focus on NCERTs for this subject.').replace(/\*\*/g, '');
            let diagHtml = `<strong>Sub-topic Analysis for ${subject}:</strong><br>` + clean.replace(/\n/g, '<br>');
            diagHtml += `<div style="margin-top:15px; display:flex; gap:10px;">
                <button onclick="window.addDiagnosisToPlan('${subject}')" class="btn-primary-sm">+ Add to Study Plan</button>
                <button onclick="window.reviewMistakes('${subject}')" class="btn-retry-wrong" style="padding:4px 10px; font-size:0.8rem;">Review Mistakes</button>
            </div>`;
            el.innerHTML = diagHtml;
        }
    } catch(e) {
        clearTimeout(timeout);
        const el = document.getElementById('ai-diagnosis-content');
        if (el) el.innerHTML = e.name === 'AbortError'
            ? '<span style="color:var(--amber-light);">⏱ AI is taking too long. Please try again in a moment.</span>'
            : '<span style="color:var(--red);">⚠ Unable to generate insights right now. Check your connection.</span>';
    }
}

function openDrillDown(subject, accuracy) {
    const panel = document.getElementById('drill-down-panel');
    document.getElementById('drill-title').textContent = subject + ' Deep Dive';
    document.getElementById('drill-close').style.display = '';
    
    // Trigger async fetch
    fetchDiagnosis(subject, accuracy);


    const color = accuracy >= 60 ? 'var(--teal)' : accuracy >= 45 ? 'var(--amber-light)' : 'var(--red)';

    document.getElementById('drill-content').innerHTML = `
        <div style="margin-bottom:1rem;">
            <div class="srb-header" style="display:flex;justify-content:space-between;margin-bottom:0.5rem;">
                <span style="color:var(--text-muted);font-size:0.85rem;">Overall Accuracy</span>
                <span style="color:${color};font-weight:700;">${accuracy}%</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width:${accuracy}%;background:${color}"></div></div>
        </div>
        <div class="ai-badge" style="margin-bottom:1rem;">✦ Performance Diagnosis</div>
        <div id="ai-diagnosis-content" style="font-size:0.85rem;color:var(--text-muted);line-height:1.7;background:var(--ai-bg);border:1px solid var(--ai-border);border-radius:10px;padding:1rem;">
            Generating specific sub-topic insights... <span class="loading-dots"></span>
        </div>
        <div style="margin-top:1rem;font-size:0.82rem;color:var(--text-faint);">Click any bar in the chart to explore another subject.</div>
    `;
}

function closeDrillDown() {
    document.getElementById('drill-title').textContent = 'Select a Subject';
    document.getElementById('drill-close').style.display = 'none';
    document.getElementById('drill-content').innerHTML = `
        <div class="drill-placeholder">
            <span style="font-size:3rem;">📊</span>
            <p>Click any bar in the Subject-wise Accuracy chart to view your detailed performance for that subject.</p>
        </div>`;
}

// Attempt History Table
function initHistoryTable() {
    AppState.historyData = [...MOCK_HISTORY, ...AppState.testAttempts];
    AppState.historyFiltered = [...AppState.historyData];
    renderHistoryTable();
}

function renderHistoryTable() {
    const tbody = document.getElementById('history-tbody');
    const start = (AppState.historyPage - 1) * AppState.historyPageSize;
    const page = AppState.historyFiltered.slice(start, start + AppState.historyPageSize);

    const isPro = AppState.user && AppState.user.isPremium;
    const titlePdf = isPro ? 'Download PDF' : 'Download PDF 👑';
    const titleRemedial = isPro ? 'Auto-Remedial Mistakes Test' : 'Auto-Remedial Mistakes Test 👑';

    tbody.innerHTML = '';
    page.forEach(row => {
        const pct = row.score;
        const chipColor = pct >= 70 ? 'background:rgba(29,158,117,0.15);color:var(--teal);' :
            pct >= 50 ? 'background:rgba(186,117,23,0.15);color:var(--amber-light);' :
                'background:rgba(226,75,74,0.15);color:var(--red);';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-weight:600;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${row.test}">${row.test}</td>
            <td style="color:var(--text-muted);">${row.date}</td>
            <td><span class="score-chip" style="${chipColor}">${row.score}%</span></td>
            <td style="color:var(--text-muted);">#${row.rank}</td>
            <td><span class="badge-${row.subject === 'General Studies' ? 'new' : 'attempted'}" style="font-size:0.72rem;">${row.subject}</span></td>
            <td style="color:var(--text-muted);">${row.time}</td>
            <td style="display:flex; gap:8px;">
                <button class="btn-ghost-sm" onclick='openReviewModal(${JSON.stringify(row)})'>View</button>
                <button class="btn-ghost-sm" style="color:var(--gold); border-color:var(--gold); padding:4px 8px;" onclick="exportTestPDF('${row.id}')" title="${titlePdf}">📄</button>
                <button class="btn-ghost-sm" style="color:var(--red); border-color:rgba(226,75,74,0.3); padding:4px 8px;" onclick="startSingleRemedialTest('${row.id}', '${row.test.replace(/'/g, "\\'")}')" title="${titleRemedial}">🔄</button>
            </td>`;
        tbody.appendChild(tr);
    });

    // Pagination
    const totalPages = Math.ceil(AppState.historyFiltered.length / AppState.historyPageSize);
    const pagEl = document.getElementById('table-pagination');
    pagEl.innerHTML = '';
    for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn' + (i === AppState.historyPage ? ' active' : '');
        btn.textContent = i;
        btn.onclick = () => { AppState.historyPage = i; renderHistoryTable(); };
        pagEl.appendChild(btn);
    }
}

function filterHistory() {
    const q = document.getElementById('history-search').value.toLowerCase();
    AppState.historyFiltered = AppState.historyData.filter(r =>
        r.test.toLowerCase().includes(q) || r.subject.toLowerCase().includes(q)
    );
    AppState.historyPage = 1;
    renderHistoryTable();
}

function sortTable(key) {
    if (AppState.historySortKey === key) AppState.historySortDir *= -1;
    else { AppState.historySortKey = key; AppState.historySortDir = 1; }

    AppState.historyFiltered.sort((a, b) => {
        let va = a[key], vb = b[key];
        if (typeof va === 'string') return va.localeCompare(vb) * AppState.historySortDir;
        return (va - vb) * AppState.historySortDir;
    });
    renderHistoryTable();
}

async function openReviewModal(row, filterMode = 'all') {
    document.getElementById('modal-title').textContent = row.test + ' — Detailed Solutions';
    document.getElementById('review-modal-body').innerHTML = `<div style="text-align:center; padding: 2rem;">Loading detailed solutions...</div>`;
    document.getElementById('review-modal').classList.remove('hidden');

    try {
        let testId = row.id;
        let questions = [];

        if (String(testId).startsWith('ai_')) {
            const aiTests = JSON.parse(localStorage.getItem('upsc_ai_tests') || '{}');
            questions = aiTests[testId] || [];
        } else {
            if(row.id && MOCK_FULL_TESTS.find(t => t.id === row.id)) testId = row.id;
            const storedQ = localStorage.getItem('upsc_test_questions_' + testId);
            if (storedQ) {
                questions = JSON.parse(storedQ);
            } else {
                testId = 2; // Default to Prototype
                const res = await apiFetch(`/api/tests/${testId}`);
                const data = await res.json();
                questions = data.questions || [];
            }
        }

        // Load retry data for this test
        const retryData = JSON.parse(localStorage.getItem('upsc_review_' + testId) || '{}');
        const wrongIdx = retryData.wrongIndices || [];
        const skipIdx = retryData.unattemptedIndices || [];
        const totalWeak = wrongIdx.length + skipIdx.length;

        let html = `
            <div style="display:flex;gap:1.5rem;margin-bottom:1.5rem;flex-wrap:wrap;background:var(--card-bg);padding:1rem;border-radius:8px; align-items:center;">
                <div class="meta-stat"><span class="meta-label">Date</span><span class="meta-val" style="font-size:1rem;color:var(--text);">${row.date}</span></div>
                <div class="meta-stat"><span class="meta-label">Score</span><span class="meta-val" style="color:var(--teal); font-size:1.1rem;">${row.score}%</span></div>
                <div class="meta-stat" style="margin-right:0.5rem;"><span class="meta-label">Time Taken</span><span class="meta-val" style="font-size:1rem;color:var(--text);">${row.time}</span></div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                    <button class="btn-ghost-sm" onclick='openReviewModal(${JSON.stringify(row).replace(/'/g, "&apos;")}, "all")' style="${filterMode==='all'?'background:var(--teal);color:#fff;':''}">View All</button>
                    ${wrongIdx.length > 0 ? `<button class="btn-ghost-sm" onclick='openReviewModal(${JSON.stringify(row).replace(/'/g, "&apos;")}, "wrong")' style="color:var(--red); border-color:var(--red); ${filterMode==='wrong'?'background:var(--red);color:#fff;':''}">View Wrong (${wrongIdx.length})</button>` : ''}
                    ${totalWeak > 0 ? `<button class="btn-ghost-sm" onclick='openReviewModal(${JSON.stringify(row).replace(/'/g, "&apos;")}, "weak")' style="color:var(--amber-light); border-color:var(--amber-light); ${filterMode==='weak'?'background:var(--amber-light);color:#fff;':''}">View Weak (${totalWeak})</button>` : ''}
                </div>
            </div>
            <div class="ai-badge" style="margin-bottom:1rem;">✦ Detailed Solutions &amp; Insights</div>
            <div class="sol-list" style="display:flex; flex-direction:column; gap:1.2rem;">
        `;

        const savedStateStr = localStorage.getItem('upsc_test_state_' + testId);
        let savedState = null;
        if (savedStateStr) {
            try { savedState = JSON.parse(savedStateStr); } catch(e){}
        }

        // Load existing tags for this test
        const reviewTagData = JSON.parse(localStorage.getItem('upsc_review_' + testId) || '{"tags":{}}');

        questions.forEach((q, i) => {
            const userAnsTemp = savedState && savedState[i] && savedState[i].selected ? savedState[i].selected : null;
            const isCorTemp = userAnsTemp && userAnsTemp === q.correct_option;
            const isSkipTemp = !userAnsTemp;

            if (filterMode === 'wrong' && (isCorTemp || isSkipTemp)) return;
            if (filterMode === 'weak' && isCorTemp) return;

            const diffRandom = ((q.id * 17) % 100);
            const difficulty = diffRandom > 75 ? 'Hard' : diffRandom > 35 ? 'Medium' : 'Easy';
            const diffColor = difficulty === 'Hard' ? 'var(--red)' : difficulty === 'Medium' ? 'var(--amber-light)' : 'var(--teal)';
            const pctCorrect = Math.max(15, 95 - diffRandom);
            const avgTime = 30 + Math.floor(diffRandom / 2);

            const userAns = savedState && savedState[i] && savedState[i].selected ? savedState[i].selected : null;
            
            let optionsHtml = '<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.5rem;">';
            ['a', 'b', 'c', 'd'].forEach(optLetter => {
                const optText = q.options[optLetter];
                if (!optText) return;
                
                const isCorrect = optLetter === q.correct_option;
                const isAttempted = optLetter === userAns;
                
                let optStyle = 'padding: 0.8rem; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-lighter);';
                let indicator = '';
                
                if (isCorrect && isAttempted) {
                    optStyle = 'padding: 0.8rem; border-radius: 6px; border: 1px solid var(--teal); background: rgba(29,158,117,0.1);';
                    indicator = '<span style="color:var(--teal); font-weight:bold; margin-left:auto; font-size:0.85rem;">✓ Your Attempt & Correct</span>';
                } else if (isCorrect) {
                    optStyle = 'padding: 0.8rem; border-radius: 6px; border: 1px solid var(--teal); background: rgba(29,158,117,0.1);';
                    indicator = '<span style="color:var(--teal); font-weight:bold; margin-left:auto; font-size:0.85rem;">✓ Correct Answer</span>';
                } else if (isAttempted && !isCorrect) {
                    optStyle = 'padding: 0.8rem; border-radius: 6px; border: 1px solid var(--red); background: rgba(226,75,74,0.1);';
                    indicator = '<span style="color:var(--red); font-weight:bold; margin-left:auto; font-size:0.85rem;">✗ Your Attempt</span>';
                }
                
                optionsHtml += `
                    <div style="${optStyle} display:flex; align-items:center;">
                        <strong style="margin-right:1rem; color:var(--text-muted);">${optLetter.toUpperCase()}.</strong>
                        <span style="color:var(--text);">${optText}</span>
                        ${indicator}
                    </div>
                `;
            });
            optionsHtml += '</div>';

            html += `
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:8px; padding:1.2rem;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem;">
                        <strong style="font-size:1.05rem; color:var(--text); line-height:1.5; padding-right:1rem;">Q${i+1}. ${q.question}</strong>
                        <span style="font-size:0.75rem; padding:3px 8px; border-radius:12px; background:rgba(255,255,255,0.1); color:${diffColor}; white-space:nowrap;">${difficulty}</span>
                    </div>
                    
                    ${optionsHtml}

                    <div style="background:var(--bg-lighter); padding:1rem; border-radius:6px; margin-bottom:1rem;">
                        <div style="font-size:0.85rem; color:var(--teal); font-weight:600; margin-bottom:0.5rem;">Explanation</div>
                        <div style="font-size:0.9rem; color:var(--text-muted); line-height:1.6;">${q.rationale || 'No explanation provided.'}</div>
                    </div>

                    <div style="background:rgba(186,117,23,0.08); border-left:3px solid var(--amber-light); padding:1rem; border-radius:4px; margin-bottom:1rem;">
                        <div style="font-size:0.85rem; color:var(--amber-light); font-weight:600; margin-bottom:0.3rem;">Mains Takeaway / Fact</div>
                        <div style="font-size:0.9rem; color:var(--text-muted); line-height:1.5;">${q.mains_hint || 'Revise key concepts for related Mains questions.'}</div>
                    </div>

                    <div style="display:flex; gap:2rem; justify-content:flex-start; border-top:1px solid var(--border); padding-top:1rem; margin-top:0.5rem; font-size:0.85rem; color:var(--text-faint);">
                        <span>Attempt Correctness: <strong style="color:var(--text-muted);">${pctCorrect}%</strong></span>
                        <span>Avg. Time Taken: <strong style="color:var(--text-muted);">${avgTime}s</strong></span>
                    </div>

                    <div class="q-tag-row">
                        <span class="q-tag-label">Tag this question:</span>
                        <button class="q-tag-btn ${reviewTagData.tags && reviewTagData.tags[i]==='doubt' ? 'active-doubt' : ''}" onclick="tagQuestionModal(${i},'doubt',${testId},this.parentElement)" title="I didn't understand this concept">🔴 Doubt</button>
                        <button class="q-tag-btn ${reviewTagData.tags && reviewTagData.tags[i]==='guess' ? 'active-guess' : ''}" onclick="tagQuestionModal(${i},'guess',${testId},this.parentElement)" title="I guessed correctly">🟡 Guess</button>
                        <button class="q-tag-btn ${reviewTagData.tags && reviewTagData.tags[i]==='revise' ? 'active-revise' : ''}" onclick="tagQuestionModal(${i},'revise',${testId},this.parentElement)" title="Needs revision">🔵 Revise Later</button>
                    </div>
                </div>
            `;
        });
        
        html += `</div>`;
        document.getElementById('review-modal-body').innerHTML = html;

    } catch (e) {
        console.error(e);
        document.getElementById('review-modal-body').innerHTML = `<div style="color:var(--red); padding:1rem;">Failed to load solutions. Please try again later.</div>`;
    }
}

function closeReviewModal(event) {
    if (event.target === document.getElementById('review-modal')) {
        document.getElementById('review-modal').classList.add('hidden');
    }
}

// Works the same as tagQuestion but called from the history View modal
function tagQuestionModal(qIndex, tag, testId, containerEl) {
    tagQuestion(qIndex, tag, testId, containerEl);
}

// ======================== QUESTION GENERATOR ========================
let selectedCount = 10;

function selectCount(n) {
    selectedCount = n;
    AppState.genCount = n;
    document.querySelectorAll('.count-pill').forEach(p => {
        p.classList.toggle('active', parseInt(p.dataset.count) === n);
    });
}

function handleTopicInput(val) {
    AppState.genTopic = val;
    const dropdown = document.getElementById('topic-dropdown');
    if (!val.trim()) { dropdown.classList.add('hidden'); return; }

    const lower = val.toLowerCase();

    // Keyword matches
    const kwMatches = TOPIC_SUGGESTIONS_DB.filter(t => t.toLowerCase().includes(lower)).slice(0, 5);

    // Semantic matches (only when few keyword matches)
    const semMatches = kwMatches.length < 3
        ? SEMANTIC_SUGGESTIONS_DB.filter(s => lower.includes(s.q) || s.q.includes(lower.split(' ')[0])).map(s => s.s).slice(0, 2)
        : [];

    let html = '';
    if (kwMatches.length > 0) {
        html += `<div class="dropdown-group-label">Suggestions</div>`;
        kwMatches.forEach(s => {
            html += `<div class="dropdown-item keyword-type" onmousedown="selectTopic('${s.replace(/'/g, "\\'")}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                ${s}
            </div>`;
        });
    }
    if (semMatches.length > 0) {
        html += `<div class="dropdown-group-label" style="margin-top:0.25rem;">Related Topics</div>`;
        semMatches.forEach(s => {
            html += `<div class="dropdown-item semantic-type" onmousedown="selectTopic('${s.replace(/'/g, "\\'")}')">
                <span class="dropdown-semantic-badge">✦</span>
                ${s}
            </div>`;
        });
    }

    if (html) {
        dropdown.innerHTML = html;
        dropdown.classList.remove('hidden');
    } else {
        dropdown.classList.add('hidden');
    }
}

function selectTopic(topic) {
    document.getElementById('gen-topic-input').value = topic;
    AppState.genTopic = topic;
    document.getElementById('topic-dropdown').classList.add('hidden');
}

function hideDropdown() {
    setTimeout(() => document.getElementById('topic-dropdown').classList.add('hidden'), 150);
}

function handleTopicKeydown(e) {
    if (e.key === 'Enter') { e.preventDefault(); generateMCQs(); }
}

async function generateMCQs() {
    const topic = document.getElementById('gen-topic-input').value.trim();
    if (!topic) {
        document.getElementById('gen-topic-input').focus();
        document.getElementById('gen-topic-input').style.borderColor = 'var(--red)';
        setTimeout(() => document.getElementById('gen-topic-input').style.borderColor = '', 2000);
        return;
    }

    // Check Free Tier Quota
    const u = AppState.user;
    if (u && !u.isPremium) {
        const today = new Date().toISOString().split('T')[0];
        const quotaKey = `upsc_gen_count_${today}`;
        const usedCount = parseInt(localStorage.getItem(quotaKey) || '0');
        if (usedCount + AppState.genCount > 25) {
            document.getElementById('upsell-message').textContent = `You've requested ${AppState.genCount} questions, but only have ${Math.max(0, 25 - usedCount)} free generations left today. Upgrade to Premium for unlimited generation!`;
            document.getElementById('premium-upsell-modal').classList.remove('hidden');
            return;
        }
        localStorage.setItem(quotaKey, usedCount + AppState.genCount);
        updateDailyQuotaUI();
    }

    // Hide questions, show loading
    document.getElementById('gen-questions-container').classList.add('hidden');
    document.getElementById('gen-loading').classList.remove('hidden');

    // Animate progress
    const fills = ['Fetching RAG context from PGVector...', 'Selecting relevant current affairs...', 'Generating questions via LLM cascade...', 'Running hallucination-guard critique node...', 'Finalizing & formatting questions...'];
    let step = 0;
    const fillEl = document.getElementById('loading-fill');
    const subEl = document.getElementById('loading-sub');

    // Render skeletons
    renderSkeletons(AppState.genCount);

    const progressInterval = setInterval(() => {
        step++;
        fillEl.style.width = `${Math.min(step * 18, 90)}%`;
        subEl.textContent = fills[Math.min(step, fills.length - 1)];
    }, 600);

    // Try real API, fallback to demo data
    let questions = [];
    try {
        const allRefs = [];
        for (let i = 0; i < Math.min(AppState.genCount, 5); i++) {
            const res = await fetch(`/generate/${encodeURIComponent(topic)}`);
            if (!res.ok) throw new Error('API error');
            const data = await res.json();
            if (data.status === 'success' && data.data?.mcq) {
                const mcq = data.data.mcq;
                allRefs.push({
                    id: i + 1,
                    question: mcq.question,
                    options: mcq.options,
                    correct: mcq.correct_option,
                    explanation: mcq.rationale || mcq.explanation || 'No explanation provided.'
                });
            }
        }
        questions = allRefs.length > 0 ? allRefs : generateSampleQuestions(topic, AppState.genCount);
    } catch (e) {
        // Backend not running — use sample questions
        await new Promise(r => setTimeout(r, 3000)); // Simulate latency
        questions = generateSampleQuestions(topic, AppState.genCount);
    }

    clearInterval(progressInterval);
    fillEl.style.width = '100%';
    await new Promise(r => setTimeout(r, 400));

    // Render questions
    document.getElementById('gen-loading').classList.add('hidden');
    AppState.generatedQuestions = questions;
    AppState.genAnswers = {};
    renderGeneratedQuestions(topic, questions);

    // Save to history
    const entry = { topic, count: questions.length, date: new Date().toLocaleDateString() };
    AppState.recentGenerations.unshift(entry);
    AppState.recentGenerations = AppState.recentGenerations.slice(0, 10);
    localStorage.setItem('recentGenerations', JSON.stringify(AppState.recentGenerations));
    renderRecentGenerations();
}

function renderSkeletons(count) {
    const el = document.getElementById('gen-skeletons');
    el.innerHTML = '';
    const n = Math.min(count, 4);
    for (let i = 0; i < n; i++) {
        el.innerHTML += `
            <div class="skeleton-card">
                <div class="skeleton-line wide"></div>
                <div class="skeleton-line medium"></div>
                <div class="skeleton-line short"></div>
                <div class="skeleton-line medium" style="margin-top:1rem;height:38px;border-radius:8px;"></div>
                <div class="skeleton-line medium" style="height:38px;border-radius:8px;"></div>
                <div class="skeleton-line short" style="height:38px;border-radius:8px;"></div>
            </div>`;
    }
}

function renderGeneratedQuestions(topic, questions) {
    document.getElementById('gen-questions-topic-title').textContent = `Questions on: ${topic}`;
    const list = document.getElementById('gen-questions-list');
    list.innerHTML = '';

    questions.forEach((q, idx) => {
        const card = document.createElement('div');
        card.className = 'gen-q-card';
        card.id = `gen-q-${idx}`;

        let optionsHtml = Object.entries(q.options).map(([key, val]) =>
            `<div class="gen-q-option" data-key="${key}" data-qidx="${idx}" onclick="selectGenOption(this, ${idx}, '${key}')">
                <span style="font-weight:700;color:var(--text-faint);min-width:20px;">${key.toUpperCase()}.</span>
                <span>${val}</span>
            </div>`
        ).join('');

        card.innerHTML = `
            <div class="gen-q-num">Question ${idx + 1} of ${questions.length}</div>
            <div class="gen-q-text">${q.question}</div>
            <div class="gen-q-options">${optionsHtml}</div>
            <div class="gen-q-footer">
                <button class="btn-primary-sm" onclick="submitGenAnswer(${idx})">Submit Answer</button>
            </div>
            <div class="gen-explanation hidden" id="gen-exp-${idx}">
                <div class="gen-explanation-label">✦ AI Explanation</div>
                <div id="gen-exp-text-${idx}"></div>
            </div>`;
        list.appendChild(card);
    });

    document.getElementById('gen-questions-container').classList.remove('hidden');
    document.getElementById('gen-submit-all-footer').classList.remove('hidden');
}

function selectGenOption(el, qIdx, key) {
    if (AppState.genAnswers[qIdx] !== undefined) return; // Already answered
    const card = document.getElementById(`gen-q-${qIdx}`);
    card.querySelectorAll('.gen-q-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    AppState.genAnswers[`sel_${qIdx}`] = key; // Temp selection
}

function submitGenAnswer(qIdx) {
    const card = document.getElementById(`gen-q-${qIdx}`);
    const selected = card.querySelector('.gen-q-option.selected');
    if (!selected) {
        selected?.classList.add('error');
        return;
    }
    if (AppState.genAnswers[qIdx] !== undefined) return; // Already submitted

    const key = selected.dataset.key;
    const correct = AppState.generatedQuestions[qIdx].correct;
    AppState.genAnswers[qIdx] = key;

    // Reveal
    card.querySelectorAll('.gen-q-option').forEach(o => {
        o.style.pointerEvents = 'none';
        if (o.dataset.key === correct) o.classList.add('correct');
        else if (o.dataset.key === key) o.classList.add('incorrect');
    });

    // Show explanation
    const expEl = document.getElementById(`gen-exp-${qIdx}`);
    document.getElementById(`gen-exp-text-${qIdx}`).textContent = AppState.generatedQuestions[qIdx].explanation;
    expEl.classList.remove('hidden');

    // Hide footer button of this card
    card.querySelector('.gen-q-footer').innerHTML = key === correct
        ? '<span style="color:var(--teal);font-weight:700;">✓ Correct!</span>'
        : `<span style="color:var(--red);font-weight:700;">✗ Incorrect — Correct: ${correct.toUpperCase()}</span>`;
}

function submitAllAnswers() {
    let correct = 0, wrong = 0, skipped = 0;
    const wrongIdx = [];
    const skipIdx = [];

    AppState.generatedQuestions.forEach((q, idx) => {
        if (AppState.genAnswers[idx] === undefined) {
            submitGenAnswer(idx);
        }
        
        const ans = AppState.genAnswers[idx];
        if (!ans) {
            skipped++;
            skipIdx.push(idx);
        } else if (ans === q.correct) {
            correct++;
        } else {
            wrong++;
            wrongIdx.push(idx);
        }
    });

    const total = AppState.generatedQuestions.length;
    const pct = Math.round((correct / total) * 100);

    const testId = 'ai_' + Date.now();
    const topic = document.getElementById('gen-topic-input').value.trim() || 'AI Generated Test';

    // Save review data for retry
    const reviewData = { wrongIndices: wrongIdx, unattemptedIndices: skipIdx, tags: {} };
    localStorage.setItem('upsc_review_' + testId, JSON.stringify(reviewData));

    // Save state for history viewer
    const state = AppState.generatedQuestions.map((q, i) => ({
        status: AppState.genAnswers[i] ? 'answered' : 'not-answered',
        selected: AppState.genAnswers[i] || null
    }));
    localStorage.setItem('upsc_test_state_' + testId, JSON.stringify(state));

    // Save questions locally so they can be reviewed/retried
    const aiTests = JSON.parse(localStorage.getItem('upsc_ai_tests') || '{}');
    aiTests[testId] = AppState.generatedQuestions;
    localStorage.setItem('upsc_ai_tests', JSON.stringify(aiTests));

    // Add to history
    const attempt = {
        test: `AI: ${topic}`,
        date: new Date().toISOString().split('T')[0],
        score: pct, rank: '-', subject: 'Custom AI',
        time: 'N/A', id: testId
    };
    AppState.testAttempts.unshift(attempt);
    localStorage.setItem('upsc_prototypeAttempts_v1', JSON.stringify(AppState.testAttempts));
    
    // Update streak tracking
    const today = new Date().toISOString().split('T')[0];
    let dailyStats = JSON.parse(localStorage.getItem('upsc_daily_stats') || '{}');
    dailyStats[today] = (dailyStats[today] || 0) + (correct + wrong);
    localStorage.setItem('upsc_daily_stats', JSON.stringify(dailyStats));
    updateStreak();

    // Disable the submit button
    const btn = document.querySelector('#gen-submit-all-footer button');
    if (btn) {
        btn.textContent = 'Saved to Hub!';
        btn.disabled = true;
        btn.style.background = 'var(--teal)';
    }

    alert(`Test results successfully saved to your Analytics Hub! Score: ${pct}%`);
}

function renderRecentGenerations() {
    const list = document.getElementById('recent-gen-list');
    if (!list) return;
    if (AppState.recentGenerations.length === 0) {
        list.innerHTML = '<p style="color:var(--text-faint);font-size:0.85rem;text-align:center;padding:1rem;">No recent generations yet.</p>';
        return;
    }
    list.innerHTML = AppState.recentGenerations.map((g, i) => `
        <div class="recent-gen-item">
            <div>
                <div class="recent-topic">${g.topic}</div>
                <div class="recent-meta">${g.count} questions · ${g.date}</div>
            </div>
            <button class="recent-regen-btn" onclick="regenTopic('${g.topic.replace(/'/g, "\\'")}')">↻ Regen</button>
        </div>`).join('');
}

function regenTopic(topic) {
    document.getElementById('gen-topic-input').value = topic;
    AppState.genTopic = topic;
    generateMCQs();
}

// ======================== DOM READY ========================
document.addEventListener('DOMContentLoaded', async () => {

    // ── Try to restore session from saved JWT token ──────────────────────────────────
    const savedToken = localStorage.getItem('upsc_token');
    if (savedToken) {
        try {
            // Validate token against server — catches expired or tampered tokens
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${savedToken}` }
            });

            if (res.ok) {
                const data = await res.json();
                const avatar = data.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
                AppState.user = {
                    user_id: data.user_id,
                    name:    data.name,
                    email:   data.email,
                    role:    data.role,
                    avatar,
                    token:   savedToken,
                };
                // Silently enter the app — no login screen needed
                document.getElementById('auth-overlay').classList.add('hidden');
                document.getElementById('app').classList.remove('hidden');
                updateUserUI();
                initApp();
            } else {
                // Token expired or invalid — clear it and show login
                localStorage.removeItem('upsc_token');
                localStorage.removeItem('upsc_user');
            }
        } catch (err) {
            // Network error — fall through to login screen
            console.warn('[Auth] Could not validate token:', err.message);
        }
    }

    // ── Mobile sidebar: close when clicking outside ────────────────────────────────
    document.addEventListener('click', (e) => {
        const sidebar = document.getElementById('sidebar');
        if (window.innerWidth <= 768 && sidebar.classList.contains('mobile-open')) {
            if (!sidebar.contains(e.target) && !e.target.closest('.mobile-menu-btn')) {
                sidebar.classList.remove('mobile-open');
            }
        }
    });
});

// ======================== TO-DO LIST ========================
// ======================== HIERARCHICAL TODO LIST ========================
// Data shape: [{topic, notes, subtopics:[{text, done}], collapsed}]

function _saveTodos(todos) {
    localStorage.setItem('upsc_todos', JSON.stringify(todos));
}
function _loadTodos() {
    return JSON.parse(localStorage.getItem('upsc_todos') || '[]');
}

function renderTodos(todos) {
    const list = document.getElementById('ai-todo-list');
    if (!list) return;
    list.innerHTML = '';

    if (!todos || todos.length === 0) {
        list.innerHTML = '<div style="color:var(--text-faint);font-size:0.85rem;padding:12px;">No tasks yet. Add a parent topic above or click a subject bar to get AI recommendations.</div>';
        return;
    }

    todos.forEach((group, gi) => {
        const topic = typeof group === 'string' ? group : (group.topic || group);
        const subtopics = typeof group === 'object' && group.subtopics ? group.subtopics : [];
        const collapsed = typeof group === 'object' ? group.collapsed : false;

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'border:1px solid var(--border); border-radius:10px; overflow:hidden; background:var(--surface);';

        // Parent row
        const parentRow = document.createElement('div');
        parentRow.style.cssText = 'display:flex; align-items:center; gap:10px; padding:10px 14px; cursor:pointer; background:var(--bg-2); border-bottom:' + (collapsed || subtopics.length === 0 ? 'none' : '1px solid var(--border)') + ';';
        parentRow.innerHTML = `
            <span style="font-size:0.75rem; font-weight:800; color:var(--text-faint); width:24px; flex-shrink:0;">${gi + 1}</span>
            <span style="font-weight:700; flex:1; font-size:0.9rem;">${topic}</span>
            <span onclick="addSubtopicInline(${gi})" style="cursor:pointer; color:var(--teal); font-size:0.8rem; padding:2px 8px; border:1px solid var(--teal); border-radius:4px; white-space:nowrap;">+ Sub-topic</span>
            <span onclick="toggleTodoGroup(${gi})" style="cursor:pointer; color:var(--text-faint); font-size:0.85rem; padding:2px 6px;">${collapsed ? '▶' : '▼'}</span>
            <span onclick="removeParentTodo(${gi})" style="cursor:pointer; color:var(--red); font-size:0.9rem; padding:2px 6px;" title="Delete">✕</span>
        `;
        wrapper.appendChild(parentRow);

        // Subtopics
        if (!collapsed) {
            subtopics.forEach((sub, si) => {
                const subRow = document.createElement('div');
                subRow.style.cssText = 'display:flex; align-items:center; gap:10px; padding:8px 14px 8px 36px; border-bottom:1px solid var(--border);';
                const subText = typeof sub === 'string' ? sub : sub.text;
                const done = typeof sub === 'object' ? sub.done : false;
                subRow.innerHTML = `
                    <span style="font-size:0.72rem; color:var(--text-faint); width:30px; flex-shrink:0;">${gi + 1}.${si + 1}</span>
                    <input type="checkbox" ${done ? 'checked' : ''} onchange="toggleSubDone(${gi},${si},this.checked)" style="width:15px;height:15px;cursor:pointer;accent-color:var(--teal);">
                    <span style="flex:1; font-size:0.85rem; text-decoration:${done ? 'line-through' : 'none'}; color:${done ? 'var(--text-faint)' : 'var(--text)'}; cursor:pointer;" onclick="startEditSubtopic(${gi},${si})">${subText}</span>
                    <span style="font-size:0.75rem; color:var(--text-faint);">-</span>
                    <span onclick="removeSubtopic(${gi},${si})" style="cursor:pointer; color:var(--red); font-size:0.8rem;">✕</span>
                `;
                wrapper.appendChild(subRow);
            });

            // Inline add subtopic input (hidden by default)
            const addRow = document.createElement('div');
            addRow.id = 'add-sub-row-' + gi;
            addRow.style.cssText = 'display:none; align-items:center; gap:8px; padding:8px 14px 8px 36px; background:var(--bg-3);';
            addRow.innerHTML = `
                <span style="font-size:0.72rem; color:var(--text-faint); width:30px;">${gi + 1}.${subtopics.length + 1}</span>
                <input id="sub-input-${gi}" type="text" class="search-input" style="flex:1; padding:4px 8px; font-size:0.82rem;" placeholder="Sub-topic name..." onkeydown="if(event.key==='Enter') saveSubtopic(${gi})">
                <button class="btn-attempt" style="padding:4px 10px; font-size:0.8rem;" onclick="saveSubtopic(${gi})">Add</button>
                <button class="btn-ghost" style="padding:4px 8px; font-size:0.8rem;" onclick="document.getElementById('add-sub-row-${gi}').style.display='none';">✕</button>
            `;
            wrapper.appendChild(addRow);
        }

        list.appendChild(wrapper);
    });
}

function addTodoItem() {
    const input = document.getElementById('custom-todo-input');
    const summaryInput = document.getElementById('custom-todo-summary');
    const val = input.value.trim();
    if (!val) return;
    let todos = _loadTodos();
    todos.push({ topic: val, notes: summaryInput ? summaryInput.value.trim() : '', subtopics: [], collapsed: false });
    _saveTodos(todos);
    renderTodos(todos);
    input.value = '';
    if (summaryInput) summaryInput.value = '';
}

function removeParentTodo(gi) {
    let todos = _loadTodos();
    todos.splice(gi, 1);
    _saveTodos(todos);
    renderTodos(todos);
}

function removeTodoItem(idx) { removeParentTodo(idx); }

function toggleTodoGroup(gi) {
    let todos = _loadTodos();
    if (typeof todos[gi] === 'object') todos[gi].collapsed = !todos[gi].collapsed;
    _saveTodos(todos);
    renderTodos(todos);
}

function addSubtopicInline(gi) {
    const row = document.getElementById('add-sub-row-' + gi);
    if (row) { row.style.display = 'flex'; const inp = document.getElementById('sub-input-' + gi); if (inp) inp.focus(); }
}

function saveSubtopic(gi) {
    const inp = document.getElementById('sub-input-' + gi);
    if (!inp || !inp.value.trim()) return;
    let todos = _loadTodos();
    if (typeof todos[gi] !== 'object') todos[gi] = { topic: todos[gi], subtopics: [], collapsed: false };
    if (!todos[gi].subtopics) todos[gi].subtopics = [];
    todos[gi].subtopics.push({ text: inp.value.trim(), done: false });
    _saveTodos(todos);
    renderTodos(todos);
}

function removeSubtopic(gi, si) {
    let todos = _loadTodos();
    todos[gi].subtopics.splice(si, 1);
    _saveTodos(todos);
    renderTodos(todos);
}

function toggleSubDone(gi, si, done) {
    let todos = _loadTodos();
    todos[gi].subtopics[si].done = done;
    _saveTodos(todos);
    renderTodos(todos);
}

function startEditSubtopic(gi, si) {
    let todos = _loadTodos();
    const current = todos[gi].subtopics[si].text;
    // Build a proper modal
    const existingModal = document.getElementById('edit-subtopic-modal');
    if (existingModal) existingModal.remove();
    const modal = document.createElement('div');
    modal.id = 'edit-subtopic-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);z-index:9999;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
        <div style="background:var(--bg-2);border:1px solid var(--border-strong);border-radius:16px;padding:24px;width:420px;max-width:90vw;box-shadow:0 25px 60px rgba(0,0,0,0.5);animation:slideUp 0.25s ease;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <h3 style="margin:0;font-size:1rem;">Edit Sub-topic</h3>
                <button onclick="document.getElementById('edit-subtopic-modal').remove()" style="background:none;border:none;color:var(--text-muted);font-size:1.2rem;cursor:pointer;">✕</button>
            </div>
            <label style="font-size:0.82rem;color:var(--text-muted);display:block;margin-bottom:6px;">Sub-topic name</label>
            <input id="edit-sub-input" type="text" value="${current.replace(/"/g,'&quot;')}" style="width:100%;background:var(--bg-3);border:1px solid var(--border);color:var(--text);padding:10px 12px;border-radius:8px;font-size:0.9rem;margin-bottom:16px;box-sizing:border-box;" onkeydown="if(event.key==='Enter') window._saveEditSub(${gi},${si})">
            <div style="display:flex;gap:10px;justify-content:flex-end;">
                <button onclick="document.getElementById('edit-subtopic-modal').remove()" style="padding:8px 18px;background:var(--bg-3);border:1px solid var(--border);color:var(--text);border-radius:8px;cursor:pointer;font-size:0.88rem;">Cancel</button>
                <button onclick="window._saveEditSub(${gi},${si})" style="padding:8px 18px;background:var(--primary);border:none;color:white;border-radius:8px;cursor:pointer;font-weight:700;font-size:0.88rem;">Save</button>
            </div>
        </div>`;
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    document.body.appendChild(modal);
    setTimeout(() => document.getElementById('edit-sub-input').focus(), 50);
}

window._saveEditSub = function(gi, si) {
    const inp = document.getElementById('edit-sub-input');
    if (!inp || !inp.value.trim()) return;
    let todos = _loadTodos();
    todos[gi].subtopics[si].text = inp.value.trim();
    _saveTodos(todos);
    renderTodos(todos);
    document.getElementById('edit-subtopic-modal').remove();
}

// ======================== TIER / RANK ENGINE ========================
const TIER_CONFIG = [
    { id: 'aspirant',    emoji: '🌱', name: 'Aspirant',    min: 0,    max: 300,  color: '#6b7280', glow: 'rgba(107,114,128,0.4)' },
    { id: 'grinder',     emoji: '⚙️', name: 'Grinder',     min: 300,  max: 700,  color: '#78716c', glow: 'rgba(120,113,108,0.4)' },
    { id: 'challenger',  emoji: '⚔️', name: 'Challenger',  min: 700,  max: 1200, color: '#3b82f6', glow: 'rgba(59,130,246,0.4)'  },
    { id: 'eliminator',  emoji: '🔥', name: 'Eliminator',  min: 1200, max: 1800, color: '#f97316', glow: 'rgba(249,115,22,0.4)'  },
    { id: 'dominator',   emoji: '🦾', name: 'Dominator',   min: 1800, max: 2500, color: '#a855f7', glow: 'rgba(168,85,247,0.4)'  },
    { id: 'apex',        emoji: '🏆', name: 'Apex Ranker', min: 2500, max: 3300, color: '#eab308', glow: 'rgba(234,179,8,0.4)'   },
    { id: 'legend',      emoji: '👑', name: 'Legend',      min: 3300, max: Infinity, color: '#f43f5e', glow: 'rgba(244,63,94,0.4)' }
];

function getTierForTP(tp) {
    return TIER_CONFIG.find(t => tp >= t.min && tp < t.max) || TIER_CONFIG[0];
}

function getAccuracyMultiplier(accuracy) {
    if (accuracy >= 80) return 1.6;
    if (accuracy >= 70) return 1.4;
    if (accuracy >= 60) return 1.25;
    if (accuracy >= 50) return 1.1;
    if (accuracy >= 40) return 1.0;
    return 0.8;
}

function computeTierPoints() {
    // Collect all questions across last 300-500 qs from test attempts (rolling window)
    const attempts = AppState.testAttempts || [];
    let allInteractions = []; // { correct, wrong, unattempted, date }

    attempts.forEach(attempt => {
        const qs    = JSON.parse(localStorage.getItem('upsc_test_questions_' + attempt.id) || '[]');
        const state = JSON.parse(localStorage.getItem('upsc_test_state_'     + attempt.id) || '[]');
        const date  = attempt.date || '';
        qs.forEach((q, i) => {
            const answered = state[i] ? state[i].selected : null;
            const correct  = q.correct_option || q.correct;
            let type;
            if (!answered) type = 'unattempted';
            else if (answered === correct) type = 'correct';
            else type = 'wrong';
            allInteractions.push({ type, date });
        });
    });

    // Rolling window: last 400 interactions
    const window = allInteractions.slice(-400);
    if (window.length === 0) return { tp: 0, rawPoints: 0, multiplier: 1, accuracy: 0, correct: 0, wrong: 0, unattempted: 0, total: 0, dailyBonus: 0, streakBonus: 0 };

    const correct     = window.filter(x => x.type === 'correct').length;
    const wrong       = window.filter(x => x.type === 'wrong').length;
    const unattempted = window.filter(x => x.type === 'unattempted').length;
    const total       = window.length;
    const attempted   = correct + wrong;
    const accuracy    = attempted > 0 ? Math.round((correct / attempted) * 100) : 0;

    const rawPoints = (correct * 4) + (wrong * -2) + (unattempted * 1);
    const multiplier = getAccuracyMultiplier(accuracy);

    // Daily attempt bonus — based on upsc_daily_stats
    const dailyStats = JSON.parse(localStorage.getItem('upsc_daily_stats') || '{}');
    let dailyBonus = 0;
    const today = new Date(); today.setHours(0,0,0,0);
    for (let i = 0; i < 5; i++) { // last 5 days
        const d = new Date(today); d.setDate(today.getDate() - i);
        const ds = d.toISOString().split('T')[0];
        const count = dailyStats[ds] || 0;
        if (count >= 80) dailyBonus += 35;
        else if (count >= 50) dailyBonus += 20;
        else if (count >= 30) dailyBonus += 10;
    }

    // Streak bonus — read from upsc_streak (maintained by updateStreak())
    const streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"count":0}');
    const streak = streakData.count || 0;
    let streakMultiplier = 1;
    if (streak >= 10) streakMultiplier = 1.15;
    else if (streak >= 5) streakMultiplier = 1.10;
    else if (streak >= 3) streakMultiplier = 1.05;

    // Also add flat streak bonus TP on top (5 TP per streak day, capped at 100)
    const flatStreakBonus = Math.min(streak * 5, 100);
    const streakBonus = Math.round((rawPoints * multiplier) * (streakMultiplier - 1)) + flatStreakBonus;

    const tp = Math.max(0, Math.round((rawPoints * multiplier) + dailyBonus + streakBonus));
    return { tp, rawPoints, multiplier, accuracy, correct, wrong, unattempted, total, dailyBonus, streakBonus, streak };
}

function applyTierTheme(tier) {
    let styleTag = document.getElementById('tier-theme-style');
    if (!styleTag) {
        styleTag = document.createElement('style');
        styleTag.id = 'tier-theme-style';
        document.head.appendChild(styleTag);
    }
    // Inject tier-specific accent colour overrides
    styleTag.textContent = `
        :root {
            --tier-accent: ${tier.color};
            --tier-glow: ${tier.glow};
        }
        #tier-hero { border-color: ${tier.color}44 !important; }
        #tier-progress-bar { background: ${tier.color} !important; }
        .tier-themed-border { border-color: ${tier.color}55 !important; }
        @keyframes tierProgressGlow {
            0%, 100% { box-shadow: 0 0 8px ${tier.color}44; }
            50% { box-shadow: 0 0 16px ${tier.color}88; }
        }
    `;
}

function renderTierCard(tierData) {
    const { tp, rawPoints, multiplier, accuracy, correct, wrong, unattempted, total, dailyBonus, streakBonus, streak } = tierData;
    const tier     = getTierForTP(tp);
    const nextTier = TIER_CONFIG[TIER_CONFIG.indexOf(tier) + 1] || null;
    const currTierIdx = TIER_CONFIG.indexOf(tier);

    // Load previous state for promotion/demotion
    const prev = JSON.parse(localStorage.getItem('upsc_tier_state') || '{}');
    const prevTierIdx = prev.tierIdx !== undefined ? prev.tierIdx : currTierIdx;
    const now = Date.now();
    const daysSince = prev.lastCalc ? (now - prev.lastCalc) / (1000 * 60 * 60 * 24) : 999;
    if (daysSince >= 5 || !prev.lastCalc) {
        localStorage.setItem('upsc_tier_state', JSON.stringify({ tp, tierIdx: currTierIdx, lastCalc: now }));
    }

    // Session Feedback (compare with tp at start of session)
    const sessionPrevTP = parseInt(sessionStorage.getItem('upsc_session_tp'));
    if (!isNaN(sessionPrevTP) && tp > sessionPrevTP) {
        const gain = tp - sessionPrevTP;
        const feedbackEl = document.getElementById('tier-session-feedback');
        if (feedbackEl) {
            feedbackEl.style.display = 'block';
            let nextTierText = '';
            if (nextTier) {
                const prog = Math.min(100, Math.round(((tp - tier.min) / (nextTier.min - tier.min)) * 100));
                nextTierText = `<div style="font-size:0.8rem; font-weight:600;">You are now ${prog}% closer to next tier</div>`;
            }
            feedbackEl.innerHTML = `<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <strong style="color:var(--teal);">+${gain} TP gained</strong> in recent session!
                    <span style="color:var(--text-muted); font-size:0.8rem; margin-left:10px;">Accuracy: ${accuracy}%</span>
                </div>
                ${nextTierText}
            </div>`;
        }
    }
    sessionStorage.setItem('upsc_session_tp', tp);

    // ── Apply tier theme ──
    applyTierTheme(tier);

    // ── Hero Banner DOM ──
    const heroBg   = document.getElementById('tier-hero-bg');
    const emojiEl  = document.getElementById('tier-emoji');
    const nameEl   = document.getElementById('tier-name');
    const tpEl     = document.getElementById('tier-tp-label');
    const badgeEl  = document.getElementById('tier-change-badge');

    if (heroBg) heroBg.style.background = `radial-gradient(ellipse at 0% 50%, ${tier.glow}, transparent 60%)`;
    if (emojiEl) emojiEl.textContent = tier.emoji;
    if (nameEl)  { nameEl.textContent = tier.name; nameEl.style.color = tier.color; }
    if (tpEl)    tpEl.textContent = tp.toLocaleString() + ' TP';

    // Progress bar & Motivation
    const progressCloser = document.getElementById('tier-progress-closer');
    const progressMotivate = document.getElementById('tier-progress-motivate');
    const barEl = document.getElementById('tier-progress-bar');
    const trackEl = document.getElementById('tier-progress-track');
    const barLRight = document.getElementById('tier-progress-label-right');
    const fastPromoEl = document.getElementById('tier-progress-fast-promo');
    const relativePerf = document.getElementById('tier-relative-perf');
    
    let progressPct = 0;
    if (nextTier) {
        progressPct = Math.min(100, Math.round(((tp - tier.min) / (nextTier.min - tier.min)) * 100));
        const sessions = Math.max(1, Math.ceil((nextTier.min - tp) / 40));
        if (progressCloser) progressCloser.textContent = `${progressPct}% complete — ~${sessions} sessions to ${nextTier.name}`;
        if (progressMotivate) progressMotivate.textContent = `Keep pushing! Fast promotion is within reach.`;
        if (barLRight) barLRight.innerHTML = `<span style="color:var(--text);">${tp.toLocaleString()}</span> / ${nextTier.min.toLocaleString()} TP`;
        if (barEl) {
            barEl.style.transition = 'none';
            barEl.style.width = '0%';
            setTimeout(() => {
                barEl.style.transition = 'width 1.8s cubic-bezier(0.2, 1, 0.3, 1.2), box-shadow 0.5s ease';
                barEl.style.width = progressPct + '%'; 
                barEl.style.background = `linear-gradient(90deg, ${tier.color}, ${nextTier.color})`;
                if (progressPct >= 80) barEl.style.boxShadow = `0 0 20px ${nextTier.color}88, inset 0 0 10px rgba(255,255,255,0.4)`;
                else barEl.style.boxShadow = `0 0 10px ${tier.color}44`;
            }, 300);
        }
        
        if (fastPromoEl) {
            const needed = Math.min(60, nextTier.min - tp);
            fastPromoEl.innerHTML = `👉 <strong>+${needed} TP</strong> today = fast promotion`;
        }
    } else {
        progressPct = 100;
        if (progressCloser) progressCloser.textContent = `You have reached the maximum tier!`;
        if (progressMotivate) progressMotivate.textContent = `Keep practicing to maintain your Legend status.`;
        if (barLRight) barLRight.textContent = `Next: MAX`;
        if (barEl) setTimeout(() => { barEl.style.width = '100%'; barEl.style.background = tier.color; }, 300);
        if (fastPromoEl) fastPromoEl.innerHTML = '';
    }
    
    // Top 20% glow
    if (trackEl) {
        if (progressPct >= 80) trackEl.style.animation = 'tierProgressGlow 2s infinite';
        else trackEl.style.animation = 'none';
    }

    // Relative Performance
    if (relativePerf) {
        relativePerf.style.display = 'inline-block';
        const aheadPct = Math.max(15, Math.min(99, progressPct + Math.floor(Math.random() * 10 - 5)));
        relativePerf.textContent = `Top ${100 - aheadPct}% in ${tier.name}`;
    }

    // Next Action Suggestion
    const actionText = document.getElementById('tier-next-action-text');
    if (actionText) {
        if (accuracy >= 70) {
            actionText.innerHTML = `Strong accuracy → attempt 25 Qs for <span style="color:#4ade80;">fast TP gain</span>`;
        } else if (accuracy > 0 && accuracy < 50) {
            actionText.innerHTML = `Improve accuracy to 70% to unlock <span style="color:#a78bfa;">higher multiplier</span>`;
        } else {
            actionText.innerHTML = `Push accuracy above 70% to boost your <span style="color:#fbbf24;">TP multiplier</span>`;
        }
    }

    // ── Promotion / Demotion badge + modal ──
    const promoted = currTierIdx > prevTierIdx;
    const demoted  = currTierIdx < prevTierIdx;
    if (badgeEl && prev.lastCalc) {
        if (promoted) {
            badgeEl.style.cssText = `display:inline-block; padding:4px 12px; border-radius:20px; font-weight:700; background:rgba(29,158,117,0.2); color:#4ade80; border:1px solid #4ade8055;`;
            badgeEl.textContent = '▲ Promoted!';
            setTimeout(() => showTierChangeModal(true, TIER_CONFIG[prevTierIdx], tier, tp), 600);
        } else if (demoted) {
            badgeEl.style.cssText = `display:inline-block; padding:4px 12px; border-radius:20px; font-weight:700; background:rgba(239,68,68,0.2); color:#f87171; border:1px solid #f8717155;`;
            badgeEl.textContent = '▼ Demoted';
            setTimeout(() => showTierChangeModal(false, TIER_CONFIG[prevTierIdx], tier, tp), 600);
        }
    }

    // ── Tier ladder — vertical, Legend at top, current tier highlighted ──
    const allTiersEl = document.getElementById('tier-all-tiers');
    if (allTiersEl) {
        const reversed = [...TIER_CONFIG].reverse(); // Legend first (best at top)
        allTiersEl.style.cssText = 'display:flex; flex-direction:column; gap:6px; width:100%; margin-top:8px;';
        allTiersEl.innerHTML = reversed.map((t) => {
            const idx = TIER_CONFIG.indexOf(t);
            const isCurr = idx === currTierIdx;
            const isAbove = idx > currTierIdx;
            const isBelow = idx < currTierIdx;
            const opacity = isAbove ? '0.38' : isBelow ? '0.55' : '1';
            const scale   = isCurr ? 'scale(1.03)' : 'scale(1)';
            const arrow   = isCurr ? `<span style="margin-left:auto; font-size:0.75rem; color:${t.color}; font-weight:700;">← YOU ARE HERE</span>` : '';
            const minLabel = isAbove ? `(${t.min} TP to unlock)` : '';
            return `<div style="
                display:flex; align-items:center; gap:10px;
                padding:8px 14px; border-radius:12px;
                border:${isCurr ? '2px' : '1px'} solid ${isCurr ? t.color : 'rgba(255,255,255,0.12)'};
                background:${isCurr ? t.glow.replace('0.4','0.15') : isBelow ? 'rgba(255,255,255,0.03)' : 'transparent'};
                opacity:${opacity};
                transform:${scale};
                transition:transform 0.2s;
                position:relative;
            ">
                <span style="font-size:1.3rem;">${t.emoji}</span>
                <div style="flex:1;">
                    <div style="font-weight:${isCurr ? '800' : '600'}; font-size:${isCurr ? '0.95rem' : '0.82rem'}; color:${isCurr ? t.color : isBelow ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.6)'};">${t.name} ${isAbove ? '<span style="font-size:0.72rem; opacity:0.7; margin-left:4px;">' + minLabel + '</span>' : ''}</div>
                    <div style="font-size:0.68rem; color:rgba(255,255,255,0.3); margin-top:1px;">${t.min}–${t.max === Infinity ? '∞' : t.max} TP</div>
                </div>
                ${arrow}
            </div>`;
        }).join('');
    }

    // ── Table & Accuracy Insight ──
    const tbody = document.getElementById('tier-stats-tbody');
    const accuracyInsightEl = document.getElementById('tier-accuracy-insight');
    if (accuracyInsightEl) {
        if (accuracy > 70) {
            accuracyInsightEl.textContent = 'Strong accuracy, attempt more questions';
            accuracyInsightEl.style.color = '#4ade80';
        } else if (accuracy >= 50) {
            accuracyInsightEl.textContent = 'Good, but can improve';
            accuracyInsightEl.style.color = '#fbbf24';
        } else if (total > 0) {
            accuracyInsightEl.textContent = 'High risk, reduce guessing';
            accuracyInsightEl.style.color = '#f87171';
        } else {
            accuracyInsightEl.textContent = 'Attempt questions to see insights';
            accuracyInsightEl.style.color = 'var(--text-faint)';
        }
    }

    if (tbody) {
        const attempted = correct + wrong;
        const basePoints = (correct * 4) + (wrong * -2) + (unattempted * 1);
        const afterMult  = Math.round(basePoints * multiplier);
        const tdS = (val, color) => `<td style="text-align:center; padding:10px 12px; font-weight:700; color:${color || 'var(--text)'};">${val}</td>`;
        const tdL = (val) => `<td style="text-align:left; padding:10px 12px; color:var(--text-muted); font-size:0.78rem;">${val}</td>`;
        tbody.innerHTML = `
            <tr style="background:rgba(255,255,255,0.03);">
                ${tdL('Count (in rolling 400)')}
                ${tdS(correct, '#4ade80')}
                ${tdS(wrong, '#f87171')}
                ${tdS(unattempted, '#94a3b8')}
                ${tdS(basePoints, basePoints >= 0 ? 'var(--teal)' : 'var(--red)')}
                ${tdS(`${accuracy}% <span style="color:#fbbf24;font-size:0.75rem;margin-left:4px;">(×${multiplier})</span>`, accuracy >= 60 ? '#4ade80' : accuracy >= 40 ? '#fbbf24' : '#f87171')}
            </tr>
            <tr>
                ${tdL('Points contribution')}
                ${tdS('+' + (correct*4), '#4ade80')}
                ${tdS((wrong*-2), '#f87171')}
                ${tdS('+' + unattempted, '#94a3b8')}
                ${tdS(basePoints, 'var(--text)')}
                ${tdS('—', 'var(--text-faint)')}
            </tr>`;
    }

    // ── Bonus Cards ──
    const bonusGrid = document.getElementById('tier-bonus-grid');
    if (bonusGrid) {
        const bonusCard = (icon, label, val, color) => `
            <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:12px 14px; display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.4rem;">${icon}</span>
                <div>
                    <div style="font-size:0.78rem; color:var(--text-muted);">${label}</div>
                    <div style="font-size:1rem; font-weight:800; color:${color};">${val}</div>
                </div>
            </div>`;
        const streakTierLabel = streak >= 10 ? '+15% TP' : streak >= 5 ? '+10% TP' : streak >= 3 ? '+5% TP' : 'No bonus yet';
        
        const stats = JSON.parse(localStorage.getItem('upsc_daily_stats') || '{}');
        const todayKey = new Date().toISOString().split('T')[0];
        const activeToday = (stats[todayKey] || 0) > 0;
        
        const streakTitle = streak > 0 
            ? (activeToday ? `🔥 ${streak}-day streak — don't break it!` : `🔥 ${streak}-day streak — complete 1 session to unlock bonus`) 
            : `Start a streak today to unlock TP bonuses!`;
        
        bonusGrid.innerHTML =
            bonusCard('', streakTitle, streakTierLabel, streak >= 3 ? '#f97316' : 'var(--text-muted)') +
            bonusCard('📅', 'Daily Bonus (last 5d)', '+' + dailyBonus + ' TP', dailyBonus > 0 ? '#eab308' : 'var(--text-muted)') +
            bonusCard('⚡', 'Streak TP Bonus', '+' + streakBonus + ' TP', streakBonus > 0 ? '#3b82f6' : 'var(--text-muted)') +
            bonusCard('📋', 'Total Questions Seen', total + ' questions', 'var(--text)');
    }

    // ── Final TP with animated counter ──
    const finalValEl    = document.getElementById('tier-final-tp-val');
    const finalFormEl   = document.getElementById('tier-final-tp-formula');
    const finalTpDiv    = document.getElementById('tier-final-tp');
    if (finalValEl) {
        finalValEl.style.color = tier.color;
        // Animate count up
        let start = 0; const end = tp; const dur = 1200;
        const step = Math.ceil(end / (dur / 16));
        const counter = setInterval(() => {
            start = Math.min(start + step, end);
            finalValEl.textContent = start.toLocaleString();
            if (start >= end) clearInterval(counter);
        }, 16);
    }
    if (finalFormEl) {
        finalFormEl.textContent = `(${rawPoints} raw pts × ${multiplier}) + ${dailyBonus} daily + ${streakBonus} streak = ${tp} TP`;
    }
    const tpFeedbackEl = document.getElementById('tier-final-tp-feedback');
    if (tpFeedbackEl) {
        if (!isNaN(sessionPrevTP) && tp > sessionPrevTP) {
            tpFeedbackEl.textContent = "Great progress 🚀 Keep pushing!";
        } else {
            tpFeedbackEl.textContent = "You're close — 1 strong session can boost you";
        }
    }
    if (finalTpDiv) {
        finalTpDiv.style.borderColor = tier.color + '44';
        finalTpDiv.style.background  = tier.glow.replace('0.4', '0.07');
    }

    // ── Start particle animation on hero canvas ──
    startTierParticles(tier.color);
}

function startTierParticles(color) {
    const canvas = document.getElementById('tier-particle-canvas');
    if (!canvas) return;
    const hero = document.getElementById('tier-hero');
    canvas.width  = hero.offsetWidth;
    canvas.height = hero.offsetHeight;
    const ctx = canvas.getContext('2d');
    const particles = Array.from({ length: 18 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 2.5 + 0.5,
        dx: (Math.random() - 0.5) * 0.4,
        dy: -Math.random() * 0.5 - 0.2,
        o: Math.random() * 0.6 + 0.2
    }));
    let animFrame;
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = color + Math.round(p.o * 255).toString(16).padStart(2,'0');
            ctx.fill();
            p.x += p.dx; p.y += p.dy;
            if (p.y < -5) { p.y = canvas.height + 5; p.x = Math.random() * canvas.width; }
        });
        animFrame = requestAnimationFrame(draw);
    }
    if (window._tierParticleFrame) cancelAnimationFrame(window._tierParticleFrame);
    window._tierParticleFrame = animFrame;
    draw();
}

function showTierChangeModal(isPromotion, fromTier, toTier, tp) {
    const existing = document.getElementById('tier-change-modal');
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = 'tier-change-modal';
    modal.style.cssText = `position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;
        background:rgba(0,0,0,0.85);backdrop-filter:blur(12px);animation:fadeIn 0.3s ease; perspective:1000px;`;
    const accentColor = isPromotion ? toTier.color : fromTier.color;
    const title = isPromotion ? '🎉 Tier Promotion!' : '📉 Tier Demotion';
    const msg   = isPromotion
        ? `You've risen from <strong>${fromTier.emoji} ${fromTier.name}</strong> to <strong style="color:${toTier.color}">${toTier.emoji} ${toTier.name}</strong>!`
        : `You've dropped from <strong>${fromTier.emoji} ${fromTier.name}</strong> to <strong style="color:${toTier.color}">${toTier.emoji} ${toTier.name}</strong>.`;
    const advice = isPromotion
        ? `Keep your accuracy above ${toTier.id === 'dominator' ? '55%' : '50%'} and attempt 30+ questions daily to hold your rank!`
        : `Increase daily question attempts and accuracy to climb back. You need ${toTier.max - tp} more TP for ${fromTier.emoji} ${fromTier.name}.`;
    
    // Better 3D Flip/Scale animation for the modal
    modal.innerHTML = `
        <div style="background:var(--bg-2);border:2px solid ${accentColor}55;border-radius:24px;padding:45px 50px;max-width:480px;width:90%;text-align:center;
            box-shadow:0 0 100px ${accentColor}44, 0 30px 60px rgba(0,0,0,0.8), inset 0 0 20px ${accentColor}22;
            transform-style:preserve-3d; animation:tierModalPop 0.7s cubic-bezier(0.34,1.56,0.64,1) forwards; position:relative; overflow:hidden;">
            
            <div style="position:absolute; inset:0; background:radial-gradient(circle at top, ${accentColor}22, transparent 60%);"></div>
            
            <div style="font-size:6rem; margin-bottom:15px; animation:bounceIn 0.8s cubic-bezier(0.34,1.56,0.64,1) 0.1s both; filter:drop-shadow(0 10px 15px rgba(0,0,0,0.3)); transform-origin:bottom center; position:relative; z-index:2;">${toTier.emoji}</div>
            
            <div style="font-size:1.8rem;font-weight:900;color:${accentColor};margin-bottom:12px; letter-spacing:-0.5px; position:relative; z-index:2; text-shadow:0 2px 10px ${accentColor}66;">${title}</div>
            <div style="font-size:1rem;color:var(--text-muted);margin-bottom:20px;line-height:1.6; position:relative; z-index:2;">${msg}</div>
            <div style="font-size:2.8rem;font-weight:900;color:${accentColor};margin:20px 0; letter-spacing:-1px; position:relative; z-index:2; background:-webkit-linear-gradient(90deg, #fff, ${accentColor}); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">${tp.toLocaleString()} TP</div>
            <div style="font-size:0.85rem;color:var(--text-faint);margin-bottom:32px;line-height:1.6; position:relative; z-index:2; background:rgba(0,0,0,0.3); padding:10px 15px; border-radius:10px;">${advice}</div>
            
            <div style="display:flex;gap:12px;justify-content:center; position:relative; z-index:2;">
                <button onclick="document.getElementById('tier-change-modal').remove()"
                    style="padding:14px 40px;background:linear-gradient(135deg, ${accentColor}, ${accentColor}aa);border:none;border-radius:12px;color:#fff;font-weight:800;font-size:1.05rem;cursor:pointer;box-shadow:0 8px 25px ${accentColor}66; transition:transform 0.2s, box-shadow 0.2s;"
                    onmouseover="this.style.transform='translateY(-2px) scale(1.03)'; this.style.boxShadow='0 12px 30px ${accentColor}88';"
                    onmouseout="this.style.transform='none'; this.style.boxShadow='0 8px 25px ${accentColor}66';">
                    ${isPromotion ? '🚀 Let\'s Go!' : '💪 I\'ll Climb Back'}
                </button>
            </div>
        </div>`;
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    document.body.appendChild(modal);
    
    // Inject keyframes if they don't exist
    if (!document.getElementById('tier-modal-styles')) {
        const s = document.createElement('style');
        s.id = 'tier-modal-styles';
        s.textContent = `
            @keyframes tierModalPop {
                0% { opacity:0; transform:scale(0.8) translateY(30px) rotateX(15deg); }
                100% { opacity:1; transform:scale(1) translateY(0) rotateX(0deg); }
            }
            @keyframes slideUp {
                0% { opacity:1; transform:translateY(0); }
                100% { opacity:0; transform:translateY(-10px); }
            }
        `;
        document.head.appendChild(s);
    }
}

function toggleTierDetails() {
    const el  = document.getElementById('tier-details');
    const btn = document.querySelector('#tier-hero [style*="expand"]');
    if (!el) return;
    const open = el.style.display !== 'none';
    
    if (open) {
        el.style.animation = 'slideUp 0.3s ease forwards';
        setTimeout(() => el.style.display = 'none', 280);
    } else {
        el.style.display = 'block';
        el.style.animation = 'none';
        el.offsetHeight; /* trigger reflow */
        el.style.animation = 'slideDown 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards';
        
        // Stagger inner rows for cooler reveal
        const rows = el.querySelectorAll('tr, .bonus-card');
        rows.forEach((r, i) => {
            r.style.opacity = '0';
            r.style.animation = `scaleIn 0.4s cubic-bezier(0.34,1.56,0.64,1) ${0.1 + i*0.05}s forwards`;
        });
    }
    
    const hint = document.querySelector('#tier-hero div[style*="Click to expand"]');
    if (hint) hint.textContent = open ? 'Click to expand ▼' : 'Click to collapse ▲';
}

window.startFocusSession = function() {
    let todos = _loadTodos();
    let targetSubtopic = null;
    for (let g of todos) {
        const isDone = typeof g === 'object' ? g.done : false;
        const topicName = typeof g === 'string' ? g : (g.topic || 'Unknown Topic');
        const subtopics = typeof g === 'object' && Array.isArray(g.subtopics) ? g.subtopics : [];
        
        if (!isDone) {
            for (let s of subtopics) {
                if (!s.done) {
                    targetSubtopic = s.text;
                    break;
                }
            }
            if (!targetSubtopic && subtopics.length === 0) {
                targetSubtopic = topicName;
            }
            if (targetSubtopic) break;
        }
    }
    if (!targetSubtopic) {
        alert("Your To-Do list is complete! Add more topics first to start a focus session.");
        return;
    }
    
    switchSection('generator', document.getElementById('nav-generator'));
    const input = document.getElementById('gen-topic-input');
    if (input) {
        input.value = targetSubtopic;
        input.focus();
        input.style.transition = 'box-shadow 0.3s ease';
        input.style.boxShadow = "0 0 20px var(--teal), 0 0 10px var(--teal) inset";
        setTimeout(() => input.style.boxShadow = "none", 1500);
    }
}

// ======================== EXAM COUNTDOWN TIMER ========================
function initCountdown() {
    renderCountdown();
    const saved = JSON.parse(localStorage.getItem('upsc_exam_countdown') || '{}');
    const dateInput = document.getElementById('exam-date-input');
    const nameInput = document.getElementById('exam-name-input');
    if (dateInput && saved.date) dateInput.value = saved.date;
    if (nameInput && saved.name) nameInput.value = saved.name;
}

function renderCountdown() {
    const el = document.getElementById('topbar-countdown');
    if (!el) return;
    const saved = JSON.parse(localStorage.getItem('upsc_exam_countdown') || '{}');
    const label = document.querySelector('#exam-countdown-widget .stat-label');
    const examName = saved.name || 'UPSC Exam';
    if (label) label.textContent = '\ud83d\udcc5 ' + examName;
    if (!saved.date) {
        el.textContent = 'Set Date';
        el.style.color = 'var(--text-faint)';
        el.style.animation = '';
        return;
    }
    const now = new Date();
    const examDate = new Date(saved.date);
    examDate.setHours(23, 59, 59, 999); // countdown to end of exam day
    const diffMs = examDate - now;
    if (diffMs < 0) {
        el.textContent = 'Done!';
        el.style.color = 'var(--text-faint)';
        el.style.animation = '';
        return;
    }
    const totalSecs = Math.floor(diffMs / 1000);
    const days  = Math.floor(totalSecs / 86400);
    const hours = Math.floor((totalSecs % 86400) / 3600);
    const mins  = Math.floor((totalSecs % 3600) / 60);
    const secs  = totalSecs % 60;
    const pad = n => String(n).padStart(2, '0');
    el.textContent = days > 0 ? `${days}d ${pad(hours)}:${pad(mins)}:${pad(secs)}` : `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
    el.style.animation = (days === 0 && hours === 0) ? 'timerPulse 1s infinite' : '';
    el.style.color = days === 0 ? 'var(--red)' : days <= 7 ? '#fbbf24' : 'var(--teal)';
}

function toggleCountdownSettings() {
    const popup = document.getElementById('countdown-settings-popup');
    if (!popup) return;
    const isHidden = popup.classList.contains('hidden');
    if (isHidden) {
        popup.classList.remove('hidden');
        setTimeout(() => document.addEventListener('click', closeCountdownOnOutside, { once: true }), 10);
    } else {
        popup.classList.add('hidden');
    }
}

function closeCountdownOnOutside(e) {
    const popup = document.getElementById('countdown-settings-popup');
    const widget = document.getElementById('exam-countdown-widget');
    if (popup && !popup.contains(e.target) && !widget.contains(e.target)) {
        popup.classList.add('hidden');
    }
}

function saveExamCountdown() {
    const dateVal = document.getElementById('exam-date-input').value;
    const nameVal = document.getElementById('exam-name-input').value.trim();
    if (!dateVal) { alert('Please select a valid exam date.'); return; }
    localStorage.setItem('upsc_exam_countdown', JSON.stringify({ date: dateVal, name: nameVal || 'UPSC Exam' }));
    renderCountdown();
    document.getElementById('countdown-settings-popup').classList.add('hidden');
}

// Live tick every second
setInterval(renderCountdown, 1000);

// ======================== STREAK ENGINE ========================
function updateStreak() {
    const today = new Date().toISOString().split('T')[0];
    let streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"lastDate":"","count":0,"longest":0}');
    
    if (streakData.lastDate === today) return; // Already counted today
    
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    if (streakData.lastDate === yesterday) {
        streakData.count++;
    } else {
        streakData.count = 1; // Reset streak
    }
    streakData.lastDate = today;
    streakData.longest = Math.max(streakData.longest, streakData.count);
    localStorage.setItem('upsc_streak', JSON.stringify(streakData));
    
    // Track all active dates for calendar
    let activeDates = JSON.parse(localStorage.getItem('upsc_active_dates') || '[]');
    if (!activeDates.includes(today)) {
        activeDates.push(today);
        localStorage.setItem('upsc_active_dates', JSON.stringify(activeDates));
    }
    
    // Update topbar
    const streakEl = document.getElementById('topbar-streak');
    if (streakEl) streakEl.textContent = streakData.count + 'd streak';
}

// ======================== BADGES ENGINE ========================
const BADGE_DEFINITIONS = [
    { id: 'first_test',    icon: '🎯', title: 'First Step',       desc: 'Completed your first test',              condition: (p, c, t, n) => n >= 1 },
    { id: 'five_tests',    icon: '📚', title: 'Dedicated Learner', desc: 'Completed 5 tests',                      condition: (p, c, t, n) => n >= 5 },
    { id: 'ten_tests',     icon: '🏆', title: 'Test Veteran',      desc: 'Completed 10 tests',                     condition: (p, c, t, n) => n >= 10 },
    { id: 'twenty_five_tests', icon: '🎓', title: 'Seasoned Scholar', desc: 'Completed 25 tests',                 condition: (p, c, t, n) => n >= 25 },
    { id: 'pass_65',       icon: '⭐', title: 'The Excellence award', desc: 'Scored 65% or more in a test',           condition: (p) => p >= 65 },
    { id: 'pass_50',       icon: '🌟', title: 'Good Foundation',   desc: 'Scored 50% or more in a full test',      condition: (p, c, t) => p >= 50 && t === 100 },
    { id: 'pass_50_5x',    icon: '🏅', title: 'Consistent Performer', desc: 'Scored 50% or more in 5 full tests',  condition: (p, c, t) => { 
        if (t !== 100) return false;
        let passed = 0;
        (window.AppState && AppState.testAttempts ? AppState.testAttempts : []).forEach(att => {
            if (att.score >= 50) {
                const qStr = localStorage.getItem('upsc_test_questions_' + att.id);
                if (qStr && qStr.length > 5000) passed++; // Roughly checking it has many questions
                else if (att.test && !att.test.toLowerCase().includes('mini')) passed++;
            }
        });
        return passed >= 5;
    }},
    { id: 'streak_7',      icon: '🔥', title: '7-Day Warrior',     desc: '7-day study streak',                     condition: () => { const s = JSON.parse(localStorage.getItem('upsc_streak') || '{}'); return s.count >= 7; }},
    { id: 'streak_30',     icon: '💎', title: 'Iron Will',         desc: '30-day study streak',                    condition: () => { const s = JSON.parse(localStorage.getItem('upsc_streak') || '{}'); return s.count >= 30; }},
    { id: 'speed_demon',   icon: '⚡', title: 'Speed Demon',       desc: 'Answered all questions in under 60 min', condition: (p, c, t) => t === 100 && c === t },
    { id: 'gen_100',       icon: '🤖', title: 'AI Padawan',        desc: 'Generated 100 questions via AI',         condition: () => { const g = parseInt(localStorage.getItem('upsc_generated_q_count')||'0'); return g >= 100; }},
    { id: 'gen_500',       icon: '🧠', title: 'AI Jedi Master',    desc: 'Generated 500 questions via AI',         condition: () => { const g = parseInt(localStorage.getItem('upsc_generated_q_count')||'0'); return g >= 500; }},
    { id: 'social_butterfly', icon: '🤝', title: 'Social Butterfly', desc: 'Added 3 friends to your network', condition: () => false },
    { id: 'friends_10',    icon: '🌍', title: 'Network Hub',       desc: 'Added 10 friends to your network',       condition: () => false },
    { id: 'paired_warriors', icon: '⚔️', title: 'Paired Warriors', desc: 'Maintained a 7-day paired streak', condition: () => false },
    { id: 'challenger', icon: '🤺', title: 'Challenger', desc: 'Challenged a friend to a mock test', condition: () => false },
    { id: 'early_bird',    icon: '🌅', title: 'Early Bird',     desc: 'Attempted a test before 8 AM', condition: () => false },
    { id: 'night_owl',     icon: '🦉', title: 'Night Owl',      desc: 'Attempted a test after 10 PM', condition: () => false },
    { id: 'comeback_kid',  icon: '📈', title: 'Comeback Kid',   desc: 'Improved score by 20% from previous test', condition: () => false },
    { id: 'premium_unlocked', icon: '👑', title: 'Premium Unlocked', desc: 'Welcome to the PRO Club!', condition: () => AppState.user && AppState.user.isPremium }
];

function evaluateAndAwardBadges(pct, correct, total, testCount) {
    let earnedBadges = JSON.parse(localStorage.getItem('upsc_badges') || '[]');
    const newlyEarned = [];

    BADGE_DEFINITIONS.forEach(badge => {
        if (!earnedBadges.includes(badge.id)) {
            if (badge.condition(pct, correct, total, testCount)) {
                earnedBadges.push(badge.id);
                newlyEarned.push(badge);
            }
        }
    });

    if (newlyEarned.length > 0) {
        localStorage.setItem('upsc_badges', JSON.stringify(earnedBadges));
        // Show badge award animations one by one
        newlyEarned.forEach((badge, i) => {
            setTimeout(() => showBadgeToast(badge), i * 2000);
        });
    }
    
    // Update badge count in sidebar
    updateBadgeDisplay();
}

function showBadgeToast(badge) {
    if (!document.getElementById('badge-award-style')) {
        const style = document.createElement('style');
        style.id = 'badge-award-style';
        style.innerHTML = `
            @keyframes premiumBadgePop {
                0% { transform: scale(0.8) translateY(20px); opacity: 0; filter: blur(5px); }
                100% { transform: scale(1) translateY(0); opacity: 1; filter: blur(0); }
            }
            @keyframes badgeTextFade {
                0% { transform: translateY(10px); opacity: 0; }
                100% { transform: translateY(0); opacity: 1; }
            }
            @keyframes swordSlash {
                0% { transform: scaleX(0) translateX(-50%) rotate(var(--angle)); opacity: 0; }
                50% { opacity: 1; filter: drop-shadow(0 0 15px #fff); }
                100% { transform: scaleX(1) translateX(50%) rotate(var(--angle)); opacity: 0; }
            }
            .slash-line {
                position: absolute; width: 150vw; height: 2px; background: linear-gradient(90deg, transparent, #fff, transparent);
                top: 50%; left: -25%; z-index: 0; transform-origin: center; opacity: 0;
            }
            @keyframes cinematicFlash {
                0%, 100% { opacity: 0; }
                10%, 30%, 50% { opacity: 0.8; background: #fff; }
                20%, 40% { opacity: 0; }
            }
            .lightning-flash {
                position: absolute; inset: 0; z-index: 0; pointer-events: none;
                animation: cinematicFlash 0.4s ease-out forwards;
            }
            @keyframes emberDrift {
                0% { transform: translateY(0) scale(1); opacity: 0; }
                20% { opacity: 1; }
                100% { transform: translateY(-50vh) scale(0); opacity: 0; }
            }
            .ember {
                position: absolute; border-radius: 50%; background: #f97316;
                box-shadow: 0 0 10px #f97316, 0 0 20px #fbbf24;
                animation: emberDrift 2.5s ease-in forwards; bottom: 30%; z-index: 0;
            }
            @keyframes nodePulse {
                0%, 100% { transform: scale(0.5); opacity: 0; }
                50% { transform: scale(1); opacity: 1; box-shadow: 0 0 30px #534AB7; }
            }
            .social-node {
                position: absolute; width: 8px; height: 8px; border-radius: 50%;
                background: #fff; animation: nodePulse 2s ease-in-out infinite alternate; z-index: 0;
            }
            
            /* NEW: Glittering Test Papers */
            @keyframes paperFloat {
                0% { transform: translateY(20vh) rotate(var(--rot)) scale(0.5); opacity: 0; }
                20% { opacity: 1; filter: drop-shadow(0 0 5px rgba(255,255,255,0.8)); }
                80% { opacity: 1; filter: drop-shadow(0 0 15px rgba(255,215,0,0.8)); }
                100% { transform: translateY(-30vh) rotate(calc(var(--rot) + 60deg)) scale(1.2); opacity: 0; }
            }
            .test-paper {
                position: absolute; width: 35px; height: 45px; background: rgba(255,255,255,0.95);
                border-radius: 4px; display: flex; align-items: center; justify-content: center;
                font-weight: 900; font-size: 0.85rem; color: #1e1e2d; z-index: 0;
                box-shadow: inset 0 0 5px rgba(0,0,0,0.1), 0 5px 15px rgba(0,0,0,0.4);
                animation: paperFloat 2.5s ease-out forwards;
            }

            /* NEW: Focus/Revision Rings */
            @keyframes focusRing {
                0% { transform: scale(3) translateZ(0); opacity: 0; border-width: 15px; }
                30% { opacity: 0.8; }
                100% { transform: scale(0.5) translateZ(0); opacity: 0; border-width: 2px; }
            }
            .focus-ring {
                position: absolute; border: 4px solid #1D9E75; border-radius: 50%;
                width: 300px; height: 300px; z-index: 0;
                animation: focusRing 1.2s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;
                box-shadow: 0 0 20px rgba(29,158,117,0.5), inset 0 0 20px rgba(29,158,117,0.5);
            }

            /* NEW: Confetti */
            @keyframes confettiFall {
                0% { transform: translateY(-10vh) rotate(0deg) scale(1); opacity: 1; }
                100% { transform: translateY(110vh) rotate(720deg) scale(0.5); opacity: 0; }
            }
            .confetti {
                position: absolute; width: 10px; height: 20px; top: -10%; z-index: 0;
                animation: confettiFall 2.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
            }

            .achievement-overlay {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: radial-gradient(circle at center, rgba(15,15,20,0.9) 0%, rgba(0,0,0,0.95) 100%);
                display: flex; align-items: center; justify-content: center;
                z-index: 99999; flex-direction: column; color: white; backdrop-filter: blur(8px);
                perspective: 1000px; overflow: hidden;
            }
            .badge-showcase {
                position: relative; width: 180px; height: 180px;
                display: flex; align-items: center; justify-content: center; margin-bottom: 2rem;
                animation: premiumBadgePop 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
                transform-style: preserve-3d;
            }
            .badge-icon-display {
                font-size: 7rem; position: relative; z-index: 2;
                filter: drop-shadow(0 15px 30px rgba(0,0,0,0.8)) drop-shadow(0 0 50px var(--glow-color));
                transform: translateZ(20px);
            }
            .achievement-text { 
                text-align: center; animation: badgeTextFade 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) 0.2s both; 
                position: relative; z-index: 3; 
            }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'achievement-overlay';
    
    // Determine a glow color based on the badge ID context
    const badgeId = (badge.id || '').toLowerCase();
    let glowColor = '#eab308'; // Default gold
    if (badgeId.includes('streak') || badgeId.includes('fire')) glowColor = '#f97316'; // Orange
    else if (badgeId.includes('social') || badgeId.includes('friend')) glowColor = '#534AB7'; // Purple
    else if (badgeId.includes('first') || badgeId.includes('easy')) glowColor = '#1D9E75'; // Teal
    else if (badgeId.includes('hard') || badgeId.includes('legend') || badgeId.includes('demon')) glowColor = '#e24b4a'; // Red

    let customEffectHTML = '';
    
    if (badgeId === 'speed_demon') {
        customEffectHTML = `
            <div class="lightning-flash"></div>
        `;
    } else if (badgeId.includes('social') || badgeId.includes('friend')) {
        customEffectHTML = `
            <div class="social-node" style="top:20%; left:30%; animation-delay:0s;"></div>
            <div class="social-node" style="top:70%; left:20%; animation-delay:0.5s;"></div>
            <div class="social-node" style="top:40%; right:25%; animation-delay:0.2s;"></div>
            <div class="social-node" style="top:80%; right:35%; animation-delay:0.8s;"></div>
        `;
    } else if (badgeId === 'paired_warriors' || badgeId === 'challenger') {
        customEffectHTML = `
            <div class="slash-line" style="--angle: 35deg; animation: swordSlash 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;"></div>
            <div class="slash-line" style="--angle: -35deg; animation: swordSlash 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) 0.3s forwards;"></div>
        `;
    } else if (badgeId.includes('test')) {
        // Glittering test papers flying up
        customEffectHTML = `
            <div class="test-paper" style="left:25%; top:60%; --rot: 15deg; animation-delay:0s;">+1</div>
            <div class="test-paper" style="left:70%; top:65%; --rot: -20deg; animation-delay:0.2s;">85%</div>
            <div class="test-paper" style="left:40%; top:75%; --rot: -5deg; animation-delay:0.4s;">+5</div>
            <div class="test-paper" style="left:60%; top:80%; --rot: 25deg; animation-delay:0.6s;">92%</div>
            <div class="test-paper" style="left:50%; top:85%; --rot: 0deg; animation-delay:0.8s;">+10</div>
        `;
    } else if (badgeId.includes('gen')) {
        // Shrinking concentric rings focusing in on the badge
        customEffectHTML = `
            <div class="focus-ring" style="width:300px; height:300px; animation-delay:0s; border-color:#1D9E75;"></div>
            <div class="focus-ring" style="width:450px; height:450px; animation-delay:0.3s; border-color:#3b82f6;"></div>
            <div class="focus-ring" style="width:600px; height:600px; animation-delay:0.6s; border-color:#8b5cf6;"></div>
        `;
    } else if (badgeId.includes('pass')) {
        // Confetti explosion from the top
        const colors = ['#f97316', '#3b82f6', '#1D9E75', '#eab308', '#e24b4a', '#8b5cf6'];
        for(let i=0; i<40; i++) {
            const left = Math.random() * 100;
            const delay = Math.random() * 0.4;
            const color = colors[Math.floor(Math.random() * colors.length)];
            customEffectHTML += `<div class="confetti" style="left:${left}%; background:${color}; animation-delay:${delay}s;"></div>`;
        }
    } else if (badgeId.includes('streak')) {
        customEffectHTML = `
            <div class="ember" style="left:30%; width:6px; height:6px; animation-duration: 2s; animation-delay: 0s;"></div>
            <div class="ember" style="left:45%; width:4px; height:4px; animation-duration: 2.5s; animation-delay: 0.2s;"></div>
            <div class="ember" style="left:60%; width:8px; height:8px; animation-duration: 1.8s; animation-delay: 0.5s;"></div>
            <div class="ember" style="left:70%; width:5px; height:5px; animation-duration: 2.2s; animation-delay: 0.1s;"></div>
            <div class="ember" style="left:40%; width:7px; height:7px; animation-duration: 2.8s; animation-delay: 0.6s;"></div>
        `;
    }

    overlay.innerHTML = `
        ${customEffectHTML}
        <div class="badge-showcase">
            <div class="badge-icon-display" style="--glow-color: ${glowColor}66;">${badge.icon || '🏅'}</div>
        </div>
        <div class="achievement-text">
            <h1 style="color:${glowColor}; margin:0; font-size:2.8rem; font-weight:800; letter-spacing:1px; text-transform:uppercase;">Achievement Unlocked</h1>
            <h2 style="margin:8px 0 0 0; font-size: 1.8rem; font-weight:500; color:#fff;">${badge.title || badge.name}</h2>
            <p style="color:var(--text-muted); font-size:1rem; max-width:400px; margin:12px auto; line-height:1.6;">${badge.desc}</p>
        </div>
    `;
    document.body.appendChild(overlay);

    setTimeout(() => {
        overlay.style.transition = 'opacity 0.8s ease';
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 800);
    }, 4000);
}

function updateBadgeDisplay() {
    const earnedBadges = JSON.parse(localStorage.getItem('upsc_badges') || '[]');
    const badgeCountEl = document.getElementById('badge-count');
    if (badgeCountEl) badgeCountEl.textContent = earnedBadges.length;

    // Make the shelf label clickable to open profile modal (badges section)
    const shelfLabel = document.querySelector('.badge-shelf-label');
    if (shelfLabel) {
        shelfLabel.style.cursor = 'pointer';
        shelfLabel.title = 'Click to see all badges';
        shelfLabel.onclick = () => openProfileModal();
    }

    // Render UNLOCKED badges in sidebar
    const badgeShelf = document.getElementById('badge-shelf');
    if (badgeShelf) {
        badgeShelf.innerHTML = '';
        BADGE_DEFINITIONS.filter(b => earnedBadges.includes(b.id)).forEach(b => {
            const span = document.createElement('span');
            span.className = 'badge-icon-pill earned';
            span.title = `✅ ${b.title}: ${b.desc}`;
            span.textContent = b.icon;
            span.style.cursor = 'pointer';
            span.onclick = () => showBadgeToast(b);
            badgeShelf.appendChild(span);
        });
        if (earnedBadges.length === 0) {
            badgeShelf.innerHTML = '<span style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">Complete tests to earn badges!</span>';
        }
    }

    // Render LOCKED badges preview with unlock hints
    const badgeShelfLocked = document.getElementById('badge-shelf-locked');
    if (badgeShelfLocked) {
        badgeShelfLocked.innerHTML = '';
        BADGE_DEFINITIONS.filter(b => !earnedBadges.includes(b.id)).slice(0, 6).forEach(b => {
            const span = document.createElement('span');
            span.className = 'badge-icon-pill locked';
            span.title = `🔒 Locked: ${b.title} — ${b.desc}`;
            span.textContent = b.icon;
            span.style.cssText = 'filter: grayscale(1); cursor: default;';
            badgeShelfLocked.appendChild(span);
        });
        const remaining = BADGE_DEFINITIONS.filter(b => !earnedBadges.includes(b.id)).length;
        if (remaining > 6) {
            const more = document.createElement('span');
            more.style.cssText = 'font-size:0.65rem; color:var(--text-muted); align-self:center;';
            more.textContent = `+${remaining - 6} more`;
            badgeShelfLocked.appendChild(more);
        }
    }
}

// ======================== REVIEW ZONES SUMMARY ========================
function getReviewZoneSummary(testId) {
    const reviewData = JSON.parse(localStorage.getItem('upsc_review_' + testId) || '{}');
    const tags = reviewData.tags || {};
    const zones = { doubt: [], guess: [], revise: [] };
    Object.entries(tags).forEach(([idx, tag]) => {
        if (zones[tag]) zones[tag].push(parseInt(idx));
    });
    return zones;
}

// Aggregate all tagged questions across every test attempt
function updateReviewZones() {
    const totals = { doubt: 0, guess: 0, revise: 0 };
    AppState.testAttempts.forEach(attempt => {
        const zones = getReviewZoneSummary(attempt.id);
        totals.doubt  += zones.doubt.length;
        totals.guess  += zones.guess.length;
        totals.revise += zones.revise.length;
    });
    ['doubt', 'guess', 'revise'].forEach(zone => {
        const countEl = document.getElementById('zone-count-' + zone);
        const ctaEl   = document.getElementById('zone-cta-' + zone);
        const label   = zone === 'doubt' ? 'Doubt' : zone === 'guess' ? 'Guess' : 'Revise';
        if (countEl) countEl.textContent = totals[zone] + ' question' + (totals[zone] !== 1 ? 's' : '') + ' tagged ' + label;
        if (ctaEl)   ctaEl.style.display = totals[zone] > 0 ? 'inline' : 'none';
    });
}

// Collect all questions of a given tag type and open the review modal
function startSmartReviewTest() {
    if (!AppState.user || !AppState.user.isPremium) {
        document.getElementById('upsell-message').textContent = 'Auto-Remedial Mistakes Tests are a Premium feature. Upgrade to unlock!';
        document.getElementById('premium-upsell-modal').classList.remove('hidden');
        return;
    }

    let tagged = [];
    const uniqueQuestionsMap = new Map();

    AppState.testAttempts.forEach(attempt => {
        const qs = JSON.parse(localStorage.getItem('upsc_test_questions_' + attempt.id) || '[]');
        const zones = getReviewZoneSummary(attempt.id);
        
        // Combine doubt, guess, and revise
        const allTaggedIndices = [...new Set([...(zones.doubt||[]), ...(zones.guess||[]), ...(zones.revise||[])])];
        
        allTaggedIndices.forEach(idx => {
            if (qs[idx]) {
                const key = qs[idx].question.trim();
                if (!uniqueQuestionsMap.has(key)) {
                    uniqueQuestionsMap.set(key, qs[idx]);
                }
            }
        });
    });

    tagged = Array.from(uniqueQuestionsMap.values());

    if (tagged.length === 0) {
        alert('No questions tagged in your Smart Review Zones yet! Tag questions during test review to populate these zones.');
        return;
    }

    // Shuffle and pick up to 50
    const shuffled = tagged.sort(() => 0.5 - Math.random());
    let selectedQuestions = shuffled.slice(0, 50);

    // Mark them visually
    selectedQuestions = selectedQuestions.map(q => ({...q, question: '[Smart Review] ' + q.question.replace(/^\[.*?\]\s*/, '')}));

    startCBT(selectedQuestions, `Smart Review Test (${selectedQuestions.length} Qs)`);
}

function startRemedialFromZone(tagType) {
    let tagged = [];
    AppState.testAttempts.forEach(attempt => {
        const qs    = JSON.parse(localStorage.getItem('upsc_test_questions_' + attempt.id) || '[]');
        const zones = getReviewZoneSummary(attempt.id);
        zones[tagType].forEach(idx => {
            if (qs[idx]) tagged.push({ ...qs[idx], _testId: attempt.id, _qIdx: idx });
        });
    });
    if (tagged.length === 0) {
        alert('No questions tagged as "' + tagType + '" yet. Tag questions during test review to populate this zone.');
        return;
    }

    const modal = document.getElementById('review-modal');
    const body  = document.getElementById('review-modal-body');
    const title = document.getElementById('modal-title');
    const zoneLabel = tagType === 'doubt' ? '🔴 Weak Zone Practice' : tagType === 'guess' ? '🟡 Risk Zone Practice' : '🔵 Revision Zone Practice';
    title.textContent = zoneLabel + ' — ' + tagged.length + ' questions';
    body.innerHTML = '';

    tagged.forEach((q, i) => {
        const correctKey = (q.correct_option || q.correct || '').toString().toLowerCase().trim();
        const opts = q.options || {};
        const cardId = 'zone-q-' + i;

        const card = document.createElement('div');
        card.id = cardId;
        card.style.cssText = 'border:1px solid var(--border); border-radius:12px; padding:18px; margin-bottom:16px; background:var(--surface);';

        // Build options HTML — each option is a button with a data-key attribute
        const optionsHtml = Object.entries(opts).map(([k, v]) => {
            const kl = k.toLowerCase().trim();
            return `<div data-key="${kl}" class="zone-opt" onclick="window._zoneAttempt('${cardId}','${kl}','${correctKey}')"
                style="display:flex; align-items:flex-start; gap:10px; padding:10px 14px; margin:6px 0; border:1.5px solid var(--border);
                border-radius:10px; cursor:pointer; font-size:0.88rem; background:var(--bg-2); transition:all 0.15s; line-height:1.5;">
                <span style="font-weight:700; flex-shrink:0; width:22px;">${k.toUpperCase()}.</span>
                <span>${v}</span>
            </div>`;
        }).join('');

        // Correct answer display (hidden until attempted)
        const correctText = opts[correctKey] || opts[Object.keys(opts).find(k=>k.toLowerCase()===correctKey)] || correctKey;
        const explanation = q.rationale || q.explanation || '';

        card.innerHTML = `
            <div style="font-size:0.72rem; color:var(--text-faint); font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">${zoneLabel} · Q${i+1}</div>
            <div style="font-size:0.96rem; line-height:1.75; margin-bottom:14px; font-weight:500;">${q.question}</div>
            <div id="${cardId}-opts">${optionsHtml}</div>
            <div id="${cardId}-result" style="display:none; margin-top:12px;">
                <div style="display:flex; align-items:center; gap:8px; padding:10px 14px; background:rgba(29,158,117,0.12); border:1px solid var(--teal); border-radius:8px; font-size:0.85rem; margin-bottom:10px;">
                    <span style="font-size:1.1rem;">✅</span>
                    <span>Correct answer: <strong style="color:var(--teal);">${correctKey.toUpperCase()}. ${correctText}</strong></span>
                </div>
                ${explanation ? `<details open>
                    <summary style="cursor:pointer; font-size:0.8rem; color:var(--primary-light); font-weight:700; padding:6px 0;">✦ Explanation</summary>
                    <div style="margin-top:8px; padding:12px; background:var(--ai-bg); border:1px solid var(--ai-border); border-radius:8px; font-size:0.82rem; color:var(--text-muted); line-height:1.7;">${explanation}</div>
                </details>` : ''}
            </div>
        `;
        body.appendChild(card);
    });

    modal.classList.remove('hidden');
}

// Called when user clicks an option in zone practice
window._zoneAttempt = function(cardId, selectedKey, correctKey) {
    const optsContainer = document.getElementById(cardId + '-opts');
    const resultEl      = document.getElementById(cardId + '-result');
    if (!optsContainer || optsContainer.dataset.answered) return; // prevent re-attempt
    optsContainer.dataset.answered = '1';

    optsContainer.querySelectorAll('.zone-opt').forEach(opt => {
        const k = opt.dataset.key;
        opt.style.cursor = 'default';
        if (k === correctKey) {
            opt.style.background = 'rgba(29,158,117,0.18)';
            opt.style.borderColor = 'var(--teal)';
            opt.style.color = 'var(--teal)';
            opt.querySelector('span:first-child').textContent += ' ✓';
        } else if (k === selectedKey) {
            opt.style.background = 'rgba(239,68,68,0.15)';
            opt.style.borderColor = 'var(--red)';
            opt.style.color = 'var(--red)';
            opt.querySelector('span:first-child').textContent += ' ✗';
        } else {
            opt.style.opacity = '0.45';
        }
    });
    if (resultEl) resultEl.style.display = 'block';
};

// ======================== STREAK CALENDAR ========================
let currentStreakMonthOffset = 0;

function changeStreakMonth(dir) {
    currentStreakMonthOffset += dir;
    renderStreakCalendar();
}

function toggleStreakCalendar() {
    const popup = document.getElementById('streak-calendar-popup');
    if (popup.classList.contains('hidden')) {
        currentStreakMonthOffset = 0;
        renderStreakCalendar();
        popup.classList.remove('hidden');
        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', closeStreakOnOutside, { once: true });
        }, 50);
    } else {
        popup.classList.add('hidden');
    }
}

function closeStreakOnOutside(e) {
    const popup = document.getElementById('streak-calendar-popup');
    if (popup && !popup.contains(e.target) && !e.target.closest('.streak-stat')) {
        popup.classList.add('hidden');
    }
}

function renderStreakCalendar() {
    const streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"lastDate":"","count":0,"longest":0}');
    const activeDates = JSON.parse(localStorage.getItem('upsc_active_dates') || '[]');
    const dailyStats = JSON.parse(localStorage.getItem('upsc_daily_stats') || '{}');

    // Stats row
    const statsEl = document.getElementById('streak-cal-stats');
    if (statsEl) {
        statsEl.innerHTML = `
            <div style="text-align:center;">
                <div style="font-size:1.6rem; font-weight:800; color:#f97316;">${streakData.count}</div>
                <div style="font-size:0.72rem; color:var(--text-muted);">Current Streak</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.6rem; font-weight:800; color:var(--teal);">${streakData.longest}</div>
                <div style="font-size:0.72rem; color:var(--text-muted);">Longest Streak</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.6rem; font-weight:800; color:var(--accent);">${activeDates.length}</div>
                <div style="font-size:0.72rem; color:var(--text-muted);">Days Studied</div>
            </div>
        `;
    }

    // Build current month calendar
    const grid = document.getElementById('streak-calendar-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const today = new Date();
    today.setHours(0,0,0,0);
    const todayStr = today.toISOString().split('T')[0];

    const targetDate = new Date(today.getFullYear(), today.getMonth() + currentStreakMonthOffset, 1);
    const currentMonth = targetDate.getMonth();
    const currentYear = targetDate.getFullYear();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    // Month Title Row
    const titleDiv = document.createElement('div');
    titleDiv.style.cssText = 'grid-column: 1 / -1; display:flex; justify-content:space-between; align-items:center; font-weight: 700; color: var(--text); padding-bottom: 6px; font-size: 0.95rem; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 4px;';
    
    titleDiv.innerHTML = `
        <button onclick="event.stopPropagation(); changeStreakMonth(-1)" style="background:rgba(255,255,255,0.05); border:none; border-radius:4px; color:var(--text); cursor:pointer; padding:4px 12px; font-size:1rem;">&larr;</button>
        <span>${monthNames[currentMonth]} ${currentYear}</span>
        <button onclick="event.stopPropagation(); changeStreakMonth(1)" style="background:rgba(255,255,255,0.05); border:none; border-radius:4px; color:var(--text); cursor:pointer; padding:4px 12px; font-size:1rem;">&rarr;</button>
    `;
    grid.appendChild(titleDiv);

    // Day column header labels
    const dayLabels = ['S','M','T','W','T','F','S'];
    dayLabels.forEach(d => {
        const lbl = document.createElement('div');
        lbl.textContent = d;
        lbl.className = 'streak-cal-day-label';
        grid.appendChild(lbl);
    });

    const firstDay = new Date(currentYear, currentMonth, 1);
    const startOffset = firstDay.getDay(); // 0 for Sunday
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

    const activeSet = new Set(activeDates);

    // Empty cells for days before the 1st
    for (let i = 0; i < startOffset; i++) {
        const emptyCell = document.createElement('div');
        grid.appendChild(emptyCell);
    }

    const examCountdown = JSON.parse(localStorage.getItem('upsc_exam_countdown') || '{}');
    const examDateStr = examCountdown.date || null;
    const examName = examCountdown.name || 'UPSC Exam';

    for (let dayNum = 1; dayNum <= daysInMonth; dayNum++) {
        const d = new Date(currentYear, currentMonth, dayNum);
        const dObj = new Date(d.getTime() - (d.getTimezoneOffset() * 60000));
        const ds = dObj.toISOString().split('T')[0];
        
        const qCount = dailyStats[ds] || 0;
        const isActive = activeSet.has(ds);
        const isToday = ds === todayStr;
        const isFuture = d > today;
        const isExamDay = ds === examDateStr;

        const cell = document.createElement('div');
        cell.className = 'streak-cal-cell';
        cell.title = ds + (qCount > 0 ? ' · ' + qCount + ' questions attempted' : '');

        if (isExamDay) {
            cell.classList.add('streak-future');
            cell.style.cssText += '; background:rgba(249,115,22,0.35); border:2px solid #f97316; box-shadow:0 0 8px rgba(249,115,22,0.5);';
            cell.innerHTML = `<span class="cal-day-num" style="color:#fbbf24;font-size:0.7rem;">${dayNum}</span><span style="font-size:0.42rem;color:#f97316;display:block;line-height:1;margin-top:1px;">🎯</span>`;
            cell.title = examName + ' — ' + ds;
            cell.onclick = (e) => {
                e.stopPropagation();
                const popup = document.createElement('div');
                popup.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#141420;border:1px solid #f97316;border-radius:12px;padding:20px 28px;z-index:9999;text-align:center;box-shadow:0 16px 48px rgba(249,115,22,0.3);';
                popup.innerHTML = `<div style="font-size:2rem;margin-bottom:8px;">🎯</div><div style="font-weight:800;font-size:1.1rem;color:#fbbf24;margin-bottom:4px;">${examName}</div><div style="color:var(--text-muted);font-size:0.85rem;margin-bottom:16px;">${ds}</div><button onclick="this.parentElement.remove()" style="padding:6px 20px;background:#f97316;border:none;border-radius:6px;color:#fff;font-weight:700;cursor:pointer;">OK</button>`;
                document.body.appendChild(popup);
            };
        } else if (isToday) {
            cell.classList.add('streak-today');
            cell.innerHTML = `<span class="cal-day-num">${dayNum}</span>${qCount > 0 ? '<span class="cal-q-count">' + qCount + '</span>' : ''}`;
        } else if (isActive) {
            cell.classList.add('streak-active');
            cell.innerHTML = `<span class="cal-day-num" style="color: #fff;">${dayNum}</span>${qCount > 0 ? '<span class="cal-q-count" style="color:rgba(255,255,255,0.9);">' + qCount + '</span>' : ''}`;
        } else if (isFuture) {
            cell.classList.add('streak-future');
            cell.innerHTML = `<span class="cal-day-num-muted">${dayNum}</span>`;
        } else {
            cell.classList.add('streak-inactive');
            cell.innerHTML = `<span class="cal-day-num-muted">${dayNum}</span>`;
        }

        grid.appendChild(cell);
    }
}

// ======================== PROFILE DROPDOWN ========================
function toggleProfileDropdown() {
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown.classList.contains('hidden')) {
        // Populate user info
        if (AppState.user) {
            const nameEl = document.getElementById('profile-name');
            const emailEl = document.getElementById('profile-email');
            const avatarEl = document.getElementById('profile-avatar');
            if (nameEl) nameEl.textContent = AppState.user.name || 'User';
            if (emailEl) emailEl.textContent = AppState.user.email || '';
            if (avatarEl) avatarEl.textContent = AppState.user.avatar || 'U';
        }

        // Populate badges
        const earnedBadges = JSON.parse(localStorage.getItem('upsc_badges') || '[]');
        const shelf = document.getElementById('profile-badge-shelf');
        if (shelf) {
            shelf.innerHTML = '';
            if (earnedBadges.length === 0) {
                shelf.innerHTML = '<span style="font-size:0.78rem;color:var(--text-faint);">Complete a test to earn badges!</span>';
            } else {
                BADGE_DEFINITIONS.filter(b => earnedBadges.includes(b.id)).forEach(b => {
                    const span = document.createElement('span');
                    span.style.cssText = 'font-size:1.25rem; cursor:default;';
                    span.title = b.title + ': ' + b.desc;
                    span.textContent = b.icon;
                    shelf.appendChild(span);
                });
            }
        }

        dropdown.classList.remove('hidden');
        setTimeout(() => {
            document.addEventListener('click', closeProfileOnOutside, { once: true });
        }, 50);
    } else {
        dropdown.classList.add('hidden');
    }
}

function closeProfileOnOutside(e) {
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown && !dropdown.contains(e.target) && !e.target.closest('.profile-btn-wrapper')) {
        dropdown.classList.add('hidden');
    }
}

function openBadgesModal() {
    const earned = JSON.parse(localStorage.getItem('upsc_badges') || '[]');
    const grid = document.getElementById('badges-modal-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    BADGE_DEFINITIONS.forEach(b => {
        const isEarned = earned.includes(b.id);
        const card = document.createElement('div');
        card.style.cssText = `
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); 
            border-radius: 12px; padding: 1.5rem 1rem; text-align: center;
            ${isEarned ? 'box-shadow: 0 0 15px rgba(186,117,23,0.1); border-color: rgba(186,117,23,0.3); cursor: pointer;' : 'opacity: 0.4; filter: grayscale(1);'}
        `;
        card.innerHTML = `
            <div style="font-size:3rem; margin-bottom:10px; ${isEarned ? 'text-shadow: 0 0 20px rgba(186,117,23,0.5);' : ''}">${b.icon}</div>
            <h4 style="margin:0 0 5px 0; color:var(--text);">${b.title}</h4>
            <div style="font-size:0.75rem; color:var(--text-muted);">${b.desc}</div>
        `;
        if (isEarned) {
            card.onclick = () => {
                document.getElementById('badges-modal').classList.add('hidden');
                showBadgeToast(b);
            };
        }
        grid.appendChild(card);
    });
    
    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileDropdown) profileDropdown.classList.add('hidden');
    document.getElementById('badges-modal').classList.remove('hidden');
}

// ======================== FRIENDS & SOCIAL ========================
function openFriendsModal() {
    // Friends is a full section — just navigate to it
    const navEl = document.getElementById('nav-friends');
    switchSection('friends', navEl);
}

function switchFriendsTab(tabId) {
    // Update active tab buttons
    document.querySelectorAll('.friends-tab').forEach(btn => {
        btn.classList.remove('active');
        btn.style.borderBottomColor = 'transparent';
        btn.style.color = 'var(--text-muted)';
    });
    const activeBtn = document.getElementById('tab-btn-' + tabId);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.borderBottomColor = 'var(--teal)';
        activeBtn.style.color = 'var(--text)';
    }

    const contentDiv = document.getElementById('friends-tab-content');
    
    if (tabId === 'network') {
        contentDiv.innerHTML = `
            <div style="margin-bottom:20px; display:flex; gap:10px;">
                <input type="text" placeholder="Enter Friend's Email or AP ID..." style="flex:1; padding:12px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(0,0,0,0.3); color:white; font-family:'Inter', sans-serif;">
                <button class="ppm-btn" style="width:auto; padding:0 20px; background:var(--teal); color:white; border:none;" onclick="alert('Friend Request Sent!'); showBadgeToast(BADGE_DEFINITIONS.find(b=>b.id==='social_butterfly'))">Add Friend</button>
            </div>
            
            <h4 style="color:var(--text-muted); margin-bottom:15px; text-transform:uppercase; font-size:0.8rem; letter-spacing:1px;">Your Active Network (2)</h4>
            
            <div style="display:flex; flex-direction:column; gap:10px;">
                <!-- Friend 1 -->
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:15px; border-radius:12px; display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:15px;">
                        <div style="width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, #1D9E75, #534AB7); display:flex; align-items:center; justify-content:center; font-weight:700;">RK</div>
                        <div>
                            <div style="font-weight:700;">Rahul Kumar</div>
                            <div style="font-size:0.8rem; color:var(--text-muted);">Last active: 2 hours ago</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:15px; align-items:center;">
                        <div style="text-align:center; cursor:pointer;" onclick="showBadgeToast(BADGE_DEFINITIONS.find(b=>b.id==='paired_warriors'))">
                            <div style="font-size:1.2rem; font-weight:800; color:#f97316;">12🔥</div>
                            <div style="font-size:0.7rem; color:var(--text-muted);">Paired Streak</div>
                        </div>
                        <button class="btn-ghost-sm" style="color:var(--teal); border-color:var(--teal);" onclick="alert('Viewing Stats for Rahul...')">View Stats</button>
                    </div>
                </div>
                <!-- Friend 2 -->
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:15px; border-radius:12px; display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:15px;">
                        <div style="width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, #BA7517, #e24b4a); display:flex; align-items:center; justify-content:center; font-weight:700;">SM</div>
                        <div>
                            <div style="font-weight:700;">Sneha Mishra</div>
                            <div style="font-size:0.8rem; color:var(--text-muted);">Last active: 1 day ago</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:15px; align-items:center;">
                        <div style="text-align:center;">
                            <div style="font-size:1.2rem; font-weight:800; color:rgba(255,255,255,0.2);">0🔥</div>
                            <div style="font-size:0.7rem; color:var(--red);">Streak Broken</div>
                        </div>
                        <button class="btn-ghost-sm" style="color:var(--teal); border-color:var(--teal);" onclick="alert('Viewing Stats for Sneha...')">View Stats</button>
                    </div>
                </div>
            </div>
            
            <div style="margin-top:20px; padding:15px; background:rgba(186,117,23,0.1); border-left:3px solid var(--amber-light); border-radius:6px; font-size:0.85rem; color:var(--text-muted);">
                <strong style="color:var(--amber-light);">Paired Streaks:</strong> A paired streak increases only when BOTH you and your friend complete a test on the same day. If either of you misses a day, the paired streak resets to 0!
            </div>
        `;
    } 
    else if (tabId === 'leaderboard') {
        contentDiv.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h4 style="margin:0; color:var(--text-muted); text-transform:uppercase; font-size:0.8rem; letter-spacing:1px;">Global vs Friends</h4>
                <select style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); color:white; padding:5px 10px; border-radius:6px; font-family:'Inter', sans-serif;">
                    <option>Friends Only</option>
                    <option>Global (Top 100)</option>
                </select>
            </div>
            
            <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:12px; overflow:hidden;">
                <!-- Rank 1 -->
                <div style="display:flex; align-items:center; padding:15px 20px; border-bottom:1px solid rgba(255,255,255,0.05); background:rgba(186,117,23,0.05);">
                    <div style="font-size:1.5rem; font-weight:900; color:var(--gold); width:40px;">#1</div>
                    <div style="flex:1; font-weight:700;">Rahul Kumar</div>
                    <div style="text-align:right;">
                        <div style="color:var(--teal); font-weight:800;">4,250 pts</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">18 Tests Completed</div>
                    </div>
                </div>
                <!-- Rank 2 -->
                <div style="display:flex; align-items:center; padding:15px 20px; border-bottom:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:1.2rem; font-weight:800; color:silver; width:40px;">#2</div>
                    <div style="flex:1; font-weight:700;">You</div>
                    <div style="text-align:right;">
                        <div style="color:var(--teal); font-weight:800;">3,100 pts</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">12 Tests Completed</div>
                    </div>
                </div>
                <!-- Rank 3 -->
                <div style="display:flex; align-items:center; padding:15px 20px;">
                    <div style="font-size:1.1rem; font-weight:700; color:#cd7f32; width:40px;">#3</div>
                    <div style="flex:1; font-weight:700;">Sneha Mishra</div>
                    <div style="text-align:right;">
                        <div style="color:var(--teal); font-weight:800;">1,850 pts</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">8 Tests Completed</div>
                    </div>
                </div>
            </div>
        `;
    }
    else if (tabId === 'challenges') {
        contentDiv.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h4 style="margin:0; color:var(--text-muted); text-transform:uppercase; font-size:0.8rem; letter-spacing:1px;">Active Challenges</h4>
                <button class="btn-ghost-sm" style="background:var(--accent); color:white; border:none;" onclick="alert('Challenge Sent!'); showBadgeToast(BADGE_DEFINITIONS.find(b=>b.id==='challenger'))">+ New Challenge</button>
            </div>
            
            <div style="background:linear-gradient(135deg, rgba(83,74,183,0.1) 0%, rgba(20,20,25,0) 100%); border:1px solid rgba(83,74,183,0.3); padding:20px; border-radius:12px; margin-bottom:15px; position:relative; overflow:hidden;">
                <div style="position:absolute; right:-20px; top:-20px; font-size:6rem; opacity:0.1;">⚔️</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="color:var(--accent); font-size:0.75rem; font-weight:700; text-transform:uppercase; margin-bottom:5px;">Received Challenge</div>
                        <h3 style="margin:0 0 5px 0;">Prototype Paper Showdown</h3>
                        <div style="font-size:0.85rem; color:var(--text-muted);">Challenged by <strong>Rahul Kumar</strong></div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:5px;">Rahul's Score:</div>
                        <div style="font-size:1.5rem; font-weight:900; color:var(--teal);">82.5%</div>
                    </div>
                </div>
                <div style="margin-top:20px; display:flex; gap:10px;">
                    <button class="ppm-btn" style="flex:1; background:var(--teal); color:white; border:none; justify-content:center;" onclick="alert('Starting challenge! Loading Prototype Paper...')">Accept & Attempt</button>
                    <button class="ppm-btn" style="width:auto; padding:0 20px; color:var(--red); border-color:rgba(226,75,74,0.3); background:rgba(226,75,74,0.1); justify-content:center;" onclick="alert('Challenge declined.')">Decline</button>
                </div>
            </div>
        `;
    }
}

// ======================== SUBTOPIC SELECTOR MODAL ========================
let _pendingSubtopics = [];  // {text, selected}
let _pendingSubject = '';

window.addDiagnosisToPlan = function(subject) {
    const el = document.getElementById('ai-diagnosis-content');
    if (!el) return;
    const text = el.innerText;
    let topics = [];
    text.split('\n').forEach(line => {
        let t = line.trim();
        if (t.startsWith('-') || t.startsWith('*')) {
            const clean = t.replace(/^[-*]\s*/, '').replace(/\*\*/g, '').split(':')[0].trim();
            if (clean) topics.push(clean);
        }
    });
    if (topics.length === 0) topics.push(subject + ' Revision');

    _pendingSubject = subject;
    _pendingSubtopics = topics.map(t => ({ text: t, selected: true }));

    // Populate checklist
    const checklist = document.getElementById('subtopic-checklist');
    document.getElementById('subtopic-modal-title').textContent = 'Add Sub-topics for: ' + subject;
    checklist.innerHTML = '';
    _pendingSubtopics.forEach((item, idx) => {
        const row = document.createElement('label');
        row.style.cssText = 'display:flex; align-items:center; gap:12px; padding:10px 14px; border:1px solid var(--border); border-radius:8px; cursor:pointer; background:var(--surface); font-size:0.88rem;';
        row.innerHTML = `
            <input type="checkbox" checked data-idx="${idx}" style="width:16px;height:16px;cursor:pointer;accent-color:var(--teal);" onchange="_pendingSubtopics[${idx}].selected=this.checked">
            <span>${item.text}</span>
        `;
        checklist.appendChild(row);
    });

    document.getElementById('subtopic-selector-modal').classList.remove('hidden');
}


function switchProfTab(tab) {
    const el = (id) => document.getElementById(id);
    if (tab === 'overview') {
        el('prof-content-overview').classList.remove('hidden');
        el('prof-content-friends').classList.add('hidden');
        el('prof-tab-overview').style.borderBottom = '2px solid var(--gold)';
        el('prof-tab-overview').style.color = 'var(--gold)';
        el('prof-tab-friends').style.borderBottom = 'none';
        el('prof-tab-friends').style.color = 'var(--text-muted)';
    } else {
        el('prof-content-overview').classList.add('hidden');
        el('prof-content-friends').classList.remove('hidden');
        el('prof-tab-friends').style.borderBottom = '2px solid var(--gold)';
        el('prof-tab-friends').style.color = 'var(--gold)';
        el('prof-tab-overview').style.borderBottom = 'none';
        el('prof-tab-overview').style.color = 'var(--text-muted)';
    }
}

function openProfileModal(otherUser = null) {
    const u = otherUser || AppState.user;
    if (!u) return;
    
    if (typeof switchSection === 'function') switchSection('profile');
    
    if (typeof switchProfTab === 'function') switchProfTab('overview');

    const isSelf = !otherUser;
    
    const el = (id) => document.getElementById(id);

    const actionsDiv = el('modal-profile-actions');
    if (actionsDiv) actionsDiv.style.display = isSelf ? 'none' : 'block';

    const coverBg = el('modal-cover-bg');
    const dpEl = el('modal-dp');
    if (coverBg) {
        coverBg.style.cursor = isSelf ? 'pointer' : 'default';
        coverBg.onclick = isSelf ? () => el('modal-cover-upload').click() : null;
        const hint = coverBg.querySelector('span');
        if (hint) hint.style.display = isSelf ? 'block' : 'none';
    }
    if (dpEl) {
        dpEl.style.cursor = isSelf ? 'pointer' : 'default';
        dpEl.onclick = isSelf ? () => el('modal-dp-upload').click() : null;
    }

    // Populate name, username, etc.
    const username = '@' + (u.email ? u.email.split('@')[0].toLowerCase().replace(/[^a-z0-9_]/g, '_') : u.name.toLowerCase().replace(/\s+/g, '_'));
    if (el('modal-profile-name')) el('modal-profile-name').textContent = u.name;
    if (el('modal-profile-username')) el('modal-profile-username').textContent = username;
    if (el('modal-dp-text')) el('modal-dp-text').textContent = u.avatar || u.name.slice(0,2).toUpperCase();
    
    // Member since
    if (el('modal-profile-member-since')) {
        el('modal-profile-member-since').textContent = isSelf ? 'Member since Jan 2026' : 'Member since Oct 2025';
    }

    // Stats
    const history = JSON.parse(localStorage.getItem('upsc_prototypeAttempts_v1') || '[]');
    if (el('modal-stat-tests')) el('modal-stat-tests').textContent = isSelf ? history.length : Math.floor(Math.random()*40)+10;
    
    const streak = JSON.parse(localStorage.getItem('upsc_streak') || '{"count":0}');
    const cStreak = isSelf ? streak.count : (u.streak || Math.floor(Math.random()*15));
    if (el('modal-stat-streak')) el('modal-stat-streak').textContent = cStreak + '🔥';
    
    const longest = isSelf ? (streak.longest || streak.count) : (cStreak + Math.floor(Math.random()*5));
    if (el('modal-stat-longest')) el('modal-stat-longest').textContent = longest;

    // Friends list
    const friends = JSON.parse(localStorage.getItem('upsc_friends') || '[{"name":"Rahul Kumar","username":"rahul_kumar","streak":7,"avatar":"RK"}]');
    if (el('modal-stat-friends')) el('modal-stat-friends').textContent = isSelf ? friends.length : Math.floor(Math.random()*20);
    
    const friendsContainer = el('modal-friends-list');
    if (friendsContainer) {
        friendsContainer.innerHTML = friends.map(f => `
            <div style="display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg-2);border:1px solid var(--border);border-radius:10px; cursor:pointer; transition:background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='var(--bg-2)'" onclick='openProfileModal(${JSON.stringify(f).replace(/'/g, "&#39;")})'>
                <div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#1D9E75,#534AB7);display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:0.9rem;flex-shrink:0;">${f.avatar || f.name.slice(0,2).toUpperCase()}</div>
                <div style="flex:1;">
                    <div style="font-weight:700;color:var(--text);">${f.name}</div>
                    <div style="font-size:0.75rem;color:var(--teal);font-weight:600;">@${(f.username || f.name.toLowerCase().replace(/\s+/g,'_'))}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1rem;font-weight:800;color:#f97316;">${f.streak || 0}🔥</div>
                    <div style="font-size:0.65rem;color:var(--text-muted);">Streak</div>
                </div>
            </div>
        `).join('') || '<p style="color:var(--text-muted);font-size:0.85rem;">No friends yet. Add friends from the Friends section!</p>';
    }

    // Badges in profile modal
    const earnedBadges = isSelf ? JSON.parse(localStorage.getItem('upsc_badges') || '[]') : ['first_test', 'streak_7', 'scholar'];
    const badgesGrid = el('modal-badges-grid');
    if (badgesGrid) {
        badgesGrid.innerHTML = '';
        BADGE_DEFINITIONS.forEach(b => {
            const isEarned = earnedBadges.includes(b.id);
            const card = document.createElement('div');
            card.style.cssText = `padding:10px;background:var(--bg-2);border:1px solid ${isEarned ? 'rgba(212,175,55,0.4)' : 'var(--border)'};border-radius:12px;text-align:center;width:80px;opacity:${isEarned ? '1' : '0.4'};cursor:default;`;
            card.title = isEarned ? `✅ ${b.title}: ${b.desc}` : `🔒 ${b.title}: ${b.desc}`;
            card.innerHTML = `<div style="font-size:1.5rem;">${b.icon}</div><div style="font-size:0.6rem;color:var(--text-muted);margin-top:4px;font-weight:600;">${b.title}</div>`;
            if (!isEarned) {
                const lockIcon = document.createElement('div');
                lockIcon.style.cssText = 'font-size:0.6rem;color:var(--text-muted);margin-top:2px;';
                lockIcon.textContent = '🔒 ' + b.desc;
                card.appendChild(lockIcon);
            }
            badgesGrid.appendChild(card);
        });
    }

    // Custom images
    if (isSelf) {
        const coverData = localStorage.getItem('upsc_cover_image');
        if (coverData) el('modal-cover-bg').style.backgroundImage = `url(${coverData})`;
        const dpData = localStorage.getItem('upsc_dp_image');
        if (dpData) {
            el('modal-dp').style.backgroundImage = `url(${dpData})`;
            if (el('modal-dp-text')) el('modal-dp-text').style.display = 'none';
        } else {
            el('modal-dp').style.backgroundImage = '';
            if (el('modal-dp-text')) el('modal-dp-text').style.display = '';
        }
    } else {
        el('modal-cover-bg').style.backgroundImage = '';
        el('modal-dp').style.backgroundImage = '';
        if (el('modal-dp-text')) el('modal-dp-text').style.display = '';
    }
}

function closeProfileModal() {
    const overlay = document.getElementById('profile-modal-overlay');
    if (overlay) overlay.classList.add('hidden');
}


function closeSubtopicModal() {
    document.getElementById('subtopic-selector-modal').classList.add('hidden');
}

function confirmSubtopicSelection() {
    const selected = _pendingSubtopics.filter(t => t.selected).map(t => t.text);
    if (selected.length === 0) { closeSubtopicModal(); return; }

    let todos = _loadTodos();
    // Find existing parent group for this subject or create one
    let groupIdx = todos.findIndex(g => (g.topic || g) === _pendingSubject);
    if (groupIdx === -1) {
        todos.push({ topic: _pendingSubject, notes: '', subtopics: [], collapsed: false });
        groupIdx = todos.length - 1;
    }
    if (typeof todos[groupIdx] === 'string') {
        todos[groupIdx] = { topic: todos[groupIdx], subtopics: [], collapsed: false };
    }
    if (!todos[groupIdx].subtopics) todos[groupIdx].subtopics = [];
    selected.forEach(text => {
        todos[groupIdx].subtopics.push({ text, done: false });
    });
    _saveTodos(todos);
    renderTodos(todos);
    closeSubtopicModal();
}

window.reviewMistakes = function(subject) {
    const wrongQs = getWrongQuestionsForSubject(subject);
    const el = document.getElementById('ai-diagnosis-content');
    if (!el) return;
    if (document.getElementById('ai-mistakes-list')) return;

    let html = `<div id="ai-mistakes-list" style="margin-top:15px; padding-top:15px; border-top:1px solid rgba(255,255,255,0.1);">
        <strong style="color:var(--red); font-size:0.88rem;">📋 Your Recent Mistakes in ${subject}:</strong>`;

    if (wrongQs.length === 0) {
        html += '<p style="color:var(--text-muted); margin-top:10px; font-size:0.85rem;">No recent wrong questions found for this subject.</p>';
    } else {
        wrongQs.forEach((item, idx) => {
            const optKeys = Object.keys(item.options || {});
            const correctKey = item.correct ? item.correct.toString().toLowerCase() : '';
            const userKey = item.userAnswer ? item.userAnswer.toString().toLowerCase() : null;
            const correctText = item.options[correctKey] || item.options[item.correct] || item.correct || '—';
            const userText = userKey ? (item.options[userKey] || item.userAnswer) : 'Not Attempted';

            html += `
            <div style="margin-top:12px; border:1px solid var(--border); border-radius:8px; overflow:hidden; font-size:0.82rem;">
                <div style="padding:10px 14px; background:var(--bg-2); cursor:pointer; display:flex; justify-content:space-between; align-items:flex-start; gap:10px;" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'; this.querySelector('.expand-icon').textContent=this.nextElementSibling.style.display==='none'?'▶':'▼';">
                    <span style="flex:1; font-weight:600; line-height:1.5; color:var(--text);">${idx + 1}. ${item.question}</span>
                    <span class="expand-icon" style="color:var(--text-faint); flex-shrink:0; font-size:0.75rem;">▶</span>
                </div>
                <div style="display:none; padding:12px 14px; background:var(--surface);">
                    <div style="display:flex; gap:20px; margin-bottom:10px; flex-wrap:wrap;">
                        <span style="color:var(--red); font-size:0.8rem;">❌ Your Answer: <strong>${userText}</strong></span>
                        <span style="color:var(--teal); font-size:0.8rem;">✅ Correct Answer: <strong>${correctText}</strong></span>
                    </div>
                    ${item.rationale ? `<div style="background:var(--ai-bg); border:1px solid var(--ai-border); border-radius:6px; padding:10px; color:var(--text-muted); line-height:1.6; font-size:0.8rem;"><strong style="color:var(--primary-light); display:block; margin-bottom:4px;">✦ AI Explanation</strong>${item.rationale}</div>` : ''}
                </div>
            </div>`;
        });
    }

    html += '</div>';
    el.innerHTML += html;
}

function handleImageUpload(input, targetId, isCover) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            const dataUrl = e.target.result;
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.style.backgroundImage = `url(${dataUrl})`;
            
            if (isCover) {
                localStorage.setItem('upsc_cover_image', dataUrl);
            } else {
                localStorage.setItem('upsc_dp_image', dataUrl);
                document.getElementById('profile-avatar-text').style.display = 'none';
                document.getElementById('topbar-user-badge').style.backgroundImage = `url(${dataUrl})`;
                document.getElementById('topbar-user-badge').style.backgroundSize = 'cover';
                document.getElementById('topbar-user-badge').textContent = '';
                const sidebarAv = document.getElementById('user-avatar');
                if (sidebarAv) {
                    sidebarAv.style.backgroundImage = `url(${dataUrl})`;
                    sidebarAv.style.backgroundSize = 'cover';
                    document.getElementById('user-avatar-text').style.display = 'none';
                }
            }
        };
        reader.readAsDataURL(file);
    }
}

// ======================== PREMIUM FEATURES ========================

function upgradeToPremium() {
    AppState.user.isPremium = true;
    localStorage.setItem('upsc_user', JSON.stringify(AppState.user));
    document.getElementById('premium-upsell-modal').classList.add('hidden');
    updateUserUI();
    
    const earned = JSON.parse(localStorage.getItem('upsc_badges') || '[]');
    if (!earned.includes('premium_unlocked')) {
        earned.push('premium_unlocked');
        localStorage.setItem('upsc_badges', JSON.stringify(earned));
    }
    
    showBadgeToast({id: 'premium_unlocked', icon: '👑', title: 'Premium Unlocked', desc: 'Welcome to the PRO Club!'});
    
    const btn = document.querySelector('.user-avatar');
    if(btn) {
        for(let i=0; i<30; i++) {
            const el = document.createElement('div');
            el.innerHTML = '✨';
            el.style.position = 'absolute';
            el.style.left = btn.getBoundingClientRect().left + 'px';
            el.style.top = btn.getBoundingClientRect().top + 'px';
            el.style.fontSize = Math.random() * 20 + 10 + 'px';
            el.style.pointerEvents = 'none';
            el.style.transition = 'all 1s cubic-bezier(0.1, 0.8, 0.3, 1)';
            document.body.appendChild(el);
            setTimeout(() => {
                el.style.transform = `translate(${(Math.random()-0.5)*200}px, ${(Math.random()-0.5)*200 - 100}px) rotate(${Math.random()*360}deg)`;
                el.style.opacity = '0';
            }, 50);
            setTimeout(() => el.remove(), 1000);
        }
    }
}

function switchGenTab(tab) {
    const topicBtn = document.getElementById('gen-tab-topic');
    const notesBtn = document.getElementById('gen-tab-notes');

    if(topicBtn) {
        topicBtn.classList.toggle('active', tab === 'topic');
        topicBtn.style.borderBottomColor = tab === 'topic' ? 'var(--teal)' : 'transparent';
        topicBtn.style.color = tab === 'topic' ? 'var(--text)' : 'var(--text-muted)';
    }
    
    if(notesBtn) {
        notesBtn.classList.toggle('active', tab === 'notes');
        notesBtn.style.borderBottomColor = tab === 'notes' ? 'var(--teal)' : 'transparent';
        notesBtn.style.color = tab === 'notes' ? 'var(--text)' : 'var(--text-muted)';
    }
    
    if (tab === 'topic') {
        document.getElementById('gen-view-topic').classList.remove('hidden');
        document.getElementById('gen-view-notes').classList.add('hidden');
        document.getElementById('topic-input-wrapper').style.display = 'block';
    } else {
        document.getElementById('gen-view-topic').classList.add('hidden');
        document.getElementById('gen-view-notes').classList.remove('hidden');
        document.getElementById('topic-input-wrapper').style.display = 'none';
    }
}

function triggerNotesUpload() {
    if (!AppState.user || !AppState.user.isPremium) {
        document.getElementById('upsell-message').textContent = 'Uploading custom PDFs and generating personalized tests is a Premium feature. Upgrade to unlock!';
        document.getElementById('premium-upsell-modal').classList.remove('hidden');
        return;
    }
    document.getElementById('notes-upload-input').click();
}

function handleNotesUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        document.getElementById('gen-topic-input').value = `Notes: ${file.name}`;
        switchGenTab('topic');
        generateMCQs();
    }
}

let pendingPdfTestId = null;

function exportTestPDF(testId = null) {
    if (!AppState.user || !AppState.user.isPremium) {
        document.getElementById('upsell-message').textContent = 'Exporting tests and detailed solutions as PDFs is a Premium feature. Upgrade to unlock!';
        document.getElementById('premium-upsell-modal').classList.remove('hidden');
        return;
    }
    pendingPdfTestId = testId;
    document.getElementById('pdf-download-modal').classList.remove('hidden');
}

function executePDFDownload() {
    document.getElementById('pdf-download-modal').classList.add('hidden');

    // Ensure Vision IAS questions are available for PDF even if page was refreshed
    if ((pendingPdfTestId == 4 || pendingPdfTestId == 3) && typeof VISION_TEST_QUESTIONS !== 'undefined') {
        if (!localStorage.getItem('upsc_test_questions_' + pendingPdfTestId)) {
            localStorage.setItem('upsc_test_questions_' + pendingPdfTestId, JSON.stringify(VISION_TEST_QUESTIONS));
        }
    }
    
    let contentDiv = document.createElement('div');
    contentDiv.style.padding = '40px';
    contentDiv.style.fontFamily = 'sans-serif';
    contentDiv.style.color = '#000';
    contentDiv.style.background = '#fff';
    
    let contentHtml = `
        <h1 style="text-align:center; color:#1D9E75; border-bottom:2px solid #ccc; padding-bottom:10px;">UPSC Mock Test Revision</h1>
    `;
    
    if (pendingPdfTestId) {
        const qStr = localStorage.getItem('upsc_test_questions_' + pendingPdfTestId);
        if (qStr) {
            const questions = JSON.parse(qStr);
            contentHtml += `<p style="font-weight:bold; margin-bottom:30px;">Total Questions: ${questions.length}</p>`;
            
            const incQ = document.getElementById('pdf-include-questions').checked;
            const incA = document.getElementById('pdf-include-answers').checked;
            const incE = document.getElementById('pdf-include-explanations').checked;
            
            questions.forEach((q, i) => {
                if (incQ) {
                    contentHtml += `<div style="margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 20px; page-break-inside: avoid;">`;
                    contentHtml += `<div style="font-weight: bold; margin-bottom: 12px; font-size:1.1rem;">Q${i+1}. ${q.question}</div>`;
                    
                    if (q.options) {
                        if (Array.isArray(q.options)) {
                            q.options.forEach((opt, oi) => {
                                contentHtml += `<div style="margin-bottom: 6px; padding-left:15px;">${String.fromCharCode(65+oi)}. ${opt}</div>`;
                            });
                        } else if (typeof q.options === 'object') {
                            Object.entries(q.options).forEach(([key, val]) => {
                                contentHtml += `<div style="margin-bottom: 6px; padding-left:15px;">${key.toUpperCase()}. ${val}</div>`;
                            });
                        }
                    }

                    // Show correct answer and user's attempt status if review data exists
                    let userAnsHtml = "";
                    let isCor = false;
                    let isSkip = false;
                    const reviewDataStr = localStorage.getItem('upsc_review_' + pendingPdfTestId);
                    const stateStr = localStorage.getItem('upsc_test_state_' + pendingPdfTestId);
                    if (reviewDataStr && stateStr) {
                        const reviewData = JSON.parse(reviewDataStr);
                        const stateData = JSON.parse(stateStr);
                        const userAns = stateData[i] ? stateData[i].selected : null;
                        
                        const correctVal = q.correct_option || q.correct;
                        if (!userAns) isSkip = true;
                        else if (userAns === correctVal) isCor = true;
                        
                        if (isSkip) {
                            userAnsHtml = `<span style="color: #666; font-weight: bold;">[Unattempted]</span>`;
                        } else if (isCor) {
                            userAnsHtml = `<span style="color: #1D9E75; font-weight: bold;">[Your Attempt: ${userAns.toUpperCase()} - Correct ??]</span>`;
                        } else {
                            userAnsHtml = `<span style="color: #e24b4a; font-weight: bold;">[Your Attempt: ${userAns.toUpperCase()} - Wrong ?]</span>`;
                        }
                    }

                    if (incA && (q.correct_option || q.correct)) {
                        const correctAns = (q.correct_option || q.correct).toUpperCase();
                        contentHtml += `<div style="color: #1D9E75; font-weight: bold; margin-top: 15px; padding: 10px; background: rgba(29,158,117,0.1); border-radius: 5px; display:flex; justify-content:space-between;">
                            <span>Correct Answer: ${correctAns}</span>
                            ${userAnsHtml}
                        </div>`;
                    }
                    if (incE && (q.rationale || q.explanation)) {
                        const explanation = q.rationale || q.explanation;
                        contentHtml += `<div style="font-style: italic; color: #444; margin-top: 10px; padding: 10px; background: #f9f9f9; border-left: 3px solid #ccc;"><strong>Explanation:</strong><br/>${explanation}</div>`;
                    }
                    contentHtml += `</div>`;
                }
            });
        } else {
            contentHtml += `<h2>No detailed test data found for offline export.</h2>`;
        }
    } else {
        contentHtml += `<h2>General test content (Demo).</h2>`;
    }
    
    contentDiv.innerHTML = contentHtml;
    
    const opt = {
        margin:       0.5,
        filename:     'UPSC_Test_Revision.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2 },
        jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
    };
    
    if (typeof html2pdf !== 'undefined') {
        html2pdf().set(opt).from(contentDiv).save();
    } else {
        alert("PDF generator library not loaded. Falling back to basic browser print.");
        document.body.appendChild(contentDiv);
        window.print();
        document.body.removeChild(contentDiv);
    }
}

let availableRemedialQuestions = [];

function openRemedialConfigModal() {
    if (!AppState.user || !AppState.user.isPremium) {
        document.getElementById('upsell-message').textContent = 'Auto-Remedial Mistakes Tests are a Premium feature. Upgrade to unlock!';
        document.getElementById('premium-upsell-modal').classList.remove('hidden');
        return;
    }
    
    document.getElementById('remedial-config-modal').classList.remove('hidden');
    // Default to last 3 papers and reset count
    document.getElementById('remedial-tests-count').value = '3';
    document.getElementById('remedial-q-count').value = '10';
    updateRemedialMaxQuestions();
}

function updateRemedialMaxQuestions() {
    const testsToConsider = document.getElementById('remedial-tests-count').value;
    const allHistory = JSON.parse(localStorage.getItem('upsc_prototypeAttempts_v1') || '[]');
    const history = allHistory.filter(a => !(a.test && a.test.includes('Remedial')) && !(a.topic && a.topic.includes('Remedial')));
    
    let limit = history.length;
    if (testsToConsider !== 'all') {
        limit = Math.min(history.length, parseInt(testsToConsider));
    }
    
    // Gather unique wrong and unattempted questions from the last N tests
    const uniqueQuestionsMap = new Map();
    const consideredTestNames = [];
    
    for (let i = 0; i < limit; i++) {
        const attempt = history[i];
        if (!attempt.id) continue;
        
        consideredTestNames.push(attempt.test || attempt.topic || 'Mock Test');
        
        const reviewDataRaw = localStorage.getItem('upsc_review_' + attempt.id);
        const questionsRaw = localStorage.getItem('upsc_test_questions_' + attempt.id);
        
        if (reviewDataRaw && questionsRaw) {
            const reviewData = JSON.parse(reviewDataRaw);
            const questions = JSON.parse(questionsRaw);
            
            const indices = [...(reviewData.wrongIndices || []), ...(reviewData.unattemptedIndices || [])];
            
            indices.forEach(idx => {
                if (questions[idx]) {
                    // Use the question text as a unique key to prevent duplicates
                    const key = questions[idx].question.trim();
                    if (!uniqueQuestionsMap.has(key)) {
                        uniqueQuestionsMap.set(key, questions[idx]);
                    }
                }
            });
        }
    }
    
    availableRemedialQuestions = Array.from(uniqueQuestionsMap.values());
    const maxAvailable = availableRemedialQuestions.length;
    
    document.getElementById('remedial-max-q-label').textContent = `Max: ${maxAvailable} available`;

    const textEl = document.getElementById('remedial-considered-tests');
    if (textEl) {
        if (consideredTestNames.length === 0) {
            textEl.textContent = 'No past tests available.';
        } else {
            textEl.textContent = 'Considering: ' + consideredTestNames.join(', ');
        }
    }
    
    // Automatically cap the requested questions to the maximum available (up to 50)
    let qInput = document.getElementById('remedial-q-count');
    if (parseInt(qInput.value) > maxAvailable) {
        qInput.value = maxAvailable;
    }
    // Hard cap at 50 for generated test
    if (parseInt(qInput.value) > 50) {
        qInput.value = 50;
    }
    
    validateRemedialQuestions();
}

function validateRemedialQuestions() {
    const qInput = document.getElementById('remedial-q-count');
    const warning = document.getElementById('remedial-warning');
    const maxAvailable = availableRemedialQuestions.length;
    let val = parseInt(qInput.value);
    
    if (isNaN(val) || val <= 0) val = 1;
    
    if (val > maxAvailable) {
        qInput.value = maxAvailable;
        warning.style.display = 'block';
    } else {
        warning.style.display = 'none';
        if (val > 50) qInput.value = 50; // hard cap
    }
}

function startSingleRemedialTest(id, testName) {
    if (!AppState.user || !AppState.user.isPremium) {
        document.getElementById('upsell-message').textContent = 'Auto-Remedial Mistakes Tests are a Premium feature. Upgrade to unlock!';
        document.getElementById('premium-upsell-modal').classList.remove('hidden');
        return;
    }
    
    const reviewDataRaw = localStorage.getItem('upsc_review_' + id);
    let questionsRaw    = localStorage.getItem('upsc_test_questions_' + id);

    // Fallback: if questions not in localStorage but this is the Vision IAS paper (id==3 or 4, or testName contains Vision IAS)
    if (!questionsRaw && (id == 4 || id == 3 || (testName && testName.includes('Vision IAS'))) && typeof VISION_TEST_QUESTIONS !== 'undefined') {
        questionsRaw = JSON.stringify(VISION_TEST_QUESTIONS);
        localStorage.setItem('upsc_test_questions_' + id, questionsRaw);
    }

    if (!reviewDataRaw || !questionsRaw) {
        alert('Test data not found. Please re-attempt the test once to rebuild the data.');
        return;
    }
    
    const reviewData = JSON.parse(reviewDataRaw);
    const questions  = JSON.parse(questionsRaw);
    const indices    = [...(reviewData.wrongIndices || []), ...(reviewData.unattemptedIndices || [])];
    
    if (indices.length === 0) {
        alert('You had a perfect score! No mistakes to review.');
        return;
    }
    
    const remedialQuestions = indices.map(idx => questions[idx]).filter(Boolean);
    
    document.getElementById('cbt-overlay').classList.remove('hidden');
    if (typeof switchSection === 'function') switchSection('tests');
    startCBT({
        id: 'remedial_' + Date.now(),
        title: 'Auto-Remedial: ' + testName,
        subject: 'Remedial',
        duration: remedialQuestions.length * 2,
        questions: remedialQuestions
    });
}

function startCustomRemedialTest() {
    let count = parseInt(document.getElementById('remedial-q-count').value);
    if (isNaN(count) || count <= 0) return;
    if (count > availableRemedialQuestions.length) count = availableRemedialQuestions.length;
    
    if (count === 0) {
        alert("You don't have any wrong or unattempted questions from the selected tests!");
        return;
    }
    
    // Shuffle and pick the requested number of questions
    const shuffled = availableRemedialQuestions.sort(() => 0.5 - Math.random());
    let selectedQuestions = shuffled.slice(0, count);
    
    // Mark them visually as review questions
    selectedQuestions = selectedQuestions.map(q => ({...q, question: '[Review] ' + q.question.replace(/^\[Review\]\s*/, '')}));
    
    const testsConsidered = document.getElementById('remedial-tests-count').value;
    const topicStr = testsConsidered === 'all' ? 'All Past Tests' : `Last ${testsConsidered} Papers`;
    
    const remedialTest = {
        id: 'remedial-custom-' + Date.now(),
        topic: `Remedial Mistake Test: ${topicStr}`,
        count: count,
        paper_type: 'Remedial',
        questions: selectedQuestions
    };
    
    document.getElementById('remedial-config-modal').classList.add('hidden');
    startCBT(remedialTest.questions, remedialTest.topic);
}

function startCBT(questions, title) {
    if (!questions || questions.length === 0) return;
    
    // Switch to tests section so the nested cbt-overlay is visible!
    switchSection('tests', document.querySelector('.nav-item[onclick*="tests"]'));
    
    const testId = 'custom-' + Date.now();
    AppState.cbtTest = {
        id: testId,
        title: title,
        questions: questions,
        isRetry: true
    };
    
    AppState.cbtState = questions.map(() => ({ status: 'unseen', selected: null }));
    AppState.cbtCurrentQ = 0;
    AppState.cbtStartTime = Date.now();
    
    // Timer: 72 seconds per question (similar to UPSC timings)
    const secs = Math.ceil(questions.length * 72);
    AppState.cbtTimeRemaining = secs;
    
    document.getElementById('cbt-exam-title').textContent = title;
    
    if (typeof buildCBTPalette === 'function') buildCBTPalette(questions.length);
    if (typeof renderCBTQuestion === 'function') renderCBTQuestion(0);
    if (typeof startCBTTimer === 'function') startCBTTimer();
    
    const reportOverlay = document.getElementById('exam-report-overlay');
    if (reportOverlay) reportOverlay.classList.add('hidden');
    
    const cbtOverlay = document.getElementById('cbt-overlay');
    if (cbtOverlay) cbtOverlay.classList.remove('hidden');
}

function updateDailyQuotaUI() {
    const u = AppState.user;
    const quotaText = document.getElementById('gen-quota-text');
    if (!quotaText) return;
    if (u && u.isPremium) {
        quotaText.textContent = 'Unlimited (PRO)';
        quotaText.style.color = 'var(--gold)';
    } else {
        const today = new Date().toISOString().split('T')[0];
        const quotaKey = `upsc_gen_count_${today}`;
        const usedCount = parseInt(localStorage.getItem(quotaKey) || '0');
        const remaining = Math.max(0, 25 - usedCount);
        quotaText.textContent = `${remaining} / 25 Left`;
        if (remaining <= 5) quotaText.style.color = 'var(--red)';
        else quotaText.style.color = 'var(--teal)';
    }
}

function initMidnightCountdown() {
    const timerEl = document.getElementById('gen-refresh-timer');
    if (!timerEl) return;
    setInterval(() => {
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setHours(24, 0, 0, 0);
        const diffMs = tomorrow - now;
        const h = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const m = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        const s = Math.floor((diffMs % (1000 * 60)) / 1000);
        timerEl.textContent = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }, 1000);
}
