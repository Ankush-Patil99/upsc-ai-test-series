"""
config.py — Central configuration for the UPSC AI Engine V2.0
All vLLM endpoints, model names, thresholds, and paths live here.
Loads from .env file automatically via python-dotenv.
"""
import os
from pathlib import Path

# Load .env from the project root (one level up from src/)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # dotenv optional — falls back to environment variables

# ─────────────────────────────────────────────────────────────────────────────
# Database connections
# ─────────────────────────────────────────────────────────────────────────────
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./pipeline_data/upscdb.sqlite3")

# ─────────────────────────────────────────────────────────────────────────────
# vLLM API Endpoints
# ─────────────────────────────────────────────────────────────────────────────
VLLM_HEAVY_BASE_URL = os.getenv("VLLM_HEAVY_BASE_URL", "http://localhost:8001/v1")
VLLM_LIGHT_BASE_URL = os.getenv("VLLM_LIGHT_BASE_URL", "http://localhost:8002/v1")

HEAVY_MODEL_NAME = os.getenv("HEAVY_MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct-AWQ")
LIGHT_MODEL_NAME = os.getenv("LIGHT_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.3")

# ─────────────────────────────────────────────────────────────────────────────
# Embedding & RAG Config
# ─────────────────────────────────────────────────────────────────────────────
RAG_EMBED_MODEL     = os.getenv("RAG_EMBED_MODEL", "/home/scai/mtech/aib242291/UPSC_Test_Agent/models/bge-large")
DEDUP_EMBED_MODEL   = os.getenv("DEDUP_EMBED_MODEL", "/home/scai/mtech/aib242291/UPSC_Test_Agent/models/bge-small")

CHROMA_PERSIST_DIR  = os.getenv("CHROMA_PERSIST_DIR", "./pipeline_data/chroma_db")
CHROMA_COLLECTION   = os.getenv("CHROMA_COLLECTION", "upsc_questions") 
CHROMA_RAG_COLLECTION = os.getenv("CHROMA_RAG_COLLECTION", "upsc_knowledge")
DEDUP_THRESHOLD     = float(os.getenv("DEDUP_THRESHOLD", 0.95))

# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base Paths
# ─────────────────────────────────────────────────────────────────────────────
KB_BASE_DIR       = os.getenv("KB_BASE_DIR", "./pipeline_data/static_kb")
SYLLABUS_MAP_PATH = f"{KB_BASE_DIR}/syllabus_map.json"
UPSC_FACTS_PATH   = f"{KB_BASE_DIR}/upsc_facts.json"
COVERAGE_TRACKER  = f"{KB_BASE_DIR}/topic_coverage.json"

# ─────────────────────────────────────────────────────────────────────────────
# LangGraph Config
# ─────────────────────────────────────────────────────────────────────────────
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "./pipeline_data/checkpoints/pipeline.db")
OUTPUT_DIR         = os.getenv("OUTPUT_DIR", "./pipeline_data/output")

# ─────────────────────────────────────────────────────────────────────────────
# QA Thresholds
# ─────────────────────────────────────────────────────────────────────────────
QA_PASS_THRESHOLD = float(os.getenv("QA_PASS_THRESHOLD", 0.75))
MAX_RETRIES       = int(os.getenv("MAX_RETRIES", 3))

# ─────────────────────────────────────────────────────────────────────────────
# Generation Params
# ─────────────────────────────────────────────────────────────────────────────
HEAVY_MAX_TOKENS = int(os.getenv("HEAVY_MAX_TOKENS", 2048))
LIGHT_MAX_TOKENS = int(os.getenv("LIGHT_MAX_TOKENS", 1024))
TEMPERATURE      = float(os.getenv("TEMPERATURE", 0.7))

PGV_TOP_K_CA       = int(os.getenv("PGV_TOP_K_CA", 5))
PGV_TOP_K_TEXTBOOK = int(os.getenv("PGV_TOP_K_TEXTBOOK", 3))

PIPELINE_VERSION = "V2.0.1"
