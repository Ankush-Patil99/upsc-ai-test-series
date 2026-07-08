"""
node_6_orchestrator.py — Node 6: QA Orchestrator (Final Auditor & Gatekeeper)
"""

import json
import logging
import re
from datetime import datetime, timezone

from src.state import QuestionState
from src.llm_client import call_heavy
from src.chroma_client import check_duplicate, add_question
from src.config import QA_PASS_THRESHOLD, MAX_RETRIES, SQLITE_DB_PATH, PIPELINE_VERSION, KB_BASE_DIR
from src.config import HEAVY_MODEL_NAME, LIGHT_MODEL_NAME
from src.utils import update_topic_coverage, log_qa_to_db

from src.utils import setup_logger
logger = setup_logger(__name__)

DIMENSION_WEIGHTS = {
    "factual_accuracy":        0.25,
    "stem_clarity":            0.20,
    "correct_answer_validity": 0.20,
    "distractor_quality":      0.15,
    "upsc_alignment":          0.10,
    "explanation_quality":     0.05,
    "format_compliance":       0.03,
    "uniqueness":              0.02,
}

RETRY_ROUTE_MAP = {
    "factual_accuracy":        "content_researcher",
    "stem_clarity":            "question_drafter",
    "correct_answer_validity": "question_drafter",
    "distractor_quality":      "distractor_engineer",
    "upsc_alignment":          "question_drafter",
    "format_compliance":       "structure_formatter",
    "explanation_quality":     "question_drafter",
    "uniqueness":              "input_controller",
}

ORCHESTRATOR_SYSTEM_PROMPT = """You are a senior UPSC question quality auditor with 20 years of experience.
Score the following MCQ across 7 quality dimensions.

For each dimension, assign a score from 0.0 (terrible) to 1.0 (excellent).
Be strict — a score above 0.75 means production-ready quality for UPSC aspirants.

Scoring guide:
- factual_accuracy:        Are all facts in the question and explanation verifiably correct?
- stem_clarity:            Is the question stem clear, unambiguous, testing a single concept?
- correct_answer_validity: Is the correct answer definitively and unambiguously correct?
- distractor_quality:      Are all 3 wrong options plausible enough to confuse a student?
- upsc_alignment:          Does the question match UPSC's style, pattern, and difficulty?
- explanation_quality:     Does the explanation clearly explain why the answer is correct?
- format_compliance:       Is the question properly formatted (no double negatives)?

Respond ONLY in this exact JSON format:
{
  "factual_accuracy":        0.0,
  "stem_clarity":            0.0,
  "correct_answer_validity": 0.0,
  "distractor_quality":      0.0,
  "upsc_alignment":          0.0,
  "explanation_quality":     0.0,
  "format_compliance":       0.0,
  "reasoning":               "Brief 2-3 sentence justification"
}"""


def _build_orchestrator_prompt(state: QuestionState) -> str:
    fq = state.get("formatted_question") or {}
    options_str = "\n".join(
        [f"  {k}: {v}" for k, v in fq.get("options", {}).items()]
    )
    correct_opt = fq.get("correct_option", "?")

    return f"""Score this UPSC MCQ across the 7 quality dimensions.

─── QUESTION ──────────────────────────────────────────────────────────────────
{state.get('question_stem', '')}

Options:
{options_str}

Correct Option : {correct_opt}
Correct Answer : {state.get('correct_answer', '')}

─── EXPLANATION ───────────────────────────────────────────────────────────────
{state.get('explanation', '')}

─── RESEARCH CONTEXT USED ─────────────────────────────────────────────────────
{(state.get('research_context') or '')[:800]}

─── METADATA ──────────────────────────────────────────────────────────────────
Paper          : {state.get('paper', '')}
Difficulty     : {state.get('difficulty', '')}
Question Type  : {state.get('question_type', '')}
Topic          : {state.get('topic', '')} / {state.get('subtopic', '')}

Now score all 7 dimensions and return valid JSON."""


