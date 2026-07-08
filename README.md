# 🎯 UPSC AI Test Series — Production-Grade LLM Platform

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100-009688?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-RAG_Pipeline-orange)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)
![AWS](https://img.shields.io/badge/AWS-EC2_Deployed-FF9900?logo=amazonaws)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=githubactions)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql)
![LangSmith](https://img.shields.io/badge/LangSmith-LLMOps_Traced-1C3C3C)

> A **full-stack AI-powered exam preparation platform** that generates contextual UPSC MCQs using a self-correcting LangGraph RAG pipeline, served via FastAPI, backed by pgvector, and deployed on AWS with a complete CI/CD pipeline.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     GitHub Actions CI/CD                      │
│  ┌──────────┐    ┌───────────┐    ┌────────────────────────┐ │
│  │  PyTest   │───▶│ Docker    │───▶│  AWS EC2 (t2.micro)   │ │
│  │  Suite    │    │ Hub Push  │    │  ┌──────────────────┐  │ │
│  └──────────┘    └───────────┘    │  │  FastAPI + Docker │  │ │
│                                   │  └────────┬─────────┘  │ │
│                                   │           │             │ │
│                                   │  ┌────────▼─────────┐  │ │
│                                   │  │ PostgreSQL +      │  │ │
│                                   │  │ pgvector (384d)   │  │ │
│                                   │  └──────────────────┘  │ │
│                                   └────────────────────────┘ │
│                                                              │
│  ┌──────────────┐          ┌─────────────────────────┐       │
│  │  LangSmith   │◀─────── │  LangGraph 3-Node RAG   │       │
│  │  (LLMOps)    │          │  Retrieve → Draft →     │       │
│  │              │          │  AI Critique (Self-Fix)  │       │
│  └──────────────┘          └─────────────────────────┘       │
│                                                              │
│  ┌──────────────┐          ┌─────────────────────────┐       │
│  │  Ollama      │◀─────── │  Local GPU Inference     │       │
│  │  Llama 3.1   │          │  RTX 5050 (8GB VRAM)    │       │
│  └──────────────┘          └─────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

| Feature | Tech | Description |
|---|---|---|
| **LangGraph RAG Pipeline** | LangGraph + Ollama | 3-node state machine: `Retrieve → Draft → AI Critique` with hallucination self-correction loop |
| **Local GPU Inference** | Ollama + Llama 3.1 8B | Zero API costs — runs entirely on laptop GPU (RTX 5050, 8GB VRAM) |
| **pgvector Embeddings** | PostgreSQL + pgvector | 384-dimensional sentence-transformer embeddings for semantic similarity search |
| **JWT + OAuth2 Auth** | bcrypt + python-jose | Secure authentication with Google Sign-In, bcrypt hashing, and sliding-window rate limiting |
| **CI/CD Pipeline** | GitHub Actions | Automated PyTest → Docker Build → Push on every commit to `main` |
| **LLMOps Tracing** | LangSmith | Full observability: latency, token usage, hallucination tracking per LangGraph run |
| **Containerized Deployment** | Docker + Docker Compose | Production `Dockerfile` + `docker-compose.prod.yml` for one-command AWS deployment |
| **24hr Auto-Scraping** | APScheduler + BeautifulSoup | Scrapes 7 news sources daily, embeds articles, and auto-generates fresh MCQs |
| **CBT Exam Frontend** | Vanilla HTML/CSS/JS | 242KB interactive exam UI with timer, subject tabs, and real-time score analytics |

---

## 🚀 Quick Start

### Local Development (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/Ankush-Patil99/upsc-ai-test-series.git
cd upsc-ai-test-series

# 2. Start PostgreSQL + pgvector
docker-compose up -d

# 3. Install Ollama and pull the model
ollama run llama3.1:8b

# 4. Install dependencies and run
pip install -r requirements.txt
uvicorn api.main:app --reload

# 5. Open the UI
# → http://localhost:8000/ui
```

### Production Deployment (AWS EC2)

```bash
# One-command deploy to a fresh EC2 instance
ssh -i your-key.pem ubuntu@<EC2_IP> 'bash -s' < deploy.sh
```

---

## 🧪 Testing

```bash
# Run the full PyTest suite
python -m pytest tests/ -v
```

| Test | What it verifies |
|---|---|
| `test_health_check` | API is up and responding |
| `test_frontend_routes` | UI is correctly mounted and served |
| `test_authentication_flow` | Full register → login → token validation flow |
| `test_unauthorized_access` | Protected routes reject unauthenticated requests |

---

## 📁 Project Structure

```
├── api/
│   ├── main.py              # FastAPI app — 30+ endpoints, auth, middleware
│   ├── auth.py              # JWT + bcrypt + OAuth2 authentication
│   └── models.py            # SQLAlchemy ORM models + pgvector columns
├── src/
│   ├── mcq_generation/
│   │   └── generator.py     # LangGraph 3-node RAG pipeline (Retrieve → Draft → AI Critique)
│   ├── agents/
│   │   ├── scraper.py       # 7-source news scraper (The Hindu, PIB, etc.)
│   │   ├── classifier.py    # Ollama-powered UPSC subject classifier
│   │   └── updater.py       # pgvector semantic deduplication + insert
│   └── ingestion/           # PDF book ingestion pipeline
├── frontend/
│   ├── index.html           # CBT exam interface (92KB)
│   ├── app.js               # Full exam logic (242KB)
│   └── style.css            # Custom responsive styling
├── tests/
│   └── test_api.py          # PyTest integration suite
├── configs/
│   └── settings.yaml        # Model and DB configuration
├── .github/workflows/
│   └── ci-cd.yml            # GitHub Actions: Test → Build → Push
├── Dockerfile               # Production container image
├── docker-compose.yml        # Local development stack
├── docker-compose.prod.yml   # Production deployment stack
├── deploy.sh                 # AWS EC2 one-command deployment script
└── requirements.txt
```

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Uvicorn, Python 3.11 |
| **AI/LLM** | LangGraph, LangChain, Ollama (Llama 3.1 8B) |
| **Database** | PostgreSQL + pgvector (384d embeddings) |
| **Auth** | JWT (python-jose), bcrypt, Google OAuth2 |
| **Ops** | Docker, Docker Compose, GitHub Actions CI/CD |
| **Monitoring** | LangSmith (LLMOps), APScheduler (Cron) |
| **Cloud** | AWS EC2 (t2.micro free tier) |
| **Frontend** | Vanilla HTML/CSS/JS (no framework overhead) |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
