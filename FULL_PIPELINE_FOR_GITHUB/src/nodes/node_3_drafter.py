"""
node_3_drafter.py — Node 3: Question Drafter (MCQ Author)

Responsibilities (from blueprint Section 4 — Node 3):
  - Reads research_context from Node 2
  - Drafts question stem + correct answer + explanation
  - Follows UPSC patterns: statement-based, match-the-following,
    assertion-reasoning, correct/incorrect, most-appropriate
  - Uses 3-5 real UPSC PYQs as few-shot examples per type
  - Single-concept testing, no ambiguity, no forbidden anti-patterns
  - Outputs structured JSON (parsed into state fields)

LLM used: Qwen-72B-AWQ (heavy endpoint)
"""

import json
import logging
import re

from src.state import QuestionState
from src.llm_client import call_heavy, get_heavy_client, _call_with_retry
from src.config import HEAVY_MODEL_NAME

from src.utils import setup_logger
logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Few-shot UPSC examples — one per major question type
# These are real UPSC PYQ patterns used to guide Qwen-72B
# ─────────────────────────────────────────────────────────────────────────────
FEW_SHOT_EXAMPLES = {

    "factual": """
EXAMPLE (Factual — Medium):
Q: With reference to the 'Pradhan Mantri Jan Dhan Yojana', which of the
   following statements is/are correct?
   1. It provides for the opening of basic savings bank accounts with zero balance.
   2. It provides for accidental insurance cover of ₹1 lakh.
   3. It aims to achieve financial inclusion for the unbanked population.
Select the correct answer using the code below:
   (a) 1 and 2 only   (b) 2 and 3 only   (c) 1 and 3 only   (d) 1, 2 and 3

Correct: 1, 2 and 3
Explanation: PMJDY was launched in 2014 to provide universal banking access.
   All three statements are correct. (Note: insurance cover was later raised to ₹2 lakh.)
""",

    "analytical": """
EXAMPLE (Analytical — Hard):
Q: The concept of 'Judicial Review' in India differs from that in the USA
   primarily because in India judicial review is:
   (a) Discretionary and not explicitly mentioned in the Constitution
   (b) Limited to constitutional validity and not extended to the wisdom
       or policy aspects of legislation
   (c) Applicable only to Central government laws
   (d) Exercised only by the Supreme Court and not High Courts

Correct: (b) Limited to constitutional validity ...
Explanation: In India, judicial review (Articles 13, 32, 226) is confined to
   checking constitutional validity. Courts cannot question legislative wisdom,
   unlike the broader US interpretation from Marbury v. Madison.
""",

    "current_affairs": """
EXAMPLE (Current Affairs — Medium):
Q: Consider the following statements about the 'Global Biodiversity Framework'
   adopted at COP15 in Montreal (2022):
   1. It set a target to protect 30% of global land and oceans by 2030.
   2. India voted against its adoption citing equity concerns.
Select the correct answer:
   (a) 1 only   (b) 2 only   (c) Both 1 and 2   (d) Neither 1 nor 2

Correct: (a) 1 only
Explanation: The Kunming-Montreal Framework's '30x30' target was adopted with
   near-unanimous support including India. Statement 2 is incorrect.
""",

    "statement_based": """
EXAMPLE (Statement-Based — Medium):
Q: Consider the following statements about the Comptroller and Auditor General (CAG) of India:
   1. The CAG is appointed by the President of India.
   2. The CAG can be removed from office by a simple majority in Parliament.
   3. The reports of the CAG are submitted to the President who causes them
      to be laid before Parliament.
Which of the statements given above is/are correct?
   (a) 1 only   (b) 1 and 3 only   (c) 2 and 3 only   (d) 1, 2 and 3

Correct: (b) 1 and 3 only
Explanation: Statement 1 is correct (Article 148). Statement 2 is incorrect —
   CAG is removed by address of both Houses, like a Supreme Court judge (special
   majority). Statement 3 is correct (Article 151).
""",

    "match_following": """
EXAMPLE (Match the Following — Hard):
Q: Match the following Constitutional Articles with their provisions:
   List-I (Article)          List-II (Provision)
   A. Article 17              1. Abolition of Untouchability
   B. Article 24              2. Prohibition of child labour in hazardous industries
   C. Article 44              3. Uniform Civil Code
   D. Article 51A             4. Fundamental Duties
Select the correct answer:
   (a) A-1, B-2, C-3, D-4   (b) A-2, B-1, C-4, D-3
   (c) A-1, B-3, C-2, D-4   (d) A-3, B-4, C-1, D-2

Correct: (a) A-1, B-2, C-3, D-4
Explanation: Each article matches directly — Article 17 abolishes untouchability;
   Article 24 prohibits employment of children below 14 in factories/mines;
   Article 44 is the Directive Principle for a Uniform Civil Code;
   Article 51A lists Fundamental Duties.
""",

    "assertion_reasoning": """
EXAMPLE (Assertion-Reasoning — Hard):
Q: Assertion (A): India follows a federal system of government.
   Reason (R): The Constitution of India provides for a clear division of
               powers between the Union and the States.
Select the correct option:
   (a) Both A and R are true, and R is the correct explanation of A
   (b) Both A and R are true, but R is NOT the correct explanation of A
   (c) A is true, but R is false
   (d) A is false, but R is true

Correct: (b) Both A and R are true, but R is NOT the correct explanation of A
Explanation: India is a federal system, but the Constitution has several
   unitary features (single citizenship, IAS cadre, residuary powers with
   Centre). The mere division of powers is necessary but not sufficient to
   fully explain federalism in India's context.
""",

    "correct_incorrect": """
EXAMPLE (Correct/Incorrect — Easy):
Q: Which of the following statements about the Reserve Bank of India is NOT correct?
   (a) It was established in 1935 under the Reserve Bank of India Act, 1934.
   (b) It was nationalized in 1948.
   (c) It functions as the banker to the Central Government only.
   (d) It regulates the issue of banknotes in India.

Correct: (c) It functions as the banker to the Central Government only.
Explanation: The RBI acts as banker to both the Central Government AND State
   Governments (though the arrangement with states varies). Options (a), (b),
   and (d) are factually correct.
""",

    "most_appropriate": """
EXAMPLE (Most Appropriate — Hard):
Q: Which of the following best describes the concept of 'Blue Economy'?
   (a) An economic model focused on the conservation of freshwater bodies
   (b) Sustainable use of ocean resources for economic growth, improved
       livelihoods, and jobs while preserving the health of the ocean ecosystem
   (c) A UN framework for managing international maritime trade disputes
   (d) The practice of investing in renewable ocean energy technologies only

Correct: (b) Sustainable use of ocean resources for economic growth ...
Explanation: The 'Blue Economy' concept (coined by Gunter Pauli) and later
   adopted by the World Bank refers to the sustainable use of ALL ocean
   resources — fisheries, tourism, shipping, energy — for economic development.
   Options (a), (c), (d) are all narrow or incorrect interpretations.
""",
}

