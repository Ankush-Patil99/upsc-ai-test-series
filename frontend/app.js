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
    historyPageSize: 8,
    historySortKey: 'date',
    historySortDir: -1,
    // Topic dropdown
    dropdownFocusIndex: -1,
};

// ======================== MOCK DATA ========================
const MOCK_FULL_TESTS = [
    { id: 2, title: 'Prototype Paper', questions: 100, duration: '2 hr', type: 'GS-1', status: 'new', paperType: 'General Studies I' }
];

const SUBJECTS = [
    { name: 'History', icon: '📜', tests: [] },
    { name: 'Art and culture', icon: '🎭', tests: [] },
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
    document.getElementById('user-avatar').textContent = u.avatar;
    document.getElementById('user-display-name').textContent = u.name;
    document.getElementById('topbar-user-badge').textContent = u.avatar;
}

// ======================== APP INIT ========================
function initApp() {
    renderTestSeries();
    initAnalytics();
    renderRecentGenerations();
    updateTopbarStats();
    applyPanelStates();
    updateBadgeDisplay();
    // Show current streak in topbar
    const streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"count":0}');
    const streakEl = document.getElementById('topbar-streak');
    if (streakEl) streakEl.textContent = streakData.count + 'd streak';
}

function updateTopbarStats() {
    const attempts = AppState.testAttempts.length || 0;
    const avg = AppState.testAttempts.length ?
        Math.round(AppState.testAttempts.reduce((s, a) => s + a.score, 0) / AppState.testAttempts.length) : 0;
    document.getElementById('topbar-tests').textContent = attempts;
    document.getElementById('topbar-avg').textContent = avg + '%';
}

