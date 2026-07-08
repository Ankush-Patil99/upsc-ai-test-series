"""
node_4_engineer.py — Node 4: Distractor Engineer (Wrong Answer Specialist)

Responsibilities (from blueprint Section 4 — Node 4):
  - Generates exactly 3 plausible but WRONG answer options (distractors)
  - Based on common UPSC misconceptions and knowledge gaps
  - Distractor types: partial truths, date transpositions, reversed cause-effect,
    confused similar entities
  - Shuffles all 4 options (correct + 3 distractors) and assigns A/B/C/D labels
  - Quality gates enforced via prompt rules (no duplicates, no absurd options)

LLM used: Mistral-7B-Instruct (light endpoint — fast, sufficient for this task)
"""

import json
import logging
import re

from src.state import QuestionState
from src.llm_client import call_light
from src.utils import shuffle_options

from src.utils import setup_logger
logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# System prompt for Mistral-7B
# ─────────────────────────────────────────────────────────────────────────────
ENGINEER_SYSTEM_PROMPT = """You are a UPSC distractor specialist. Your job is to create exactly 3 plausible but WRONG answer options for the given MCQ.

CRITICAL FORMATTING RULES:
1. MATCH THE EXACT STYLE AND LENGTH OF THE CORRECT ANSWER. Do NOT over-explain. Be extremely concise.
2. If the question is "statement_based" (e.g., correct answer is a code like "1 and 2 only", "1, 2 and 3"), your distractors MUST BE EXACTLY CODES! (e.g. "2 and 3 only", "1 only"). NEVER write logic or sentences in statement-based options.
3. NEVER repeat the question stem or the correct answer inside your distractors.

DISTRACTOR CREATION RULES (for factual/analytical questions):
1. Plausibility: A well-prepared aspirant should genuinely hesitate.
2. Strategies: Use partial truths (change one date/name), swapped concepts, or reversed cause-and-effect.
3. FORBIDDEN: Do not create absurd options. Do not add "All of the above" or "None of the above".

Respond ONLY in this exact JSON format — no markdown, no extra text:
{
  "distractor_1": "Text of wrong option 1",
  "distractor_2": "Text of wrong option 2",
  "distractor_3": "Text of wrong option 3"
}"""


def _build_engineer_prompt(state: QuestionState) -> str:
    return f"""Generate 3 plausible WRONG answer options (distractors) for the following UPSC MCQ.

Question Type  : {state.get('question_type', 'factual')}
Question Stem  : {state.get('question_stem', '')}
Correct Answer : {state.get('correct_answer', '')}
Explanation    : {state.get('explanation', '')}
Topic          : {state.get('topic', '')}
Difficulty     : {state.get('difficulty', 'medium')}

Based on common UPSC misconceptions about this topic, generate 3 distractors that
a well-prepared aspirant might still get confused about. Follow the rules strictly."""


def _parse_engineer_response(raw: str) -> list[str]:
    """Parses Mistral's JSON response and returns a list of 3 distractor strings."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")

    try:
        data = json.loads(cleaned)
        distractors = [
            data.get("distractor_1", "").strip(),
            data.get("distractor_2", "").strip(),
            data.get("distractor_3", "").strip(),
        ]
        # Filter out empty strings
        distractors = [d for d in distractors if d]
        if len(distractors) == 3:
            return distractors
        raise ValueError(f"Expected 3 distractors, got {len(distractors)}")
    except Exception as e:
        logger.warning(f"[Node4] JSON parse failed: {e}. Attempting regex fallback.")
        matches = re.findall(r'"distractor_\d"\s*:\s*"(.*?)"', raw, re.DOTALL)
        if len(matches) >= 3:
            return [m.strip() for m in matches[:3]]

        # Last resort: split by newlines and take non-empty lines
        lines = [l.strip() for l in raw.split("\n") if l.strip() and len(l.strip()) > 10]
        return lines[:3] if len(lines) >= 3 else []



def distractor_engineer_node(state: QuestionState) -> dict:
    """
    LangGraph Node 4 — Distractor Engineer.
    Returns partial state update with 'distractors' (list of 3 strings).
    """
    logger.info(f"[Node4] Generating distractors for: '{state.get('question_stem', '')[:80]}...'")

    if not state.get("question_stem") or not state.get("correct_answer"):
        logger.error("[Node4] Missing question_stem or correct_answer. Skipping distractor generation.")
        return {
            "distractors": [],
            "qa_flags": (state.get("qa_flags") or []) + ["missing_stem_or_answer_for_distractor"],
        }

    user_prompt = _build_engineer_prompt(state)

    try:
        raw_response = call_light(ENGINEER_SYSTEM_PROMPT, user_prompt)
        logger.info(f"[Node4] Raw response length: {len(raw_response)} chars.")
    except Exception as e:
        logger.error(f"[Node4] Mistral-7B call failed: {e}")
        return {
            "distractors": [],
            "qa_flags": (state.get("qa_flags") or []) + ["distractor_llm_error"],
        }

    distractors = _parse_engineer_response(raw_response)

    if len(distractors) < 3:
        logger.warning(f"[Node4] Only got {len(distractors)} distractors. Expected 3.")
        return {
            "distractors": distractors,
            "qa_flags": (state.get("qa_flags") or []) + ["insufficient_distractors"],
        }

    logger.info(f"[Node4] 3 distractors generated successfully.")
    return {
        "distractors": distractors,
    }
