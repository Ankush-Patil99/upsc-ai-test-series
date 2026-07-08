"""
kb_loader.py — Loads the Static Knowledge Base JSON files into memory once.
Used by Node 2 (Content Researcher) and Node 6 (QA Orchestrator).
"""
import json
import logging
from pathlib import Path
from src.config import SYLLABUS_MAP_PATH, UPSC_FACTS_PATH, COVERAGE_TRACKER

from src.utils import setup_logger
logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Lazy singletons — loaded once per process
# ─────────────────────────────────────────────────────────────────────────────
_syllabus_map:     dict | None = None
_upsc_facts:       dict | None = None
_coverage_tracker: dict | None = None


def _load_json(path: str, label: str) -> dict:
    p = Path(path)
    if not p.exists():
        logger.warning(f"[KB] {label} not found at {path}. Returning empty dict.")
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def get_syllabus_map() -> dict:
    """UPSC subject → topic → subtopics taxonomy."""
    global _syllabus_map
    if _syllabus_map is None:
        _syllabus_map = _load_json(SYLLABUS_MAP_PATH, "syllabus_map")
    return _syllabus_map


def get_upsc_facts() -> dict:
    """Verified UPSC facts: constitutional articles, acts, key dates etc."""
    global _upsc_facts
    if _upsc_facts is None:
        _upsc_facts = _load_json(UPSC_FACTS_PATH, "upsc_facts")
    return _upsc_facts


def get_coverage_tracker() -> dict:
    """Tracks question count per subtopic to prevent over-generation."""
    global _coverage_tracker
    if _coverage_tracker is None:
        _coverage_tracker = _load_json(COVERAGE_TRACKER, "topic_coverage")
    return _coverage_tracker


def lookup_facts_for_topic(topic: str, subtopic: str) -> str:
    """
    Returns a formatted string of all KB facts relevant to the given topic/subtopic.
    Used as grounding material by Node 2 before calling the LLM.
    """
    facts = get_upsc_facts()
    relevant = []

    # Search for facts whose 'topic' key partially matches
    for key, entry in facts.items():
        entry_topic = entry.get("topic", "").lower()
        entry_sub   = entry.get("subtopic", "").lower()
        if topic.lower() in entry_topic or subtopic.lower() in entry_sub:
            relevant.append(
                f"- [{key}] {entry.get('fact', '')} "
                f"(Source: {entry.get('source', 'KB')})"
            )

    if not relevant:
        return f"No static KB entries found for topic: '{topic} / {subtopic}'."
    return "\n".join(relevant)
