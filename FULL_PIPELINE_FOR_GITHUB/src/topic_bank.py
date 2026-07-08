"""
topic_bank.py — Large UPSC topic bank for dynamic question generation.
Covers all 4 GS papers with diverse subtopics, difficulties, and question types.
Used by main.py --count N to auto-sample N question inputs.
"""
import random

# All valid question types in the pipeline
QUESTION_TYPES = [
    "factual",
    "analytical",
    "analytical",
    "factual",
    "factual",
    "analytical",
    "analytical",
    "current_affairs",
]

# ─────────────────────────────────────────────────────────────────────────────
# Full topic bank — (topic, subtopic, difficulty, paper, question_type)
# ─────────────────────────────────────────────────────────────────────────────
TOPIC_BANK = [
    # ── GS 1 — History ──────────────────────────────────────────────────────
    ("Indian History", "Indus Valley Civilisation — Mohenjo-Daro and Harappa", "medium", "GS1", "factual"),
    ("Indian History", "Vedic Period — Rigvedic vs Later Vedic Society", "hard", "GS1", "analytical"),
    ("Indian History", "Buddhism and Jainism — Comparison of Core Doctrines", "medium", "GS1", "analytical"),
    ("Indian History", "Mauryan Empire — Ashoka's Dhamma and Its Spread", "easy", "GS1", "factual"),
    ("Indian History", "Gupta Period — Golden Age of India", "medium", "GS1", "analytical"),
    ("Indian History", "Medieval India — Bhakti and Sufi Movements", "medium", "GS1", "analytical"),
    ("Indian History", "Mughal Empire — Administration and Architecture", "easy", "GS1", "factual"),
    ("Indian History", "Modern India — Revolt of 1857 Causes and Nature", "medium", "GS1", "analytical"),
    ("Indian History", "Modern India — Indian National Congress Formation 1885", "easy", "GS1", "factual"),
    ("Indian History", "Modern India — Non-Cooperation Movement 1920-22", "medium", "GS1", "factual"),
    ("Indian History", "Modern India — Civil Disobedience Movement and Salt March", "medium", "GS1", "analytical"),
    ("Indian History", "Modern India — Quit India Movement 1942", "hard", "GS1", "factual"),
    ("Indian History", "Modern India — Partition of Bengal 1905 and Aftermath", "medium", "GS1", "factual"),
    ("Indian History", "Modern India — Role of Revolutionary Nationalism", "hard", "GS1", "analytical"),
    ("Indian History", "Modern India — Peasant and Tribal Movements", "hard", "GS1", "analytical"),
    ("Indian History", "Post-Independence — Integration of Princely States", "medium", "GS1", "factual"),

    # ── GS 1 — Art & Culture ────────────────────────────────────────────────
    ("Art and Culture", "Classical Dance Forms — Bharatanatyam, Kathak, Odissi", "easy", "GS1", "factual"),
    ("Art and Culture", "Classical Music — Hindustani vs Carnatic Traditions", "medium", "GS1", "analytical"),
    ("Art and Culture", "Temple Architecture — Nagara vs Dravida Style", "medium", "GS1", "analytical"),
    ("Art and Culture", "Painting Schools — Mughal, Rajput, Madhubani, Warli", "easy", "GS1", "factual"),
    ("Art and Culture", "UNESCO Intangible Cultural Heritage from India", "hard", "GS1", "current_affairs"),
    ("Art and Culture", "Indian Puppetry and Folk Theatre Traditions", "medium", "GS1", "factual"),
    ("Art and Culture", "Buddhist Art — Stupas, Chaityas, and Viharas", "medium", "GS1", "factual"),
    ("Art and Culture", "Indian Literature — Sangam Literature and Tamil Heritage", "hard", "GS1", "analytical"),

    # ── GS 1 — Geography ────────────────────────────────────────────────────
    ("Indian Geography", "Physical Features — Himalayas, Deccan Plateau, Coastal Plains", "easy", "GS1", "factual"),
    ("Indian Geography", "Rivers — Himalayan vs Peninsular River Systems", "medium", "GS1", "factual"),
    ("Indian Geography", "Monsoon — Mechanism and Regional Variations", "medium", "GS1", "analytical"),
    ("Indian Geography", "Soils of India — Types, Distribution and Crops", "medium", "GS1", "factual"),
    ("Indian Geography", "Natural Vegetation — Tropical, Temperate, Alpine Forests", "easy", "GS1", "factual"),
    ("Indian Geography", "Agriculture — Green Revolution and Its Impact", "medium", "GS1", "analytical"),
    ("Indian Geography", "Demographhy — Census 2011 Key Findings", "easy", "GS1", "factual"),
    ("Indian Geography", "Disaster — Cyclone, Flood, Earthquake Prone Zones", "medium", "GS1", "analytical"),
    ("World Geography", "World Climate Zones — Koppen Classification", "hard", "GS1", "analytical"),
    ("World Geography", "Ocean Currents and Their Impact on Climate", "hard", "GS1", "analytical"),
    ("World Geography", "Tectonic Plates — Earthquakes and Volcanoes", "medium", "GS1", "factual"),
    ("World Geography", "Straits, Gulfs, and Bays of Strategic Importance", "medium", "GS1", "factual"),

    # ── GS 2 — Indian Polity ─────────────────────────────────────────────────
    ("Indian Polity", "Constitutional Framework — Preamble and its Significance", "easy", "GS2", "analytical"),
    ("Indian Polity", "Fundamental Rights — Article 14 Right to Equality", "medium", "GS2", "analytical"),
    ("Indian Polity", "Fundamental Rights — Article 19 Freedom of Speech", "medium", "GS2", "factual"),
    ("Indian Polity", "Fundamental Rights — Article 21 Right to Life and Personal Liberty", "hard", "GS2", "analytical"),
    ("Indian Polity", "Fundamental Rights — Article 21A Right to Education", "easy", "GS2", "factual"),
    ("Indian Polity", "Fundamental Rights — Article 32 Right to Constitutional Remedies", "medium", "GS2", "analytical"),
    ("Indian Polity", "Directive Principles — Article 44 Uniform Civil Code", "hard", "GS2", "analytical"),
    ("Indian Polity", "Fundamental Duties — Article 51A and Their Significance", "medium", "GS2", "analytical"),
    ("Indian Polity", "Parliament — Powers and Functions of Rajya Sabha", "hard", "GS2", "analytical"),
    ("Indian Polity", "Parliament — Legislative Process and Money Bills", "medium", "GS2", "analytical"),
    ("Indian Polity", "Parliament — Parliamentary Committees and Their Role", "hard", "GS2", "factual"),
    ("Indian Polity", "President of India — Powers, Election, Impeachment", "medium", "GS2", "factual"),
    ("Indian Polity", "Prime Minister and Council of Ministers — Constitutional Position", "medium", "GS2", "analytical"),
    ("Indian Polity", "Supreme Court — Original, Appellate and Advisory Jurisdiction", "hard", "GS2", "analytical"),
    ("Indian Polity", "High Courts — Jurisdiction and Writ Powers", "medium", "GS2", "factual"),
    ("Indian Polity", "Federal Structure — Centre-State Relations (Articles 245-263)", "hard", "GS2", "analytical"),
    ("Indian Polity", "Emergency Provisions — National, State, Financial Emergency", "hard", "GS2", "factual"),
    ("Indian Polity", "Constitutional Bodies — Election Commission of India", "medium", "GS2", "analytical"),
    ("Indian Polity", "Constitutional Bodies — Comptroller and Auditor General", "medium", "GS2", "analytical"),
    ("Indian Polity", "Constitutional Bodies — UPSC and State PSCs", "easy", "GS2", "factual"),
    ("Indian Polity", "Constitutional Bodies — National Commission for SC/ST", "medium", "GS2", "factual"),
    ("Indian Polity", "Panchayati Raj — 73rd and 74th Constitutional Amendments", "medium", "GS2", "analytical"),
    ("Indian Polity", "Amendment of Constitution — Article 368 Procedure", "hard", "GS2", "analytical"),
    ("Governance", "Right to Information Act 2005 — Scope and Exemptions", "medium", "GS2", "factual"),
    ("Governance", "Lokpal and Lokayukta — Anti-Corruption Framework", "medium", "GS2", "analytical"),
    ("Governance", "Judicial Activism and Public Interest Litigation", "hard", "GS2", "analytical"),
    ("Governance", "E-Governance Initiatives — Digital India Programme", "easy", "GS2", "current_affairs"),
    ("International Relations", "India's Neighbourhood First Policy", "medium", "GS2", "analytical"),
    ("International Relations", "India-China Relations — Border Disputes and Trade", "hard", "GS2", "analytical"),
    ("International Relations", "India-USA Strategic Partnership", "medium", "GS2", "analytical"),
    ("International Relations", "SAARC, BIMSTEC — Regional Cooperation Frameworks", "medium", "GS2", "factual"),
    ("International Relations", "WTO — India's Stance on Agricultural Subsidies", "hard", "GS2", "analytical"),
    ("International Relations", "United Nations — Security Council Reform", "hard", "GS2", "analytical"),
    ("International Relations", "India at G20 — Key Priorities and Outcomes", "medium", "GS2", "current_affairs"),
    ("International Relations", "SCO — India's Membership and Strategic Importance", "medium", "GS2", "factual"),

    # ── GS 3 — Economy ──────────────────────────────────────────────────────
    ("Indian Economy", "GDP, GNP, NNP — Concepts and Differences", "easy", "GS3", "factual"),
    ("Indian Economy", "Five Year Plans — Evolution and NITI Aayog", "medium", "GS3", "analytical"),
    ("Indian Economy", "Taxation — Direct vs Indirect Taxes", "easy", "GS3", "factual"),
    ("Indian Economy", "Taxation — Goods and Services Tax (GST) Structure", "medium", "GS3", "factual"),
    ("Indian Economy", "Banking — Reserve Bank of India Functions and Instruments", "easy", "GS3", "factual"),
    ("Indian Economy", "Banking — Non-Performing Assets and IBC 2016", "hard", "GS3", "analytical"),
    ("Indian Economy", "Inflation — Types, Causes and Monetary Policy Response", "medium", "GS3", "analytical"),
    ("Indian Economy", "Union Budget — Key Components and Fiscal Policy", "medium", "GS3", "factual"),
    ("Indian Economy", "Foreign Trade — Balance of Payment, Current Account Deficit", "hard", "GS3", "analytical"),
    ("Indian Economy", "FDI and FII — Differences and Policy Framework", "medium", "GS3", "analytical"),
    ("Indian Economy", "Infrastructure — National Infrastructure Pipeline", "medium", "GS3", "current_affairs"),
    ("Indian Economy", "Agriculture — Minimum Support Price Mechanism", "medium", "GS3", "analytical"),
    ("Indian Economy", "Food Security — National Food Security Act 2013", "easy", "GS3", "factual"),
    ("Indian Economy", "Land Reforms — Post-Independence Measures", "hard", "GS3", "analytical"),
    ("Indian Economy", "Inclusive Growth — Poverty Measurement and MGNREGA", "medium", "GS3", "analytical"),
    ("Indian Economy", "Digital Economy — UPI, Fintech and Financial Inclusion", "easy", "GS3", "current_affairs"),
    ("Indian Economy", "Make in India — PLI Schemes and Manufacturing", "medium", "GS3", "current_affairs"),
    ("Internal Security", "Left Wing Extremism — Causes and Government Response", "hard", "GS3", "analytical"),
    ("Internal Security", "Cyber Security — Threats, IT Act and Frameworks", "medium", "GS3", "analytical"),
    ("Internal Security", "Border Management — India's Security Challenges", "hard", "GS3", "analytical"),
    ("Disaster Management", "National Disaster Management Authority — Role and Structure", "medium", "GS3", "factual"),
    ("Disaster Management", "Sendai Framework 2015-30 — Key Priorities", "hard", "GS3", "analytical"),

    # ── GS 3 — Science & Technology ─────────────────────────────────────────
    ("Science and Technology", "Space — ISRO Missions: Chandrayaan, Mangalyaan, Gaganyaan", "medium", "GS3", "analytical"),
    ("Science and Technology", "Nuclear Energy — India's Three Stage Nuclear Programme", "hard", "GS3", "analytical"),
    ("Science and Technology", "Biotechnology — GM Crops and Regulation in India", "hard", "GS3", "analytical"),
    ("Science and Technology", "Artificial Intelligence — Applications and Ethical Issues", "medium", "GS3", "analytical"),
    ("Science and Technology", "5G Technology — Applications and India's Rollout", "easy", "GS3", "current_affairs"),
    ("Science and Technology", "Quantum Computing — Basics and National Mission", "hard", "GS3", "factual"),
    ("Science and Technology", "Defence — Indigenous Defence Production and DRDO", "medium", "GS3", "analytical"),
    ("Science and Technology", "Health — COVID-19 Vaccines and Covaxin Development", "medium", "GS3", "factual"),

    # ── GS 3 — Environment ──────────────────────────────────────────────────
    ("Environment", "Climate Change — Paris Agreement and India's NDC Commitments", "hard", "GS3", "analytical"),
    ("Environment", "Biodiversity — Convention on Biological Diversity and Nagoya Protocol", "hard", "GS3", "analytical"),
    ("Environment", "Biodiversity — Ramsar Convention Wetlands in India", "hard", "GS3", "current_affairs"),
    ("Environment", "Biodiversity — IUCN Red List Categories", "medium", "GS3", "factual"),
    ("Environment", "Forest Rights Act 2006 — Provisions and Significance", "medium", "GS3", "analytical"),
    ("Environment", "Pollution — Air Quality Index and National Clean Air Programme", "medium", "GS3", "factual"),
    ("Environment", "Renewable Energy — Solar Mission and Wind Power Targets", "easy", "GS3", "current_affairs"),
    ("Environment", "Wildlife Protection Act 1972 — Key Schedules and Amendments", "medium", "GS3", "factual"),
    ("Environment", "Environment Impact Assessment — Notification and Process", "hard", "GS3", "analytical"),
    ("Environment", "Plastic Pollution — Extended Producer Responsibility", "medium", "GS3", "current_affairs"),

    # ── GS 4 — Ethics ────────────────────────────────────────────────────────
    ("Ethics", "Philosophical Basis of Governance — Plato, Kautilya, Gandhi", "hard", "GS4", "analytical"),
    ("Ethics", "Probity in Public Life — Integrity, Impartiality and Objectivity", "medium", "GS4", "analytical"),
    ("Ethics", "Emotional Intelligence — Concept and Application in Governance", "medium", "GS4", "analytical"),
    ("Ethics", "Attitude — Components, Formation and Change", "medium", "GS4", "factual"),
    ("Ethics", "Civil Services — Constitutional Values and Code of Conduct", "hard", "GS4", "analytical"),
    ("Ethics", "Corruption — Causes, Effects and Anti-Corruption Measures", "hard", "GS4", "analytical"),
    ("Ethics", "Corporate Governance — CSR and Ethical Business Practices", "medium", "GS4", "analytical"),
    ("Ethics", "Work Culture — Accountability, Transparency and Responsiveness", "easy", "GS4", "factual"),
]


def sample_topics(count: int, seed: int = None) -> list[dict]:
    """
    Returns `count` question input dicts sampled from the topic bank.
    If count > len(TOPIC_BANK), topics are reused with shuffled types/difficulties.
    
    Args:
        count: Number of question inputs to generate.
        seed:  Optional random seed for reproducibility.
    
    Returns:
        List of dicts compatible with run_single_question() input format.
    """
    if seed is not None:
        random.seed(seed)

    bank = list(TOPIC_BANK)
    result = []

    full_passes = count // len(bank)
    remainder   = count %  len(bank)

    for _ in range(full_passes):
        shuffled = bank.copy()
        random.shuffle(shuffled)
        result.extend(shuffled)

    if remainder:
        result.extend(random.sample(bank, remainder))

    # Convert tuples to dicts
    return [
        {
            "topic":         t[0],
            "subtopic":      t[1],
            "difficulty":    t[2],
            "paper":         t[3],
            "question_type": t[4],
        }
        for t in result
    ]
