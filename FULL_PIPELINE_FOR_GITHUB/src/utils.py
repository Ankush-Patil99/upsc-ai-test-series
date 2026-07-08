"""
utils.py — Shared utility functions used across multiple pipeline nodes.
"""
import random
import string
import json
import logging
import re
import sqlite3
from pathlib import Path

def setup_logger(name: str):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(str(log_dir / f"{name.split('.')[-1]}.log"), mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))
        logger.addHandler(fh)
    return logger

logger = setup_logger(__name__)

def shuffle_options(correct_answer: str, distractors: list[str]) -> dict:
    all_options = [correct_answer] + distractors[:3]
    random.shuffle(all_options)
    labels = list(string.ascii_uppercase[:4])
    options_dict = {labels[i]: all_options[i] for i in range(4)}
    correct_label = next(label for label, text in options_dict.items() if text == correct_answer)
    return {"options": options_dict, "correct_option": correct_label}

def parse_json_response(raw: str, required_keys: list[str] = None) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    try:
        data = json.loads(cleaned)
        if required_keys:
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required key: '{key}'")
        return data
    except Exception as e:
        logger.warning(f"[utils] JSON parse failed: {e}. Raw: {raw[:300]}")
        return {}

def update_topic_coverage(topic: str, subtopic: str, kb_base_dir: str):
    import os
    coverage_path = os.path.join(kb_base_dir, "topic_coverage.json")
    key = f"{topic}::{subtopic}"
    try:
        if os.path.exists(coverage_path):
            with open(coverage_path, "r", encoding="utf-8") as f:
                coverage = json.load(f)
        else:
            coverage = {}
        coverage[key] = coverage.get(key, 0) + 1
        with open(coverage_path, "w", encoding="utf-8") as f:
            json.dump(coverage, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[utils] Failed to update topic coverage: {e}")

def log_qa_to_db(state: dict, sqlite_db_path: str, pipeline_version: str,
                 heavy_model: str, light_model: str):
    """Writes a QA log entry to SQLite instead of Postgres."""
    try:
        fq = state.get("formatted_question") or {}
        conn = sqlite3.connect(sqlite_db_path)
        with conn:
            cur = conn.cursor()
            # Auto-create table if it doesn't exist yet
            cur.execute("""
                CREATE TABLE IF NOT EXISTS qa_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id TEXT, topic TEXT, subtopic TEXT, paper TEXT,
                    difficulty TEXT, question_type TEXT, qa_score REAL,
                    approved INTEGER, retry_count INTEGER, qa_flags TEXT,
                    model_heavy TEXT, model_light TEXT, pipeline_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO qa_logs (
                    question_id, topic, subtopic, paper, difficulty, question_type,
                    qa_score, approved, retry_count, qa_flags,
                    model_heavy, model_light, pipeline_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fq.get("id", "unknown"),
                state.get("topic", ""),
                state.get("subtopic", ""),
                state.get("paper", ""),
                state.get("difficulty", ""),
                state.get("question_type", ""),
                state.get("qa_score", 0.0),
                state.get("approved", False),
                state.get("retry_count", 0),
                json.dumps(state.get("qa_flags", [])),
                heavy_model,
                light_model,
                pipeline_version,
            ))
        conn.close()
    except Exception as e:
        logger.warning(f"[utils] Failed to write qa_log: {e}")