def _parse_qa_scores(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    try:
        data = json.loads(cleaned)
        for dim in DIMENSION_WEIGHTS:
            if dim != "uniqueness" and dim not in data:
                raise ValueError(f"Missing dimension score: '{dim}'")
        return data
    except Exception as e:
        logger.warning(f"[Node6] QA score JSON parse failed: {e}. Using defaults.")
        return {dim: 0.5 for dim in DIMENSION_WEIGHTS if dim != "uniqueness"}


def _check_format_compliance(state: QuestionState) -> float:
    stem = state.get("question_stem", "")
    flags = []

    forbidden = ["all of the above", "none of the above"]
    for f in forbidden:
        if f in stem.lower():
            flags.append(f"forbidden_phrase: '{f}'")

    if re.search(r"\bnot\b.*\bnot\b", stem, re.IGNORECASE):
        flags.append("double_negative_detected")

    fq = state.get("formatted_question") or {}
    required_keys = ["id", "question", "options", "correct_option", "explanation"]
    for key in required_keys:
        if not fq.get(key):
            flags.append(f"null_field: '{key}'")

    if flags:
        logger.warning(f"[Node6] Format issues found: {flags}")
        return max(0.0, 1.0 - 0.25 * len(flags))
    return 1.0


def _compute_weighted_qa_score(dim_scores: dict) -> float:
    total = 0.0
    for dim, weight in DIMENSION_WEIGHTS.items():
        try:
            total += float(dim_scores.get(dim, 0.0)) * weight
        except (ValueError, TypeError):
            total += 0.5 * weight
    return round(min(1.0, max(0.0, total)), 4)


def _get_worst_dimension(dim_scores: dict) -> str:
    # Filter to only dimensions with numeric scores (skip 'reasoning' string etc.)
    numeric = {d: v for d, v in dim_scores.items() if isinstance(v, (int, float))}
    if not numeric:
        return "factual_accuracy"  # safe fallback
    return min(numeric, key=lambda d: numeric[d])


def _build_qa_flags(dim_scores: dict, threshold: float = 0.6) -> list[str]:
    flags = []
    for dim, score in dim_scores.items():
        if dim == "reasoning": continue
        try:
            if float(score) < threshold: flags.append(dim)
        except (ValueError, TypeError):
            flags.append(dim)
    return flags


def qa_orchestrator_node(state: QuestionState) -> dict:
    retry_count = state.get("retry_count", 0)
    logger.info(f"[Node6] QA audit starting | retry_count={retry_count}")

    if retry_count >= MAX_RETRIES:
        logger.warning(f"[Node6] Max retries ({MAX_RETRIES}) reached. Marking FAILED.")
        return {"qa_score": 0.0, "qa_flags": ["max_retries_exceeded"], "approved": False, "retry_count": retry_count}

    format_score = _check_format_compliance(state)
    is_dup, similarity = check_duplicate(state.get("question_stem", ""))
    uniqueness_score = 0.0 if is_dup else 1.0

    try:
        user_prompt = _build_orchestrator_prompt(state)
        # Use small max_tokens (512) — QA response is just a short JSON object.
        # This keeps total tokens within the 4096 model context limit.
        from src.llm_client import get_heavy_client, _call_with_retry
        raw_response = _call_with_retry(
            get_heavy_client(), HEAVY_MODEL_NAME,
            ORCHESTRATOR_SYSTEM_PROMPT, user_prompt, max_tokens=512
        )
        llm_scores   = _parse_qa_scores(raw_response)
    except Exception as e:
        logger.error(f"[Node6] Qwen-72B QA failed: {e}. Falling back.")
        llm_scores = {dim: 0.6 for dim in DIMENSION_WEIGHTS if dim != "uniqueness"}

    all_dim_scores = {**llm_scores, "format_compliance": format_score, "uniqueness": uniqueness_score}
    qa_score = _compute_weighted_qa_score(all_dim_scores)
    qa_flags = _build_qa_flags(all_dim_scores)
    approved = qa_score >= QA_PASS_THRESHOLD and not is_dup

    logger.info(f"[Node6] QA Score: {qa_score:.4f} | Approved: {approved} | Flags: {qa_flags}")

    # Process Approval
    if approved:
        fq = state.get("formatted_question") or {}
        qid = fq.get("id", f"unknown_{retry_count}")
        add_question(
            question_id=qid, question_stem=state.get("question_stem", ""),
            metadata={"paper": state.get("paper", ""), "topic": state.get("topic", "")}
        )
        if state.get("formatted_question"):
            state["formatted_question"]["qa_score"] = qa_score
        update_topic_coverage(state.get("topic", ""), state.get("subtopic", ""), KB_BASE_DIR)

    # Log to DB
    log_qa_to_db(
        state={**dict(state), "qa_score": qa_score, "approved": approved, "retry_count": retry_count + 1, "qa_flags": qa_flags},
        sqlite_db_path=SQLITE_DB_PATH,
        pipeline_version=PIPELINE_VERSION,
        heavy_model=HEAVY_MODEL_NAME,
        light_model=LIGHT_MODEL_NAME,
    )

    if not approved and retry_count < MAX_RETRIES:
        worst = _get_worst_dimension(all_dim_scores)
        if worst not in qa_flags: qa_flags.append(worst)
        logger.info(f"[Node6] Worst dim: '{worst}' → routes to: {RETRY_ROUTE_MAP.get(worst)}")

    return {
        "qa_score": qa_score,
        "qa_flags": qa_flags,
        "approved": approved,
        "retry_count": retry_count + 1,
        "formatted_question": state.get("formatted_question"),
    }
