"""
node_2_researcher.py — Node 2: Content Researcher (Subject-Matter Expert)

Responsibilities (from blueprint Section 4 — Node 2):
  - Queries ChromaDB RAG for top-K Current Affairs chunks (source_type=CA)
  - Queries ChromaDB RAG for top-K Textbook / NCERT chunks (source_type=textbook)
  - Looks up Static Knowledge Base (constitutional articles, acts, key dates)
  - Calls Qwen-72B to synthesize a 300-500 word dense factual brief
  - Every fact must cite source (CA:chunk_id, TB:chunk_id, or KB:key)

CA Priority Mode (question_type = "current_affairs"):
  - Retrieves more CA chunks (top-7 instead of top-5)
  - System prompt STRICTLY forbids the LLM from using parametric knowledge
    beyond what is retrieved — zero hallucination guarantee for recent events.
  - Textbook chunks used only as supplementary background context.

LLM used: Qwen-72B-AWQ (heavy endpoint)
"""

import logging

from src.state import QuestionState
from src.llm_client import call_heavy, get_heavy_client, get_light_client, _call_with_retry
from src.kb_loader import lookup_facts_for_topic
from src.pgvector_client import (
    retrieve_ca_chunks,
    retrieve_textbook_chunks,
    format_chunks_as_context,
)
from src.chroma_client import retrieve_pyq_chunks
from src.config import PGV_TOP_K_CA, PGV_TOP_K_TEXTBOOK, HEAVY_MODEL_NAME, LIGHT_MODEL_NAME

from src.utils import setup_logger
logger = setup_logger(__name__)

# ── Top-K overrides for current_affairs mode ─────────────────────────────────
CA_TOP_K_BOOST    = max(PGV_TOP_K_CA, 7)   # Minimum 7 CA chunks for CA questions
CA_TB_SUPPLEMENTAL = 2                       # Only 2 textbook chunks in CA mode (background)

# ─────────────────────────────────────────────────────────────────────────────
# System prompts — different flavours for CA vs standard topics
# ─────────────────────────────────────────────────────────────────────────────

RESEARCHER_SYSTEM_PROMPT_STANDARD = """You are an expert UPSC content researcher and subject-matter authority.
Your task is to produce a dense, factually verified research brief (300-500 words) for a specific UPSC topic.

Rules you MUST follow:
1. Base every fact on the provided retrieved context below — do NOT hallucinate.
2. For each fact you include, cite the exact source using the format [CA:chunk_id] or [TB:chunk_id] or [KB:key].
3. Focus on facts that are directly testable in a UPSC MCQ (dates, articles, acts, committees, etc.).
4. Highlight any information that is particularly tricky or commonly confused by students.
5. If the topic relates to recent events (post-2023), clearly flag those sections with [RECENT].
6. Write in factual prose — no bullet points, no headings. Just 300-500 words of dense, citable content.
7. End with a one-sentence "Key Testable Fact" that summarises the most UPSC-relevant point."""


RESEARCHER_SYSTEM_PROMPT_CA = """You are an expert UPSC current affairs analyst.
Your task is to produce a 300-500 word research brief grounded EXCLUSIVELY in the retrieved Current Affairs context.

CRITICAL ANTI-HALLUCINATION RULES — violating EVEN ONE rule causes automatic rejection:
1. *** USE ONLY the retrieved CA context provided below. ***
   Do NOT use any knowledge from your pre-training weights for facts, dates, names, or figures.
   If a fact is NOT present in the retrieved context, you must state "Not in retrieved context" and omit it.
2. Cite EVERY fact using [CA:N] format (where N is the CA chunk number from context).
3. Focus on: recent policy announcements, government schemes, international agreements,
   environmental events, economic data, and scientific milestones — from the retrieved text only.
4. Clearly flag time-sensitive facts with [RECENT: YYYY-MM if known].
5. Write 300-500 words of dense, citable factual prose (no bullet points, no headings).
6. End with a "Key Testable Fact" — the single most UPSC-ready data point from the retrieved context.
7. If the retrieved CA context is thin or unrelated to the topic, note "Context limited for this topic"
   at the top and work with what's available — still DO NOT fabricate."""


