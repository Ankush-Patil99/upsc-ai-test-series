# 🚀 UPSC AI Platform

> **Self-Correcting RAG Pipeline for Automated UPSC Question Generation**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-RAG-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-blue?logo=githubactions)
![LangSmith](https://img.shields.io/badge/LangSmith-Tracing-black)

A full-stack AI exam platform that automates current affairs ingestion, semantic retrieval, and contextual MCQ generation for UPSC Prelims aspirants using a self-correcting LangGraph RAG pipeline.

---

# 📚 Table of Contents

- Overview
- Problem Statement
- Target Users
- Key Features
- System Workflow
- Design Evolution
- Retrieval & Embedding
- LLM Configuration
- Tech Stack
- Project Structure
- Usage
- Testing
- CI Pipeline
- LangSmith
- Performance
- Current Status

---

# 📖 Overview

The platform automatically scrapes UPSC current affairs sources, embeds the collected content into PostgreSQL + pgvector, retrieves relevant context using semantic search, and generates contextual MCQs through a self-correcting LangGraph pipeline powered by a locally hosted Llama 3.1 model.

---

# 🎯 Problem Statement

Manual collection of daily current affairs is repetitive and time-consuming.

This project automates:

Current Affairs Ingestion
→ Embedding
→ Retrieval
→ Contextual MCQ Generation

---

# 👥 Target Users

- UPSC Prelims Aspirants

---

# ✨ Key Features

- 🤖 Self-correcting LangGraph RAG pipeline
- 🧠 Local Llama 3.1 inference using Ollama
- 🔎 Semantic retrieval using pgvector
- 🔐 JWT authentication with bcrypt
- 🌐 Google Sign-In support
- 📝 CBT exam frontend built using Vanilla HTML/CSS/JavaScript
- 📊 Analytics endpoint
- 🐳 Dockerized application
- ✅ GitHub Actions CI verification
- 📈 LangSmith tracing during local execution

---

# 🔄 System Workflow

Daily News Sources
→ Ingestion
→ Embedding
→ PostgreSQL + pgvector
→ Retrieve
→ Draft
→ Critique
→ Contextual MCQ
→ FastAPI
→ CBT Frontend

---

# 🏗️ Design Evolution

## Original Design

Scrape
→ Classify
→ Chunk & Embed
→ Retrieve
→ Draft
→ Critique
→ Difficulty Calibration
→ Format

## Final Design

Retrieve
→ Draft
→ Critique

Maximum of three self-correction iterations.

### Engineering Decisions

- Classifier node moved into the ingestion pipeline after GPU OOM errors.
- Difficulty calibration removed because three sequential LLM calls exhausted VRAM.
- Multi-model cascade removed because disk swapping (~45 seconds) made inference impractical.
- Embedding node removed after embedding was moved into the ingestion pipeline.

---

# 🔍 Retrieval & Embedding

| Parameter | Value |
|-----------|-------|
| Embedding Model | all-MiniLM-L6-v2 |
| Dimensions | 384 |
| Vector Store | PostgreSQL + pgvector |
| Chunk Size | 1200 characters |
| Chunk Overlap | 200 characters |
| Splitter | RecursiveCharacterTextSplitter |
| Dedup Threshold | L2 distance < 0.15 |
| Retrieval | k=4 facts + k=3 PYQs |

---

# 🤖 LLM Configuration

| Setting | Value |
|----------|-------|
| Model | llama3.1:8b |
| Runtime | Ollama |
| Temperature | 0.3 |
| Structured Output | No |
| JSON Mode | No |
| Parsing | Regex extraction |

---

# 🛠️ Tech Stack

| Layer | Technology |
|--------|------------|
| Backend | FastAPI |
| AI | LangGraph, Ollama, Llama 3.1 |
| Database | PostgreSQL + pgvector |
| Authentication | JWT, bcrypt, Google OAuth |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Observability | LangSmith |
| DevOps | Docker, GitHub Actions |

---

# 📂 Project Structure

```text
api/
configs/
docs/
frontend/
scripts/
src/
tests/
Dockerfile
docker-compose.yml
docker-compose.prod.yml
requirements.txt
README.md
```

---

# 🚀 Usage

## Clone

```bash
git clone <repository-url>
cd <repository-name>
```

## Start Dependencies

```bash
docker-compose up -d
```

## Run Application

```bash
uvicorn api.main:app --reload
```

---

# 🧪 Testing

Current implementation includes four pytest tests executed against a lightweight mock application.

Current tests validate route shapes only.

---

# ⚙️ GitHub Actions

Current pipeline:

1. Install Python dependencies
2. Execute four pytest tests
3. Verify Docker image builds successfully

Current pipeline does **not**:

- Push Docker images
- Deploy to EC2

---

# 📈 LangSmith

- Local tracing enabled using `LANGCHAIN_API_KEY`
- Production tracing not configured

---

# ⏱️ Performance

Average end-to-end MCQ generation time:

**30.24 seconds**

Measured runs:

- 32.57 s
- 31.40 s
- 26.74 s

Pipeline includes:

- pgvector retrieval
- Llama draft generation
- Llama critique pass

Current hardware:

RTX 5050 GPU

Planned production optimization:

Replace local inference with Groq for sub-2 second generation.

---

# 📌 Current Status

### Live

- The Hindu
- Indian Express
- ForumIAS 9PM

### Mocked / Stubbed

- Drishti IAS
- VisionIAS
- InsightsIAS
- PIB
- PRS Legislative

---

## 📄 License

This repository is intended as a portfolio and learning project.
