# 🎯 UPSC AI Platform — Self-Correcting RAG Pipeline

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-RAG_Pipeline-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=githubactions)
![LangSmith](https://img.shields.io/badge/LangSmith-LLMOps_Traced-1C3C3C)
![Ollama](https://img.shields.io/badge/Ollama-Llama_3.1_8B-black)

> A full-stack AI exam preparation platform that auto-scrapes UPSC current affairs sources daily, embeds the content into a pgvector database, and generates contextual MCQs through a **self-correcting LangGraph RAG pipeline** running entirely on a local GPU — served via FastAPI with JWT auth and a CBT exam frontend.

---

## 📚 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Key Features](#-key-features)
- [System Workflow](#-system-workflow)
- [Architecture](#-architecture)
- [Design Evolution](#-design-evolution)
- [Retrieval & Embedding](#-retrieval--embedding)
- [LLM Configuration](#-llm-configuration)
- [Authentication](#-authentication)
- [Current Affairs Sources](#-current-affairs-sources)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Testing](#-testing)
- [CI/CD Pipeline](#️-cicd-pipeline)
- [LangSmith Tracing](#-langsmith-tracing)
- [Performance](#️-performance)
- [Deployment](#-deployment)
- [Current Status](#-current-status)

---

## 📖 Overview

The platform runs a complete automated loop:

1. **Scrape** — pulls daily current affairs from news sources (RSS feeds + HTTP scraping)
2. **Classify & Chunk** — classifies articles by UPSC subject, splits into 1200-character chunks
3. **Deduplicate & Embed** — semantic deduplication via pgvector L2 distance before insertion
4. **Retrieve** — similarity search returns top textbook facts + historical PYQ patterns
5. **Draft** — Llama 3.1 8B generates a structured MCQ with rationale and mains hint
6. **Critique** — same model acts as LLM-judge; flags hallucinations and triggers re-draft
7. **Serve** — FastAPI delivers questions to a Vanilla JS CBT exam frontend with analytics

---

## 🎯 Problem Statement

UPSC aspirants spend hours manually collecting current affairs from scattered sources and have no adaptive, AI-generated practice questions tied to that content.

This platform automates the full pipeline:

```
Current Affairs Collection → Embedding → Retrieval → MCQ Generation
```

No manual curation. No API token limits. Runs entirely on local hardware.

---

## ✨ Key Features

| Feature | Technology | Details |
|---|---|---|
| **Self-Correcting RAG Pipeline** | LangGraph | 3-node state machine: `Retrieve → Draft → Critique` with hallucination loop (max 3 iterations) |
| **Local GPU Inference** | Ollama + Llama 3.1 8B | Zero API costs, zero token limits — runs on RTX 5050 8GB VRAM |
| **Semantic Retrieval** | PostgreSQL + pgvector | 384d embeddings, L2 deduplication at threshold 0.15 |
| **JWT + Google Auth** | bcrypt + python-jose | Sliding-window rate limiting, token blacklist on logout, Google Sign-In (OAuth2) |
| **CBT Exam Frontend** | Vanilla HTML/CSS/JS | 242KB interactive UI — timer, subject tabs, real-time score analytics |
| **24hr Auto-Scraping** | APScheduler + BeautifulSoup | Scheduled pipeline scrapes sources, classifies, embeds, and deduplicates daily |
| **LLMOps Tracing** | LangSmith | Full observability — latency, token usage, and critique trace logged per LangGraph run |
| **Containerized** | Docker + Docker Compose | Production `Dockerfile` + `docker-compose.prod.yml` for one-command deployment |
| **CI Verification** | GitHub Actions | Automated PyTest → Docker build on every push to `main` |

---

## 🔄 System Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE (24hr)                    │
│                                                                 │
│  The Hindu (RSS) ─┐                                             │
│  Indian Express ──┼──▶ Chunk (1200 chars) ──▶ Classify ──▶    │
│  ForumIAS (HTTP) ─┘       (overlap: 200)          ↕             │
│                         Deduplicate (L2 < 0.15) ──▶ pgvector   │
└──────────────────────────────────────────┬──────────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  pgvector   │
                                    │ 384d embeds │
                                    └──────┬──────┘
                                           │
┌──────────────────────────────────────────▼──────────────────────┐
│                    LANGGRAPH RAG PIPELINE                       │
│                                                                 │
│   Retrieve (k=4 facts + k=3 PYQs)                               │
│       │                                                         │
│       ▼                                                         │
│   Draft MCQ  ◀─────────────────────────────────┐               │
│       │                                         │ HALLUCINATED  │
│       ▼                                         │               │
│   Critique (LLM-as-judge) ─── PASS ──▶ Final MCQ               │
│       │                                         │               │
│       └──── HALLUCINATED ───────────────────────┘  (max 3x)     │
└─────────────────────────────────────────────────────────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │  FastAPI + JWT Auth      │
                              └────────────┬────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │  CBT Frontend (Vanilla) │
                              │  Timer · Tabs · Analytics│
                              └─────────────────────────┘
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   GitHub Actions CI/CD                       │
│  ┌───────────┐    ┌──────────────┐                           │
│  │  4 pytest │───▶│ Docker Build │  Stage 3 (push + deploy) │
│  │   tests   │    │  ci-check    │  not yet wired            │
│  └───────────┘    └──────────────┘                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   Application Stack                          │
│                                                              │
│  FastAPI ──▶ PostgreSQL + pgvector ──▶ LangGraph Pipeline   │
│     │                                          │             │
│     │                              Ollama (Llama 3.1 8B)     │
│     │                              RTX 5050 · 8GB VRAM       │
│     │                                          │             │
│     └────────────── LangSmith Tracing ◀────────┘            │
└──────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Design Evolution

### Original Pipeline Design (6+ nodes)

```
Scrape → Classify → Chunk & Embed → Retrieve → Draft → Critique → Difficulty Calibrate → Format
```

### Final Pipeline Design (3 nodes)

```
Retrieve → Draft → Critique  (max 3 self-correction loops)
```

### Engineering Decisions

| Removed Node | Original Purpose | Reason Removed |
|---|---|---|
| **Classifier Node** (in-graph) | Classify articles into UPSC subjects inside LangGraph | Two sequential 8B LLM calls caused OOM on 8GB VRAM. Moved classification into pre-ingestion pipeline (`classifier.py`) |
| **Difficulty Calibration Node** | Adjust MCQ difficulty based on user `TaxonomyScore` | Three sequential LLM calls (Draft + Critique + Calibrate) exhausted VRAM |
| **Multi-Model Cascade** | Route hard questions to 70B, simple ones to 8B | No 70B fits in 8GB VRAM; disk swap took ~45s — unusable |
| **Separate Embedding Node** | Dynamically embed new facts mid-generation | Redundant once ingestion pipeline was solidified |

Moving classification and embedding into a separately scheduled ingestion pipeline improved maintainability and made the real-time graph lean enough to run on consumer hardware.

---

## 🔍 Retrieval & Embedding

| Parameter | Value |
|---|---|
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Dimensions** | 384 |
| **Vector Store** | PostgreSQL + pgvector |
| **Chunk Size** | 1200 characters |
| **Chunk Overlap** | 200 characters |
| **Splitter** | `RecursiveCharacterTextSplitter` |
| **Deduplication** | L2 distance < 0.15 — chunk skipped if near-duplicate found |
| **Retrieval k** | k=4 textbook facts + k=3 PYQ patterns |

### Database Schema

PostgreSQL stores all platform data across six tables: `users` (credentials, streaks, roles), `test_sessions` (every exam attempt with score and time), `taxonomy_scores` (per-subject mastery percentages), `mock_tests` (pre-generated question sets), `test_questions` (individual MCQs with rationale and mains hints), and `universal_question_bank` (384-dimensional pgvector embeddings for semantic retrieval).

---

## 🤖 LLM Configuration

| Setting | Value |
|---|---|
| **Model** | `llama3.1:8b` |
| **Runtime** | Ollama (local) |
| **Temperature** | 0.3 |
| **Structured Output** | No — regex extraction on raw text (`re.search(r'\{.*\}', ...)`) |
| **JSON Mode** | No |
| **Critique Model** | Same model (`llama3.1:8b`) used as LLM-as-judge |

### Why Local Llama Instead of Cloud APIs

Cloud LLM APIs were evaluated first:

| API Tried | Issue |
|---|---|
| Groq (free tier) | 6,000 tokens/min limit — batch generation repeatedly hit `429 Too Many Requests` |
| Together AI | Per-day token caps broke the 24hr automated pipeline |
| OpenRouter | Free model quotas insufficient for scheduled batch runs |
| Google Gemini (free) | Quota resets and cold starts made it unreliable for automation |

**Local Llama 3.1 8B via Ollama was chosen for:**
- Zero token limits — 24hr APScheduler cycle runs uninterrupted
- Zero per-request cost
- Consistent outputs at `temperature=0.3`
- Full offline capability (except the scraping step)

**Trade-off acknowledged:** ~30s generation latency on local GPU vs ~1–2s on hosted APIs. Acceptable for a background batch pipeline where MCQs are pre-generated.

---

## 🔐 Authentication

| Feature | Implementation | Status |
|---|---|---|
| **JWT** | `python-jose` — HS256, 7-day expiry | ✅ Live |
| **bcrypt** | `bcrypt.hashpw` / `bcrypt.checkpw` | ✅ Live |
| **Rate Limiting** | Sliding-window: 5 failed logins per 60s per IP | ✅ Live |
| **Token Blacklist** | In-memory set for immediate logout invalidation | ✅ Live |
| **Google Sign-In** | `google.oauth2.id_token.verify_oauth2_token` — upserts user on first login | ✅ Implemented |

---

## 📰 Current Affairs Sources

| Source | Method | Status |
|---|---|---|
| **The Hindu** | RSS feed via `feedparser` | ✅ Live |
| **Indian Express** | RSS feed via `feedparser` | ✅ Live |
| **ForumIAS 9PM** | HTTP scrape + BeautifulSoup | ✅ Live |
| **Drishti IAS** | HTTP scrape | ⚠️ Connected, placeholder content |
| **VisionIAS** | PDF download + PyPDF extraction | 🔧 Architecture scaffolded |
| **InsightsIAS** | PDF download + PyPDF extraction | 🔧 Architecture scaffolded |
| **PIB** | — | 🔧 Endpoint stubbed |
| **PRS Legislative** | — | 🔧 Endpoint stubbed |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Uvicorn, Python 3.11 |
| **AI / LLM** | LangGraph, LangChain, Ollama, Llama 3.1 8B |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Database** | PostgreSQL + pgvector (384-dimensional) |
| **Authentication** | JWT (`python-jose`), bcrypt, Google OAuth2 |
| **Scheduler** | APScheduler (24hr background cron) |
| **Observability** | LangSmith (LLMOps tracing) |
| **Frontend** | Vanilla HTML/CSS/JS — no framework |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Scraping** | BeautifulSoup, feedparser, requests |

---

## 📂 Project Structure

```
├── api/
│   ├── main.py              # FastAPI app — auth, tests, analytics, pipeline endpoints
│   ├── auth.py              # JWT + bcrypt + Google OAuth2
│   └── models.py            # SQLAlchemy ORM + pgvector columns
├── src/
│   ├── mcq_generation/
│   │   └── generator.py     # LangGraph 3-node RAG: Retrieve → Draft → Critique
│   ├── agents/
│   │   ├── scraper.py       # Multi-source scraper (RSS + HTTP + PDF)
│   │   ├── classifier.py    # Llama-powered UPSC subject classifier
│   │   └── updater.py       # Chunk → Deduplicate → pgvector insert
│   └── ingestion/           # PDF book ingestion pipeline (NCERTs, reference books)
├── frontend/
│   ├── index.html           # CBT exam interface (92KB)
│   ├── app.js               # Full exam logic (242KB)
│   └── style.css            # Custom responsive styling (52KB)
├── tests/
│   └── test_api.py          # 4 pytest tests
├── configs/
│   └── settings.yaml        # Model names, DB URL, chunk settings
├── .github/workflows/
│   └── ci-cd.yml            # GitHub Actions: Test → Build
├── Dockerfile               # Production container image
├── docker-compose.yml       # Local dev stack
├── docker-compose.prod.yml  # Production stack
├── deploy.sh                # AWS EC2 bootstrap script
└── requirements.txt
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker + Docker Compose
- [Ollama](https://ollama.com)

### Setup

```bash
# 1. Clone
git clone https://github.com/Ankush-Patil99/upsc-ai-test-series.git
cd upsc-ai-test-series

# 2. Start PostgreSQL + pgvector
docker-compose up -d

# 3. Pull the model
ollama pull llama3.1:8b

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
uvicorn api.main:app --reload

# UI:   http://localhost:8000/ui
# Docs: http://localhost:8000/docs
```

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

| Test | What it Verifies |
|---|---|
| `test_health_check` | Root endpoint returns `{"status": "operational"}` |
| `test_authentication_register` | Register endpoint returns a JWT token |
| `test_authentication_login` | Login returns token with correct email |
| `test_unauthorized_access` | Protected routes reject unauthenticated requests (HTTP 401) |

> Tests run against a lightweight mock app and validate HTTP contracts without requiring a live PostgreSQL or Ollama instance — suitable for CI environments.

---

## ⚙️ CI/CD Pipeline

**Trigger:** Every push and pull request to `main`.

```
Push to main
    │
    ▼
Stage 1: Test
    ├── Set up Python 3.11
    ├── Cache pip dependencies
    └── Run: python -m pytest tests/ -v
    │
    ▼ (push to main only, after tests pass)
Stage 2: Build
    └── docker build -t upsc-test-series:ci-check .
```

**Current CI does:**
- ✅ Run 4 pytest tests
- ✅ Verify Docker image compiles

**Current CI does not:**
- Push image to Docker Hub
- Deploy to EC2

The next stage (Docker Hub push + EC2 SSH deploy via `appleboy/ssh-action`) is designed and `deploy.sh` is production-ready. Pending: provisioning `DOCKERHUB_TOKEN` and `EC2_SSH_KEY` as GitHub repository secrets.

---

## 📈 LangSmith Tracing

Tracing is conditionally enabled at startup:

```python
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "upsc-test-series")
```

| Environment | Status |
|---|---|
| **Local** | ✅ Active — `LANGCHAIN_API_KEY` configured in `.env` |
| **Production** | Not configured (EC2 not yet deployed) |

Every LangGraph run is traced with full latency breakdown and token counts. The critique output (PASS / HALLUCINATED) is returned in the API response as `critique_trace` and visible in LangSmith run logs.

---

## ⏱️ Performance

### End-to-End MCQ Generation Latency

Measured on: **RTX 5050 8GB VRAM · Ollama + Llama 3.1 8B · FastAPI dev server**

| Run | Latency |
|---|---|
| Run 1 | 32.57s |
| Run 2 | 31.40s |
| Run 3 | 26.74s |
| **Average** | **30.24s** |

### What the 30s Includes

```
pgvector similarity search  (k=4 facts + k=3 PYQs)
    → Llama 3.1 8B Draft generation          (LLM call #1)
    → Llama 3.1 8B Critique evaluation       (LLM call #2)
    → Re-draft if hallucination detected     (up to 3 loops)
```

Two sequential 8B model calls on a single GPU accounts for the latency.

### Production Path

Replace local Ollama with **Groq API**. Expected latency: **< 2 seconds**. `GROQ_API_KEY` is stored in `.env` — swapping `ChatOllama` for `ChatGroq` in `generator.py` is a one-line configuration change.

> **Note for users:** This is background batch generation latency. MCQs are pre-generated and stored in the database. Users loading an exam see **zero generation wait time**.

---

## ☁️ Deployment

### Infrastructure (Ready)

| Artifact | Status | Purpose |
|---|---|---|
| `Dockerfile` | ✅ Written & tested | Production FastAPI container |
| `docker-compose.prod.yml` | ✅ Written | Two-service stack: FastAPI + PostgreSQL/pgvector |
| `deploy.sh` | ✅ Written | Full EC2 bootstrap: Docker install, repo clone, pgvector extension |
| CI/CD push + deploy stage | 🔧 Designed, not wired | Awaiting GitHub secrets |

### Manual Deployment

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP> 'bash -s' < deploy.sh
```

### Cloud Constraint

The primary constraint is the LLM, not the infrastructure:

- **t2.micro** (free tier) — 1 vCPU, 1GB RAM — cannot run Llama 3.1 8B
- **g4dn.xlarge** (NVIDIA T4, 16GB VRAM) — ~$0.52/hr — sufficient but not free tier
- **Solution:** Swap inference to Groq API for cloud deployment. The rest of the stack (FastAPI + PostgreSQL + pgvector) runs on any `t3.medium`+ instance.

---

## 📌 Current Status

### Working End-to-End

- ✅ User registration, login, Google Sign-In, JWT, rate limiting
- ✅ CBT exam frontend — attempt, submit, analytics
- ✅ LangGraph RAG pipeline (Retrieve → Draft → Critique)
- ✅ APScheduler 24hr ingestion trigger
- ✅ LangSmith tracing (local)
- ✅ Docker build verified in CI

### Scrapers

| Source | Status |
|---|---|
| The Hindu (RSS) | ✅ Live |
| Indian Express (RSS) | ✅ Live |
| ForumIAS 9PM | ✅ Live |
| Drishti IAS | ⚠️ Partial |
| VisionIAS | 🔧 Scaffolded |
| InsightsIAS | 🔧 Scaffolded |
| PIB | 🔧 Stubbed |
| PRS Legislative | 🔧 Stubbed |

### Planned

- Docker Hub push + EC2 deploy in CI/CD
- Groq API swap for cloud inference
- Complete remaining scraper implementations
- Persistent token blacklist (Redis)

---

## 📄 License

MIT License — built as a portfolio and learning project.