// ======================== NAVIGATION ========================
function switchSection(section, el) {
    // Sections
    ['tests', 'analytics', 'generator'].forEach(s => {
        document.getElementById(`section-${s}`).classList.toggle('active', s === section);
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
    const titles = { tests: 'Test Series', analytics: 'Analytics Dashboard', generator: 'Question Generator' };
    document.getElementById('page-title').textContent = titles[section] || section;
    AppState.currentSection = section;

    // On analytics — init charts if not done
    if (section === 'analytics') {
        setTimeout(() => { initCharts(); initHistoryTable(); }, 50);
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
    // Re-init charts to match theme
    if (AppState.subjectChart) { AppState.subjectChart.destroy(); AppState.subjectChart = null; }
    if (AppState.trendChart) { AppState.trendChart.destroy(); AppState.trendChart = null; }
    if (AppState.currentSection === 'analytics') setTimeout(initCharts, 50);
}

// ======================== TEST SERIES ========================
function renderTestSeries() {
    renderFullLengthTests();
    renderSubjectGrid();
}

function renderFullLengthTests() {
    const grid = document.getElementById('full-length-grid');
    grid.innerHTML = '';
    MOCK_FULL_TESTS.forEach(test => {
        grid.appendChild(buildTestCard(test, false));
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
    // Find test in mock data
    const fullTest = MOCK_FULL_TESTS.find(t => t.id === testId);
    const subjectTest = SUBJECTS.flatMap(s => s.tests).find(t => t.id === testId);
    const test = fullTest || subjectTest;
    if (!test) return;

    // Fetch questions from API, fallback to sample questions
    let questions;
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

    AppState.cbtTest = { ...test, questions };
    AppState.cbtState = questions.map(() => ({ status: 'unseen', selected: null }));
    AppState.cbtCurrentQ = 0;
    AppState.cbtStartTime = Date.now();

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
                    score: s.score, rank: '-', subject: 'General Studies',
                    time: `${mins}m ${secs}s`, id: s.id
                });
            });
            
            SCORE_TREND.all = [...data.sessions].reverse().map(s => s.score);
            
            Object.keys(SUBJECT_ACCURACY).forEach(k => delete SUBJECT_ACCURACY[k]);
            SUBJECTS.forEach(s => {
                SUBJECT_ACCURACY[s.name] = 0;
            });
            data.taxonomy.forEach(t => {
                if(t.category !== 'General Geography') {
                    SUBJECT_ACCURACY[t.category] = Math.round(t.mastery_percentage);
                }
            });
            
            const totalTests = data.sessions.length;
            const avgScore = totalTests ? Math.round(data.sessions.reduce((a,c)=>a+c.score,0)/totalTests) : 0;
            const sortedTax = [...data.taxonomy].filter(t => t.category !== 'General Geography').sort((a,b)=>a.mastery_percentage - b.mastery_percentage);
            const weakSubj = sortedTax.length > 0 ? sortedTax[0] : null;
            
            const elRank = document.getElementById('stat-rank');
            if (elRank) elRank.textContent = '#--'; 
            document.getElementById('stat-avg').textContent = `${avgScore}%`;
            document.getElementById('stat-total').textContent = totalTests;
            document.getElementById('stat-weak').textContent = weakSubj ? weakSubj.category : 'N/A';
            
            const breakdownEl = document.getElementById('stat-test-breakdown');
            if (breakdownEl) {
                const bCount = {};
                data.sessions.forEach(s => {
                    bCount[s.topic_tested] = (bCount[s.topic_tested] || 0) + 1;
                });
                breakdownEl.innerHTML = Object.entries(bCount).map(([k,v]) => `<div style="padding: 2px 0;">${k}: <strong>${v}</strong></div>`).join('');
            }
            
            const dynamicInsightsEl = document.getElementById('dynamic-ai-insights');
            if (dynamicInsightsEl) {
                if (data.sessions.length > 0) {
                    const topWeakness = weakSubj ? weakSubj.category : "specific areas";
                    let timeTakenAvg = Math.round(data.sessions.reduce((a,c)=>a+c.time_taken_secs,0)/data.sessions.length / 60);
                    let streakData = JSON.parse(localStorage.getItem('upsc_streak') || '{"count":0}');
                    let streakStr = streakData.count;
                    let strongSubj = sortedTax.length > 1 ? sortedTax[sortedTax.length-1].category : '';
                    let strongAcc = sortedTax.length > 1 ? Math.round(sortedTax[sortedTax.length-1].mastery_percentage) : 0;
                    
                    dynamicInsightsEl.innerHTML = `<strong>Study Pattern Analysis:</strong> Across your ${totalTests} test attempts, you maintain a ${streakStr} day streak. You spend around ${timeTakenAvg} minutes per test on average. Your overall average score is ${avgScore}%.<br><br>
                    <strong>Subject Wise Basic Analysis:</strong><br>
                    • <strong>${topWeakness}</strong> is your weakest area. Focus on revising fundamental concepts to improve your overall score.<br>
                    ${strongSubj ? `• Your strongest area appears to be <strong>${strongSubj}</strong> with <strong>${strongAcc}%</strong> accuracy.<br>` : ''}
                    <br>Review the automatically generated tasks below or add your own custom goals to maintain momentum.`;
                } else {
                    dynamicInsightsEl.innerHTML = `Attempt your first mock test to unlock personalized AI diagnosis and peer benchmarking insights!`;
                }
            }
            
            const todoListEl = document.getElementById('ai-todo-list');
            if (todoListEl) {
                let currentTodos = JSON.parse(localStorage.getItem('upsc_todos') || 'null');
                if (!currentTodos || currentTodos.length === 0) {
                    currentTodos = sortedTax.slice(0, 3).map((t, idx) => {
                        let d = new Date(); d.setDate(d.getDate() + (idx+1)*2);
                        return { topic: `Revise basic concepts of ${t.category}`, date: d.toISOString().split('T')[0], summary: 'AI Auto-Recommended' };
                    });
                    if(currentTodos.length === 0) currentTodos = [{ topic: "Complete 'Prototype Paper' mock test", date: "", summary: "" }];
                    localStorage.setItem('upsc_todos', JSON.stringify(currentTodos));
                }
                renderTodos(currentTodos);
            }
        }
    } catch(e) { console.error('Failed analytics fetch', e); }
    
    initCharts();
    if (typeof renderHistoryTable === 'function') renderHistoryTable();
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
    const colors = values.map(v => v >= 70 ? 'rgba(29,158,117,0.8)' : v >= 50 ? 'rgba(186,117,23,0.8)' : 'rgba(226,75,74,0.8)');
    const borderColors = values.map(v => v >= 70 ? '#1D9E75' : v >= 50 ? '#BA7517' : '#E24B4A');

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
                        label: ctx => ` ${ctx.parsed.x}% accuracy`
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