# ─────────────────────────────────────────────────────────────────────────────
# Paper-specific guidance (what Node 3 should focus on per paper)
# ─────────────────────────────────────────────────────────────────────────────
PAPER_GUIDANCE = {
    "GS1": "Focus on History, Geography, Indian Society, Art & Culture. Avoid current affairs.",
    "GS2": "Focus on Polity, Governance, Constitution, IR, Social Justice.",
    "GS3": "Focus on Economy, Environment, Science & Technology, Internal Security.",
    "GS4": "Focus on Ethics, Integrity, Aptitude. Questions should be scenario-based.",
    "CSAT": "Focus on comprehension, logical reasoning, basic numeracy. Keep it concise.",
}

# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────
DRAFTER_SYSTEM_PROMPT = """You are an expert UPSC question setter with 15 years of experience.
Your task is to draft a high-quality MCQ from the provided research context.

STRICT RULES — violating any rule results in rejection:
1. Test exactly ONE concept. No multi-barrelled questions.
2. FORBIDDEN patterns: "All of the above", "None of the above", double negatives, trick questions.
3. The correct answer must be definitively and unambiguously correct — verified by the research context.
4. The question must match the exact difficulty and UPSC paper style specified.
5. For 'statement-based' type: use numbered statements (1, 2, 3) and end with
   "Which of the above statements is/are correct?"
6. For 'assertion-reasoning' type: use "Assertion (A):" and "Reason (R):" format.
7. The explanation must clearly explain WHY the correct answer is correct and
   WHY the other options are wrong (where applicable).
8. The question solution MUST contain a 'mains_fact' — a specific fact or data point from the
   topic that would be highly valuable for UPSC Mains answer writing.
9. Analyze the provided PYQ context (if any) to learn UPSC question patterns and recent trends.
   Use the PYQs to identify what is historically important. IGNORE detailed textbook information
   that falls outside the focus areas of the PYQs (e.g. if the PYQs only test 2 specific chapters
   out of a book, strictly focus your question on those highly-tested concepts).

Respond ONLY in this exact JSON format — no markdown, no extra text:
{
  "question_stem": "The full question text here",
  "correct_answer": "The correct option text (full sentence, not just A/B/C/D)",
  "explanation": "Detailed 3-5 sentence explanation explicitly stating WHY the answer is correct and citing sources",
  "mains_fact": "A concise, single-sentence fact valuable for Mains answer writing",
  "citations": "Exact names/URLs of the database sources used to draft this (e.g. 'NCERT History' or 'VisionIAS')"
}"""


