# Docs — Project Documentation

---

## Files

### project_summary.txt (root level)
Architecture and engineering decisions summary — covers both pipeline phases,
why local inference was chosen over cloud APIs, and all measured performance numbers.

### PROJECT_OVERVIEW.txt
Detailed breakdown of each current affairs source (scraping method, status),
all API endpoints, and the database schema with table descriptions.

### pipeline.txt
Complete end-to-end pipeline specification — from data ingestion through
LangGraph MCQ generation to FastAPI serving. Documents every endpoint,
every DB table, and the full deployment checklist.

### Question generation.txt
Prompt templates and output schema used by the LangGraph Drafter node
for MCQ generation. Includes the JSON structure expected from Llama 3.1 8B.

### aws_architecture.jpg
Architecture diagram showing the planned AWS EC2 deployment topology —
FastAPI container, PostgreSQL/pgvector, and the Ollama inference layer.

---

## What Lives Elsewhere

- Core pipeline code: src/mcq_generation/generator.py
- API routes: api/main.py
- Authentication: api/auth.py
- Ingestion agents: src/agents/
- Dev utility scripts: scripts/
