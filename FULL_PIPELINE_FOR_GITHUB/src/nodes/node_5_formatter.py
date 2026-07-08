"""
node_5_formatter.py — Node 5: Structure Formatter (Presentation Designer)

Responsibilities (from blueprint Section 4 — Node 5):
  - Transforms raw components into the final JSON schema the website expects
  - Assigns difficulty_score (0.0–1.0) and estimated_time_seconds
  - Calls Mistral-7B to produce a clean 2-3 line explanation for the website
  - Shuffles and assigns A/B/C/D option labels (correct answer randomized)
  - Adds pipeline metadata (generated_at, pipeline_version, id)

LLM used: Mistral-7B-Instruct (light endpoint)
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from src.state import QuestionState
from src.llm_client import call_light
from src.utils import shuffle_options
from src.config import PIPELINE_VERSION
from src.syllabus_tagger import tag_question

from src.utils import setup_logger
logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Difficulty score mapping (rule-based, no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────
DIFFICULTY_SCORE_MAP = {
    "easy":   0.25,
    "medium": 0.55,
    "hard":   0.82,
}

# ─────────────────────────────────────────────────────────────────────────────
# Estimated solving time in seconds per difficulty
# ─────────────────────────────────────────────────────────────────────────────
TIME_MAP = {
    "easy":   45,
    "medium": 75,
    "hard":   110,
}

# ─────────────────────────────────────────────────────────────────────────────
# System prompt for condensed website explanation
# ─────────────────────────────────────────────────────────────────────────────
FORMATTER_SYSTEM_PROMPT = """You are a UPSC content editor preparing question explanations for a student-facing website.
Given the full detailed explanation, write a concise 2-3 sentence version that:
1. Explicitly states WHY the correct answer is correct (key fact or principle).
2. Explains WHY the other options are incorrect, if applicable.
3. Mentions the most important supporting detail (year, article, act, etc.).
4. Is written in simple, student-friendly language.

Respond with ONLY the condensed explanation text — no JSON, no labels, no markdown."""


def _build_formatter_prompt(correct_answer: str, explanation: str) -> str:
    return f"""Condense the following UPSC explanation into 2-3 clear sentences for a student website.

Correct Answer : {correct_answer}
Full Explanation: {explanation}