def _get_few_shot(question_type: str) -> str:
    """Returns the relevant few-shot PYQ example for the question type."""
    qtype = question_type.lower()
    if qtype in FEW_SHOT_EXAMPLES:
        return FEW_SHOT_EXAMPLES[qtype]
    # Default to factual if unknown type
    return FEW_SHOT_EXAMPLES["factual"]


def _build_drafter_prompt(state: QuestionState) -> str:
    q_type  = state.get("question_type", "factual")
    paper   = state.get("paper", "GS2")
    diff    = state.get("difficulty", "medium")
    topic   = state.get("topic", "")
    subtopic= state.get("subtopic", "")
    context = state.get("research_context", "")
    tags    = ", ".join(state.get("tags", []))
    few_shot= _get_few_shot(q_type)
    paper_g = PAPER_GUIDANCE.get(paper, "")
    pyq_ctx = state.get("pyq_context", "")

    return f"""Draft a UPSC MCQ using the parameters below.

─── PARAMETERS ───────────────────────────────────────
Paper          : {paper}
Topic          : {topic}
Subtopic       : {subtopic}
Difficulty     : {diff}
Question Type  : {q_type}
Tags           : {tags}
Paper Guidance : {paper_g}

─── VERIFIED RESEARCH CONTEXT (your ONLY source of facts) ────────────────────
{context[:1000]}

{pyq_ctx[:400]}

─── FEW-SHOT UPSC EXAMPLE (match this style) ─────────────────────────────────
{few_shot}

─── YOUR TASK ────────────────────────────────────────
Now draft the MCQ in the exact JSON format specified. Do not include options A/B/C/D —
only write the question stem and the correct answer text. The distractor node will
generate the wrong options separately."""