function switchTrend(btn, key) {
    document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

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

function openDrillDown(subject, accuracy) {
    const panel = document.getElementById('drill-down-panel');
    document.getElementById('drill-title').textContent = subject + ' Deep Dive';
    document.getElementById('drill-close').style.display = '';

    const color = accuracy >= 70 ? 'var(--teal)' : accuracy >= 50 ? 'var(--amber-light)' : 'var(--red)';

    document.getElementById('drill-content').innerHTML = `
        <div style="margin-bottom:1rem;">
            <div class="srb-header" style="display:flex;justify-content:space-between;margin-bottom:0.5rem;">
                <span style="color:var(--text-muted);font-size:0.85rem;">Overall Accuracy</span>
                <span style="color:${color};font-weight:700;">${accuracy}%</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width:${accuracy}%;background:${color}"></div></div>
        </div>
        <div class="ai-badge" style="margin-bottom:1rem;">✦ AI Diagnosis</div>
        <div style="font-size:0.85rem;color:var(--text-muted);line-height:1.7;background:var(--ai-bg);border:1px solid var(--ai-border);border-radius:10px;padding:1rem;">
            ${accuracy >= 70
                ? `<strong>${subject}</strong> is your strong area at ${accuracy}%. Focus on advanced multi-statement questions. Try to push above 85% by practicing harder PYQs specifically tagged to this subject.`
                : accuracy >= 50
                    ? `<strong>${subject}</strong> needs improvement at ${accuracy}%. Identify specific weak sub-topics based on your latest attempt. Spend 30 min/day on NCERTs for this subject. Use the Question Generator to practice 10 targeted questions daily. Aim to reach 70%+ within 2 weeks.`
                    : `<strong>${subject}</strong> is a critical weak area at ${accuracy}%. This requires urgent attention. Start with NCERT foundation (Class 9-12), then move to standard references. Make a 30-day study plan. Use our generator for daily 5-question drills. Avoid full tests on this subject until basics are solid.`
            }
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
            <td><button class="btn-ghost-sm" onclick='openReviewModal(${JSON.stringify(row)})'>View →</button></td>`;
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
function renderTodos(todos) {
    const list = document.getElementById('ai-todo-list');
    if (!list) return;
    list.innerHTML = '';
    todos.forEach((t, i) => {
        const topic = typeof t === 'string' ? t : t.topic;
        const summary = typeof t === 'string' ? '' : (t.summary || t.date || '');
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${i + 1}</td>
            <td style="font-weight:600;">${topic}</td>
            <td style="color:var(--text-muted);">${summary || '-'}</td>
            <td>
                <span style="cursor:pointer; color:var(--red); font-weight:bold; padding:0 5px;" onclick="removeTodoItem(${i})" title="Delete">✕</span>
            </td>
        `;
        list.appendChild(tr);
    });
}

function addTodoItem() {
    const input = document.getElementById('custom-todo-input');
    const dateInput = document.getElementById('custom-todo-date');
    const summaryInput = document.getElementById('custom-todo-summary');
    
    const val = input.value.trim();
    if (val) {
        let todos = JSON.parse(localStorage.getItem('upsc_todos') || '[]');
        todos.push({
            topic: val,
            date: dateInput ? dateInput.value : '',
            summary: summaryInput ? summaryInput.value.trim() : ''
        });
        localStorage.setItem('upsc_todos', JSON.stringify(todos));
        renderTodos(todos);
        
        input.value = '';
        if(dateInput) dateInput.value = '';
        if(summaryInput) summaryInput.value = '';
    }
}

function removeTodoItem(idx) {
    let todos = JSON.parse(localStorage.getItem('upsc_todos') || '[]');
    todos.splice(idx, 1);
    localStorage.setItem('upsc_todos', JSON.stringify(todos));
    renderTodos(todos);
}

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
    { id: 'pass_70',       icon: '✅', title: 'Above the Cut',     desc: 'Scored 70% or more in a test',           condition: (p) => p >= 70 },
    { id: 'ace_90',        icon: '⭐', title: 'Ace Aspirant',      desc: 'Scored 90% or more in a test',           condition: (p) => p >= 90 },
    { id: 'streak_7',      icon: '🔥', title: '7-Day Warrior',     desc: '7-day study streak',                     condition: () => { const s = JSON.parse(localStorage.getItem('upsc_streak') || '{}'); return s.count >= 7; }},
    { id: 'streak_30',     icon: '💎', title: 'Iron Will',         desc: '30-day study streak',                    condition: () => { const s = JSON.parse(localStorage.getItem('upsc_streak') || '{}'); return s.count >= 30; }},
    { id: 'perfect_score', icon: '🌟', title: 'Perfect Score',     desc: 'Scored 100% in any test',               condition: (p) => p === 100 },
    { id: 'speed_demon',   icon: '⚡', title: 'Speed Demon',       desc: 'Answered all questions in under 60 min', condition: (p, c, t) => t === 100 && c === t },
    { id: 'social_butterfly', icon: '🤝', title: 'Social Butterfly', desc: 'Added 3 friends to your network', condition: () => false },
    { id: 'paired_warriors', icon: '⚔️', title: 'Paired Warriors', desc: 'Maintained a 7-day paired streak', condition: () => false },
    { id: 'challenger', icon: '🤺', title: 'Challenger', desc: 'Challenged a friend to a mock test', condition: () => false },
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
    if (!document.getElementById('sticker-animation-style')) {
        const style = document.createElement('style');
        style.id = 'sticker-animation-style';
        style.innerHTML = `
            @keyframes flyInHit {
                0% { transform: translateX(-150vw) translateY(50vh) rotate(-45deg) scale(0.5); opacity: 0; }
                50% { transform: translateX(10vw) translateY(-5vh) rotate(15deg) scale(1.5); opacity: 1; }
                70% { transform: translateX(-5vw) translateY(5vh) rotate(-5deg) scale(1.2); }
                100% { transform: translateX(0) translateY(0) rotate(0deg) scale(1); }
            }
            @keyframes targetShake {
                0%, 100% { transform: translateX(0); }
                20%, 60% { transform: translateX(-15px) rotate(-10deg); }
                40%, 80% { transform: translateX(15px) rotate(10deg); }
            }
            @keyframes stickerPop {
                0% { transform: scale(0); opacity: 0; }
                50% { transform: scale(1.2); opacity: 1; }
                70% { transform: scale(0.95); }
                100% { transform: scale(1); opacity: 1; }
            }
            .achievement-overlay {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center;
                z-index: 99999; flex-direction: column; color: white; backdrop-filter: blur(8px);
            }
            .achievement-sticker-container {
                position: relative; width: 250px; height: 250px;
                display: flex; align-items: center; justify-content: center; margin-bottom: 2rem;
            }
            .achievement-target { font-size: 8rem; animation: targetShake 0.6s 0.7s ease-out; }
            .achievement-arrow { position: absolute; font-size: 6rem; animation: flyInHit 0.7s forwards cubic-bezier(0.25, 1, 0.5, 1); }
            .achievement-text { text-align: center; animation: stickerPop 0.5s 0.9s backwards; }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'achievement-overlay';
    overlay.innerHTML = `
        <div class="achievement-sticker-container">
            <div class="achievement-target">🎯</div>
            <div class="achievement-arrow">${badge.icon || '🚀'}</div>
        </div>
        <div class="achievement-text">
            <h1 style="color:var(--gold); margin:0; font-size:3rem; text-shadow: 0 0 30px rgba(186,117,23,0.8); font-weight:900;">Badge Unlocked!</h1>
            <h2 style="margin:15px 0 0 0; font-size: 2rem;">${badge.title || badge.name}</h2>
            <p style="color:rgba(255,255,255,0.8); font-size:1.2rem; max-width:400px; margin:10px auto;">${badge.desc}</p>
        </div>
    `;
    document.body.appendChild(overlay);

    setTimeout(() => {
        overlay.style.transition = 'opacity 0.6s';
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 600);
    }, 4500);
}

function updateBadgeDisplay() {
    const earnedBadges = JSON.parse(localStorage.getItem('upsc_badges') || '[]');
    const badgeCountEl = document.getElementById('badge-count');
    if (badgeCountEl) badgeCountEl.textContent = earnedBadges.length;

    // Render badges in sidebar or topbar
    const badgeShelf = document.getElementById('badge-shelf');
    if (badgeShelf) {
        badgeShelf.innerHTML = '';
        BADGE_DEFINITIONS.filter(b => earnedBadges.includes(b.id)).forEach(b => {
            const span = document.createElement('span');
            span.className = 'badge-icon-pill earned';
            span.title = b.title + ': ' + b.desc;
            span.textContent = b.icon;
            span.style.cursor = 'pointer';
            span.onclick = () => showBadgeToast(b);
            badgeShelf.appendChild(span);
        });
        // Show locked count
        const locked = BADGE_DEFINITIONS.length - earnedBadges.length;
        if (locked > 0) {
            const lockSpan = document.createElement('span');
            lockSpan.className = 'badge-icon-pill locked';
            lockSpan.title = locked + ' badges still locked';
            lockSpan.textContent = '+' + locked;
            badgeShelf.appendChild(lockSpan);
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
        <button onclick="changeStreakMonth(-1)" style="background:rgba(255,255,255,0.05); border:none; border-radius:4px; color:var(--text); cursor:pointer; padding:4px 12px; font-size:1rem;">&larr;</button>
        <span>${monthNames[currentMonth]} ${currentYear}</span>
        <button onclick="changeStreakMonth(1)" style="background:${currentStreakMonthOffset < 0 ? 'rgba(255,255,255,0.05)' : 'transparent'}; border:none; border-radius:4px; color:${currentStreakMonthOffset < 0 ? 'var(--text)' : 'rgba(255,255,255,0.1)'}; cursor:${currentStreakMonthOffset < 0 ? 'pointer' : 'default'}; padding:4px 12px; font-size:1rem;" ${currentStreakMonthOffset >= 0 ? 'disabled' : ''}>&rarr;</button>
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

    for (let dayNum = 1; dayNum <= daysInMonth; dayNum++) {
        const d = new Date(currentYear, currentMonth, dayNum);
        // adjust to local timezone string format YYYY-MM-DD
        const dObj = new Date(d.getTime() - (d.getTimezoneOffset() * 60000));
        const ds = dObj.toISOString().split('T')[0];
        
        const qCount = dailyStats[ds] || 0;
        const isActive = activeSet.has(ds);
        const isToday = ds === todayStr;
        const isFuture = d > today;

        const cell = document.createElement('div');
        cell.className = 'streak-cal-cell';
        cell.title = ds + (qCount > 0 ? ' · ' + qCount + ' questions attempted' : '');

        if (isToday) {
            cell.classList.add('streak-today');
            cell.innerHTML = `<span class="cal-day-num">${dayNum}</span>${qCount > 0 ? '<span class="cal-q-count">' + qCount + '</span>' : ''}`;
        } else if (isActive) {
            cell.classList.add('streak-active');
            cell.innerHTML = `<span class="cal-day-num" style="color: #fff;">${dayNum}</span>${qCount > 0 ? '<span class="cal-q-count" style="color:rgba(255,255,255,0.9);">' + qCount + '</span>' : ''}`;
        } else if (isFuture) {
            cell.classList.add('streak-future');
        } else {
            // Inactive past day — show only the date number in muted text
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
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    document.getElementById('friends-modal').classList.remove('hidden');
    switchFriendsTab('network');
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