Write only the condensed version:"""


def _generate_question_id(paper: str, difficulty: str) -> str:
    """Generates a unique question ID in the format Q_GS2_2026_<short_uuid>."""
    year  = datetime.now(timezone.utc).strftime("%Y")
    short = str(uuid.uuid4()).replace("-", "")[:6].upper()
    return f"Q_{paper}_{year}_{short}"


def _get_condensed_explanation(correct_answer: str, explanation: str) -> str:
    """Calls Mistral-7B to produce a 2-3 line website-ready explanation."""
    try:
        prompt = _build_formatter_prompt(correct_answer, explanation)
        result = call_light(FORMATTER_SYSTEM_PROMPT, prompt)
        return result.strip()
    except Exception as e:
        logger.warning(f"[Node5] Failed to condense explanation via LLM: {e}. Using original.")
        # Fallback: truncate to first 3 sentences
        sentences = re.split(r'(?<=[.!?])\s+', explanation.strip())
        return " ".join(sentences[:3])


def _get_analytics_subject(topic: str, subtopic: str, paper: str) -> str:
    text = (topic + " " + subtopic).lower()
    
    if "art and culture" in text or "art & culture" in text:
        return "Art and culture"
    if "histor" in text or "revolt" in text or "empire" in text or "movement" in text or "freedom struggle" in text:
        return "History"
    if "geograph" in text or "river" in text or "climate" in text or "monsoon" in text:
        return "Geography"
    if "international relation" in text or "foreign" in text or "saarc" in text or "wto" in text or "treaty" in text:
        return "International relations"
    if "polity" in text or "constitution" in text or "governance" in text or "rights" in text or "parliament" in text:
        return "Polity"
    if "econom" in text or "banking" in text or "tax" in text or "gdp" in text or "inflation" in text:
        return "Economics"
    if "environment" in text or "biodiversity" in text or "agricultur" in text or "disaster" in text or "pollution" in text or "wildlife" in text:
        return "Environment, agriculture and biodiversity"
    if "science" in text or "technolog" in text or "space" in text or "cyber" in text or "defense" in text or "health" in text:
        return "Science and technology"
        
    # Fallback to Paper heuristics
    if paper == "GS1":
        return "History"
    elif paper == "GS2":
        return "Polity"
    elif paper == "GS3":
        return "Economics"
    elif paper == "GS4":
        return "Polity"  # Ethics -> Polity for simplicity
    
    return "Polity"
def structure_formatter_node(state: QuestionState) -> dict:
    """
    LangGraph Node 5 — Structure Formatter.
    Returns partial state update with 'formatted_question', 'difficulty_score',
    'estimated_time_seconds'.
    """
    logger.info(f"[Node5] Formatting question for paper='{state.get('paper')}'")

    # ── Validate required fields exist ───────────────────────────────────────
    required = ["question_stem", "correct_answer", "distractors", "explanation"]
    for field in required:
        if not state.get(field):
            logger.error(f"[Node5] Missing required field: '{field}'")
            return {
                "formatted_question": None,
                "qa_flags": (state.get("qa_flags") or []) + [f"formatter_missing_{field}"],
            }

    distractors = state["distractors"]
    if len(distractors) < 3:
        logger.error(f"[Node5] Only {len(distractors)} distractors available. Need 3.")
        return {
            "formatted_question": None,
            "qa_flags": (state.get("qa_flags") or []) + ["formatter_insufficient_distractors"],
        }

    # ── Step 1: Shuffle options A/B/C/D ──────────────────────────────────────
    shuffled = shuffle_options(state["correct_answer"], distractors)

    # ── Step 2: Get condensed explanation for website ─────────────────────────
    condensed_explanation = _get_condensed_explanation(
        state["correct_answer"], state["explanation"]
    )

    # ── Step 3: Compute difficulty score and time ─────────────────────────────
    diff_label    = state.get("difficulty", "medium").lower()
    diff_score    = DIFFICULTY_SCORE_MAP.get(diff_label, 0.55)
    solving_time  = TIME_MAP.get(diff_label, 75)

    # ── Step 4: Re-tag using the fully generated question stem ──────────────
    # Node 1 assigned tags without the question stem (it hadn't been generated yet).
    # Now that we have the full stem, we can do a much better syllabus tag match.
    existing_tags = state.get("tags") or []
    enriched_tags = tag_question(
        topic=state.get("topic", ""),
        subtopic=state.get("subtopic", ""),
        question_stem=state.get("question_stem", ""),
        paper=state.get("paper", ""),
        max_tags=8,
    )
    # Merge: keep Node1 tags + add any new ones from stem-based matching; deduplicate
    seen_tags: set[str] = set()
    merged_tags: list[str] = []
    for t in (existing_tags + enriched_tags):
        if t.lower() not in seen_tags:
            seen_tags.add(t.lower())
            merged_tags.append(t)
    final_tags = merged_tags[:8]   # cap at 8
    logger.info(f"[Node5] Final syllabus tags ({len(final_tags)}): {final_tags}")

    # ── Step 5: Assign broad Analytics tag ───────────────────────────────────
    analytics_tag = _get_analytics_subject(
        state.get("topic", ""), 
        state.get("subtopic", ""), 
        state.get("paper", "")
    )
    
    # ── Step 6: Assemble the final website-ready JSON object ─────────────────
    question_id = _generate_question_id(state.get("paper", "GS"), diff_label)

    formatted_question = {
        "id":                    question_id,
        "question":              state["question_stem"],
        "options":               shuffled["options"],
        "correct_option":        shuffled["correct_option"],
        "explanation":           condensed_explanation,
        "full_explanation":      state["explanation"],   # stored internally
        "mains_fact":            state.get("mains_fact", ""),
        "citations":             state.get("citations", ""),
        "tags":                  final_tags,
        "analytics_subject":     analytics_tag,
        "paper":                 state.get("paper", ""),
        "difficulty":            diff_label,
        "difficulty_score":      diff_score,
        "question_type":         state.get("question_type", ""),
        "estimated_time_seconds":solving_time,
        "qa_score":              None,    # filled by Node 6
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "pipeline_version":      PIPELINE_VERSION,
    }

    logger.info(f"[Node5] Formatted question ID: {question_id} | correct_option: {shuffled['correct_option']}")

    return {
        "formatted_question":     formatted_question,
        "difficulty_score":       diff_score,
        "estimated_time_seconds": solving_time,
    }
