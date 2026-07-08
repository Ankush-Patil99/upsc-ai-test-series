"""
node_1_controller.py — Node 1: Input Controller (Intake & Routing)

Responsibilities (from blueprint Section 4 — Node 1):
  - Validates topic/subtopic against UPSC syllabus taxonomy
  - Expands vague topics into specific, testable subtopics (via Mistral-7B)
  - Assigns EXACT UPSC syllabus tags via `src.syllabus_tagger`
    (tags are the exact words from the GS1/GS2/GS3 PDFs — no LLM-invented labels)
  - Multiple tags are allowed if the question spans multiple syllabus topics
  - Initialises retry_count = 0 and all state fields to None/defaults
  - Reads topic_coverage.json to prioritize under-generated subtopics

LLM used: Mistral-7B-Instruct (light endpoint) — only for subtopic refinement
"""

import json
import logging
from datetime import datetime, timezone

from src.state import QuestionState
from src.llm_client import call_light
from src.kb_loader import get_coverage_tracker
from src.syllabus_tagger import tag_question

from src.utils import setup_logger
logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Valid UPSC taxonomy
# ─────────────────────────────────────────────────────────────────────────────
VALID_PAPERS = {"GS1", "GS2", "GS3", "GS4", "CSAT"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_QUESTION_TYPES = {
    "factual", "analytical", "current_affairs",
    "statement_based", "match_following", "assertion_reasoning",
    "correct_incorrect", "most_appropriate",
}

# ─────────────────────────────────────────────────────────────────────────────
# System prompt — ONLY for subtopic refinement now (NOT for tags)
# ─────────────────────────────────────────────────────────────────────────────
CONTROLLER_SYSTEM_PROMPT = """You are a UPSC syllabus expert. Given a topic and subtopic, refine the subtopic into the most specific, testable angle for a single MCQ question.

Respond ONLY in the following JSON format with no extra text:
{
  "refined_subtopic": "The refined, specific subtopic as a single sentence"
}"""


def _validate_inputs(state: QuestionState) -> list[str]:
    """Returns a list of validation errors, empty if all valid."""
    errors = []
    if state.get("paper") not in VALID_PAPERS:
        errors.append(f"Invalid paper '{state.get('paper')}'. Must be one of {VALID_PAPERS}.")
    if state.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"Invalid difficulty '{state.get('difficulty')}'. Must be one of {VALID_DIFFICULTIES}.")
    if state.get("question_type") not in VALID_QUESTION_TYPES:
        errors.append(f"Invalid question_type '{state.get('question_type')}'. Must be one of {VALID_QUESTION_TYPES}.")
    if not state.get("topic", "").strip():
        errors.append("Topic cannot be empty.")
    if not state.get("subtopic", "").strip():
        errors.append("Subtopic cannot be empty.")
    return errors


def _check_coverage(topic: str, subtopic: str) -> int:
    """Returns current question count for this subtopic from coverage tracker."""
    tracker = get_coverage_tracker()
    key = f"{topic}::{subtopic}"
    return tracker.get(key, 0)


def _refine_subtopic(topic: str, subtopic: str, paper: str) -> str:
    """
    Calls Mistral-7B ONLY to refine the subtopic into the most specific
    testable angle. Tags are now derived from syllabus PDFs — not from the LLM.
    """
    user_prompt = (
        f"UPSC Paper: {paper}\n"
        f"Topic: {topic}\n"
        f"Subtopic: {subtopic}\n\n"
        f"Refine the subtopic into a highly SPECIFIC, OBSCURE, or UNIQUE testable angle for one MCQ. "
        f"Do NOT just pick the most common or obvious aspect. Dive into a very specific nook of this topic to guarantee 100% variety."
    )

    raw = call_light(CONTROLLER_SYSTEM_PROMPT, user_prompt)

    try:
        cleaned = raw.strip().strip("```json").strip("```").strip()
        result  = json.loads(cleaned)
        refined = result.get("refined_subtopic", "").strip()
        return refined if refined else subtopic
    except Exception as e:
        logger.warning(f"[Node1] Failed to parse LLM subtopic response: {e}. Keeping original.")
        return subtopic


def input_controller_node(state: QuestionState) -> dict:
    """
    LangGraph Node 1 — Input Controller.
    Returns a partial state update dict (LangGraph merges it automatically).
    """
    logger.info(
        f"[Node1] Starting Input Controller for "
        f"topic='{state.get('topic')}' paper='{state.get('paper')}'"
    )

    # ── Step 1: Validate inputs ──────────────────────────────────────────────
    errors = _validate_inputs(state)
    if errors:
        error_msg = " | ".join(errors)
        logger.error(f"[Node1] Validation failed: {error_msg}")
        return {
            "tags": [],
            "retry_count": 0,
            "approved": False,
            "qa_flags": [f"validation_error: {error_msg}"],
            "qa_score": 0.0,
            "research_context": None,
            "question_stem": None,
            "correct_answer": None,
            "distractors": None,
            "explanation": None,
            "formatted_question": None,
            "difficulty_score": None,
            "estimated_time_seconds": None,
        }

    # ── Step 2: Coverage check (warn if over-generated subtopic) ─────────────
    coverage_count = _check_coverage(state["topic"], state["subtopic"])
    if coverage_count > 10:
        logger.warning(
            f"[Node1] Subtopic '{state['subtopic']}' already has {coverage_count} questions. "
            f"Consider diversifying topics."
        )

    # ── Step 3: Refine subtopic via Mistral-7B ────────────────────────────────
    refined_subtopic = _refine_subtopic(state["topic"], state["subtopic"], state["paper"])
    logger.info(f"[Node1] Refined subtopic: '{refined_subtopic}'")

    # ── Step 4: Assign EXACT UPSC syllabus tags from PDFs ────────────────────
    # tag_question() reads GS1/GS2/GS3 PDFs and returns the exact phrases
    # from the official UPSC Mains syllabus that match this question.
    # Multiple tags are returned if the question spans multiple syllabus areas.
    tags = tag_question(
        topic=state["topic"],
        subtopic=refined_subtopic,
        question_stem="",         # stem not yet generated at Node 1
        paper=state.get("paper", ""),
    )
    logger.info(f"[Node1] Syllabus tags assigned ({len(tags)}): {tags}")

    # ── Step 5: Return initialised state ─────────────────────────────────────
    return {
        "subtopic":    refined_subtopic,
        "tags":        tags,
        "retry_count": state.get("retry_count", 0),
        "approved":    False,
        "qa_score":    None,
        "qa_flags":    [],
        # Initialise all generated fields to None
        "research_context":       None,
        "question_stem":          None,
        "correct_answer":         None,
        "distractors":            None,
        "explanation":            None,
        "formatted_question":     None,
        "difficulty_score":       None,
        "estimated_time_seconds": None,
    }