def _parse_drafter_response(raw: str) -> dict:
    """
    Parses Qwen-72B's JSON response. Handles markdown fences gracefully.
    Returns dict with question_stem, correct_answer, explanation.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")

    try:
        data = json.loads(cleaned)
        required = ["question_stem", "correct_answer", "explanation", "mains_fact", "citations"]
        for key in required:
            if not data.get(key, ""):
                # Allow mains_fact & citations to be empty if the LLM couldn't find one
                if key in ["mains_fact", "citations"]:
                    logger.debug(f"[Node3] Missing {key} in LLM response.")
                else:
                    raise ValueError(f"Missing or empty field: '{key}'")
        if "citations" not in data: data["citations"] = ""
        return data
    except Exception as e:
        logger.warning(f"[Node3] JSON parse failed: {e}. Attempting regex fallback.")

        # Regex fallback: try to extract fields individually
        stem_match  = re.search(r'"question_stem"\s*:\s*"(.*?)"(?=,\s*")', raw, re.DOTALL)
        ans_match   = re.search(r'"correct_answer"\s*:\s*"(.*?)"(?=,\s*")', raw, re.DOTALL)
        exp_match   = re.search(r'"explanation"\s*:\s*"(.*?)"(?=,\s*")', raw, re.DOTALL)
        mains_match = re.search(r'"mains_fact"\s*:\s*"(.*?)"', raw, re.DOTALL)
        cit_match   = re.search(r'"citations"\s*:\s*"(.*?)"', raw, re.DOTALL)

        return {
            "question_stem":  stem_match.group(1).strip()  if stem_match  else "",
            "correct_answer": ans_match.group(1).strip()   if ans_match   else "",
            "explanation":    exp_match.group(1).strip()   if exp_match   else "",
            "mains_fact":     mains_match.group(1).strip() if mains_match else "",
            "citations":      cit_match.group(1).strip()   if cit_match   else "",
        }


def question_drafter_node(state: QuestionState) -> dict:
    """
    LangGraph Node 3 — Question Drafter.
    Returns partial state update with question_stem, correct_answer, explanation.
    """
    logger.info(
        f"[Node3] Drafting question | topic='{state.get('topic')}' "
        f"| type='{state.get('question_type')}' | difficulty='{state.get('difficulty')}'"
    )

    if not state.get("research_context"):
        logger.error("[Node3] research_context is empty — cannot draft question.")
        return {
            "question_stem":  "",
            "correct_answer": "",
            "explanation":    "",
            "mains_fact":     "",
            "qa_flags":       (state.get("qa_flags") or []) + ["missing_research_context"],
        }

    user_prompt = _build_drafter_prompt(state)

    try:
        # Use 1024 max_tokens — the required JSON output is compact.
        # This keeps total tokens safely within the 4096-token model context window.
        raw_response = _call_with_retry(
            get_heavy_client(), HEAVY_MODEL_NAME,
            DRAFTER_SYSTEM_PROMPT, user_prompt, max_tokens=1024
        )
        logger.info(f"[Node3] Raw LLM response length: {len(raw_response)} chars.")
    except Exception as e:
        logger.error(f"[Node3] Qwen-72B call failed: {e}")
        return {
            "question_stem":  "",
            "correct_answer": "",
            "explanation":    "",
            "mains_fact":     "",
            "qa_flags": (state.get("qa_flags") or []) + ["drafter_llm_error"],
        }

    parsed = _parse_drafter_response(raw_response)

    # Guard: if key fields are still empty after parsing, flag it
    if not parsed.get("question_stem") or not parsed.get("correct_answer"):
        logger.warning("[Node3] Parsed response has empty stem or answer.")
        return {
            "question_stem":  parsed.get("question_stem", ""),
            "correct_answer": parsed.get("correct_answer", ""),
            "explanation":    parsed.get("explanation", ""),
            "mains_fact":     parsed.get("mains_fact", ""),
            "qa_flags": (state.get("qa_flags") or []) + ["drafter_empty_output"],
        }

    logger.info(f"[Node3] Draft complete. Stem length: {len(parsed['question_stem'])} chars.")

    return {
        "question_stem":  parsed["question_stem"],
        "correct_answer": parsed["correct_answer"],
        "explanation":    parsed["explanation"],
        "mains_fact":     parsed.get("mains_fact", ""),
        "citations":      parsed.get("citations", "")
    }