def _build_user_prompt(state: QuestionState, retrieved_context: str, kb_facts: str,
                        is_ca: bool = False) -> str:
    ca_instruction = (
        "\n⚠ CURRENT AFFAIRS MODE: Your brief must be grounded ONLY in the CA context above.\n"
        "Do not supplement with knowledge not present in the retrieved chunks.\n"
    ) if is_ca else ""

    return f"""Generate a 300-500 word factual research brief for the following UPSC question parameters.

UPSC Paper     : {state['paper']}
Topic          : {state['topic']}
Subtopic       : {state['subtopic']}
Question Type  : {state['question_type']}
Difficulty     : {state['difficulty']}
{ca_instruction}
─── RETRIEVED CONTEXT (use this as your PRIMARY/ONLY source) ───
{retrieved_context[:2000]}

─── STATIC KNOWLEDGE BASE FACTS ───
{kb_facts[:300]}

Now write the 300-500 word research brief, citing every fact with [CA:N], [TB:N], or [KB:key] tags."""


def content_researcher_node(state: QuestionState) -> dict:
    """
    LangGraph Node 2 — Content Researcher.
    Returns partial state update with 'research_context'.
    """
    topic    = state.get("topic", "")
    subtopic = state.get("subtopic", "")
    paper    = state.get("paper", "")
    q_type   = state.get("question_type", "factual")
    is_ca    = (q_type == "current_affairs")

    logger.info(
        f"[Node2] Researching: topic='{topic}' | subtopic='{subtopic}' | "
        f"paper='{paper}' | type='{q_type}'"
        + (" [CA-GROUNDED MODE]" if is_ca else "")
    )

    # ── Step 1: Build a semantic search query ────────────────────────────────
    search_query = f"{topic} {subtopic} {paper} UPSC current affairs" if is_ca \
                   else f"{topic} {subtopic} {paper} UPSC"

    # ── Step 2: Retrieve from ChromaDB RAG ───────────────────────────────────
    if is_ca:
        # CA mode: prioritise scraped CA chunks heavily; only small textbook supplement
        ca_chunks = retrieve_ca_chunks(search_query, top_k=CA_TOP_K_BOOST)
        tb_chunks = retrieve_textbook_chunks(search_query, top_k=CA_TB_SUPPLEMENTAL)
        if not ca_chunks:
            logger.warning(
                "[Node2] [CA-MODE] No CA chunks found in ChromaDB for this topic. "
                "The question may lack fresh factual grounding. "
                "Run: python ca_scraper.py --run-now  to populate CA context."
            )
    else:
        ca_chunks = retrieve_ca_chunks(search_query)
        tb_chunks = retrieve_textbook_chunks(search_query)

    retrieved_context = format_chunks_as_context(ca_chunks, tb_chunks)

    # ── Step 3: Lookup Static Knowledge Base ─────────────────────────────────
    kb_facts = lookup_facts_for_topic(topic, subtopic)

    # ── Step 3.5: Retrieve PYQ Context for trend/pattern matching ────────────
    # User requested using PYQs to watch question patterns prioritizing recent trends
    # and filtering out textbook importance based on what is actually tested.
    raw_pyq_chunks = retrieve_pyq_chunks(search_query, top_k=5)
    pyq_context_str = ""
    if raw_pyq_chunks:
        pyq_context_str = "--- PREVIOUS YEAR QUESTIONS (USE FOR PATTERN/FOCUS ANALYSIS) ---\n"
        for i, chunk in enumerate(raw_pyq_chunks):
            pyq_context_str += f"[PYQ:{i+1}] {chunk.strip()}\n\n"
    else:
        pyq_context_str = "[No recent PYQ trends found for this exact topic.]"

    logger.info(
        f"[Node2] Retrieved {len(ca_chunks)} CA chunks, {len(tb_chunks)} TB chunks, "
        f"{len(raw_pyq_chunks)} PYQs. KB facts: {len(kb_facts)} chars."
    )

    # ── Step 4: Call Qwen-72B to synthesize the research brief ───────────────
    system_prompt = RESEARCHER_SYSTEM_PROMPT_CA if is_ca else RESEARCHER_SYSTEM_PROMPT_STANDARD
    user_prompt   = _build_user_prompt(state, retrieved_context, kb_facts, is_ca=is_ca)

    try:
        # Use 1024 max_tokens — researcher output is a 300-500 word brief.
        # This keeps total tokens safely within the 4096-token model context window.
        research_context = _call_with_retry(
            get_light_client(), LIGHT_MODEL_NAME,
            system_prompt, user_prompt, max_tokens=1024
        )
        logger.info(f"[Node2] Research brief generated: {len(research_context)} chars.")
    except Exception as e:
        logger.error(f"[Node2] Mistral-7B call failed: {e}")
        # Fallback: use raw retrieved context — at least it's grounded in vector store
        research_context = (
            f"[FALLBACK — LLM unavailable. Raw retrieved context below.]\n\n"
            f"{retrieved_context}\n\n"
            f"{kb_facts}"
        )

    return {
        "research_context": research_context,
        "pyq_context": pyq_context_str,
    }
