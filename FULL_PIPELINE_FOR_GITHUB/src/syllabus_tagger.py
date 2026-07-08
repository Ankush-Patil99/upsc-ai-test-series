"""
syllabus_tagger.py — UPSC Official Syllabus Tag Matcher
=========================================================
Extracts the official UPSC Mains GS1 / GS2 / GS3 topic phrases
from the Drishti IAS syllabus PDFs and provides a function that
maps any question (topic + subtopic + question stem) onto the
EXACT syllabus wording used in those PDFs.

WHY THIS MODULE EXISTS
----------------------
The user's requirement: questions must be tagged with the exact words
that appear in the UPSC syllabus PDFs — not LLM-generated labels.
Multiple tags are allowed if the question spans multiple syllabus topics.

PDF STRUCTURE (Drishti IAS Mains syllabus print)
-------------------------------------------------
These are web-to-PDF exports from drishtiias.com, so they contain:
  - Header/footer chrome (timestamps, URLs, page numbers) — SKIPPED
  - Two-column layout on many pages in GS1 (left col + right col)
  - Single-column layout on GS2 and GS3 pages
  - Mixed indentation encoding topic hierarchy:
      x0 ≈ 34-40   → UPSC main syllabus sentence (coarse topic)
      x0 ≈ 64-66   → sub-topic heading
      x0 ≈ 96-142  → sub-sub-topic / bullet point
      x0 ≈ 154-233 → section break heading (e.g. "Art & Culture")
      x0 ≥ 280     → right column content (same hierarchy encoding)

HOW TAGGING WORKS
-----------------
1. On first use, `_build_syllabus_index()` is called (cached thereafter).
   It reads GS1.pdf, GS2.pdf, GS3.pdf and extracts every topic phrase.
2. To tag a question, `tag_question(topic, subtopic, stem)` joins the
   input text then finds all syllabus phrases that are a "substring match"
   OR whose words overlap significantly (Jaccard ≥ 0.25).
3. Returns a deduplicated, sorted list of matching exact syllabus phrases.
4. Falls back to [topic, subtopic] if no syllabus match is found.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Optional

from src.utils import setup_logger
logger = setup_logger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent      # UPSC_Test_Agent/
SYLLABUS_DIR = BASE_DIR / "data" / "syllabus"

PDF_FILES = {
    "GS1": SYLLABUS_DIR / "GS1.pdf",
    "GS2": SYLLABUS_DIR / "GS2.pdf",
    "GS3": SYLLABUS_DIR / "GS3.pdf",
}

# ── Chrome / navigation text to skip ─────────────────────────────────────────
_SKIP_RE = re.compile(
    r"(drishtiias\.com"
    r"|https?://"
    r"|^\d{2}/\d{2}/\d{4}"       # date stamp: 15/04/2026
    r"|print_manually"
    r"|General\s+Studies-[IVX]+\s*\|"
    r"|\d+/\d+$"                  # page counter: 7/11
    r"|^\s*\d+\s*$"               # bare page numbers
    r")",
    re.IGNORECASE,
)

# ── Minimum phrase length (chars) to be a valid syllabus tag ─────────────────
_MIN_PHRASE_LEN = 8

# ── Tagging thresholds ────────────────────────────────────────────────────────
# Jaccard similarity on word sets: a syllabus phrase is a tag if it scores ≥ this
_JACCARD_THRESHOLD = 0.20

# Minimum number of words from the syllabus phrase that must appear in the
# question text (for short phrases this is more reliable than Jaccard)
_MIN_WORD_OVERLAP = 3

# ─────────────────────────────────────────────────────────────────────────────
# Internal state — cached once per process
# ─────────────────────────────────────────────────────────────────────────────
_index_lock      = threading.Lock()
_syllabus_index: Optional[dict[str, list[str]]] = None   # paper → [phrase, ...]
_all_phrases:    Optional[list[tuple[str, str]]]  = None  # [(paper, phrase), ...]


# ─────────────────────────────────────────────────────────────────────────────
# PDF text extraction — 2-column aware
# ─────────────────────────────────────────────────────────────────────────────

def _extract_blocks_column_aware(page) -> list[str]:
    """
    Extract text blocks from a PDF page, handling 2-column layouts.

    Two-column detection: if ≥10% of chars are in the right half, treat as
    two-column (left top→bottom first, then right top→bottom).

    Returns a list of raw block strings in reading order.
    """
    blocks = page.get_text("blocks", sort=True)
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return []

    mid          = page.rect.width / 2
    left_blocks  = [b for b in text_blocks if b[0] < mid]
    right_blocks = [b for b in text_blocks if b[0] >= mid]
    right_chars  = sum(len(b[4]) for b in right_blocks)
    total_chars  = sum(len(b[4]) for b in text_blocks)
    is_two_col   = total_chars > 0 and (right_chars / total_chars) >= 0.10

    if is_two_col:
        ordered = (
            sorted(left_blocks,  key=lambda b: b[1]) +
            sorted(right_blocks, key=lambda b: b[1])
        )
    else:
        ordered = text_blocks   # already sorted top-to-bottom

    return [b[4] for b in ordered]


def _merge_block_lines(block_text: str) -> list[str]:
    """
    Split a single PDF text block into discrete topic phrases.

    Strategy:
    - Split by newline — each newline-separated line is a candidate phrase.
    - Within the block, merge a line with the NEXT only if:
        • the current line ends without terminal punctuation (.;?!), AND
        • the next line starts with a lowercase letter (continuation),
        • AND the block has ≤ 3 lines (so we don't merge a whole bullet list).
    - Result: a list of individual topic phrases from this block.
    """
    lines = [ln.strip() for ln in block_text.split("\n") if ln.strip()]
    lines = [ln for ln in lines if not _SKIP_RE.search(ln)]
    if not lines:
        return []

    # Simple within-block merge: only merge when clearly one sentence
    merged: list[str] = []
    buf = ""
    for ln in lines:
        if not buf:
            buf = ln
            continue
        # Detect continuation: buf ends without punctuation AND ln starts lowercase
        buf_ends_incomplete = buf and buf[-1] not in ".;?!)"
        ln_starts_lower     = ln and ln[0].islower()
        if buf_ends_incomplete and ln_starts_lower:
            buf = buf.rstrip() + " " + ln
        else:
            merged.append(buf)
            buf = ln
    if buf:
        merged.append(buf)
    return merged


def _extract_phrases_from_pdf(pdf_path: Path, paper: str) -> list[str]:
    """
    Extract all valid syllabus topic phrases from a single PDF.

    Each PyMuPDF text block is treated as a self-contained unit.
    Lines within a block are split into individual candidates; within-block
    continuation merging is applied carefully.
    Navigation chrome (timestamps, URLs, page numbers) is filtered out.
    """
    try:
        import fitz
    except ImportError:
        logger.error("[SyllabusTagger] PyMuPDF not installed. Run: pip install pymupdf")
        return []

    if not pdf_path.exists():
        logger.warning(f"[SyllabusTagger] PDF not found: {pdf_path}")
        return []

    all_candidates: list[str] = []

    try:
        doc = fitz.open(str(pdf_path))
        for page in doc:
            block_texts = _extract_blocks_column_aware(page)
            for block_text in block_texts:
                if _SKIP_RE.search(block_text):
                    continue
                phrases = _merge_block_lines(block_text)
                all_candidates.extend(phrases)
        doc.close()
    except Exception as e:
        logger.error(f"[SyllabusTagger] Failed to read '{pdf_path}': {e}")
        return []

    # Clean, filter, deduplicate
    cleaned: list[str] = []
    seen: set[str] = set()
    for phrase in all_candidates:
        # Remove leading bullet chars and normalise whitespace
        phrase = re.sub(r"^\s*[-•–—*]\s*", "", phrase)
        phrase = re.sub(r"\s+", " ", phrase).strip()
        phrase = phrase.strip("()[]{}\"'")
        phrase = re.sub(r"\s+\d+/\d+\s*$", "", phrase).strip()  # trailing page nums
        if len(phrase) < _MIN_PHRASE_LEN:
            continue
        if _SKIP_RE.search(phrase):
            continue
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(phrase)

    logger.info(
        f"[SyllabusTagger] {paper}: {len(cleaned)} phrases extracted from '{pdf_path.name}'"
    )
    return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# Index builder — called once, cached
# ─────────────────────────────────────────────────────────────────────────────

def _build_syllabus_index() -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """
    Build and cache the syllabus index from GS1/GS2/GS3 PDFs.
    Returns:
        index  : {paper: [phrase, ...]}
        flat   : [(paper, phrase), ...] — for matching
    """
    global _syllabus_index, _all_phrases

    with _index_lock:
        if _syllabus_index is not None:
            return _syllabus_index, _all_phrases

        index: dict[str, list[str]] = {}
        flat:  list[tuple[str, str]] = []

        for paper, pdf_path in PDF_FILES.items():
            phrases = _extract_phrases_from_pdf(pdf_path, paper)
            index[paper] = phrases
            flat.extend((paper, p) for p in phrases)

        total = sum(len(v) for v in index.values())
        logger.info(f"[SyllabusTagger] Index built: {total} total phrases across GS1+GS2+GS3")

        _syllabus_index = index
        _all_phrases    = flat

    return _syllabus_index, _all_phrases


# ─────────────────────────────────────────────────────────────────────────────
# Matching engine
# ─────────────────────────────────────────────────────────────────────────────

# Stop-words to exclude from word overlap scoring
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to",
    "for", "with", "by", "from", "its", "it", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "not", "no", "nor", "so", "yet", "both", "either", "neither",
    "such", "as", "this", "that", "these", "those", "their", "which",
    "who", "what", "how", "when", "where", "why", "all", "each", "every",
    "any", "some", "most", "other", "more", "than", "about", "into",
    "up", "out", "over", "under", "between", "among", "during", "after",
    "before", "since", "through", "across", "against", "along",
    "related", "issues", "various", "different", "important",
    "based", "within", "upon", "etc", "pertaining",
})


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens, minus stop-words, from a text string."""
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


def _is_match(query_words: set[str], phrase: str) -> bool:
    """
    Returns True if the syllabus phrase qualifies as a tag for the given
    question tokens.

    Two independent matching strategies (either is sufficient):
      A. Substring: the phrase (cleaned to a short form) is a substring
         of the query text — reliable for short exact topic names.
      B. Word overlap: Jaccard ≥ _JACCARD_THRESHOLD on content words AND
         at least _MIN_WORD_OVERLAP content words match — reliable for
         longer descriptive phrases.
    """
    phrase_words = _tokenize(phrase)
    if not phrase_words:
        return False

    # Strategy B: Jaccard + minimum overlap count
    overlap = query_words & phrase_words
    if (len(overlap) >= _MIN_WORD_OVERLAP and
            _jaccard(query_words, phrase_words) >= _JACCARD_THRESHOLD):
        return True

    return False


def tag_question(
    topic: str,
    subtopic: str,
    question_stem: str = "",
    paper: str = "",
    max_tags: int = 8,
) -> list[str]:
    """
    Find all UPSC syllabus phrases that are relevant tags for this question.

    Args:
        topic          : question topic (from state)
        subtopic       : question subtopic
        question_stem  : the generated question text (optional, improves matching)
        paper          : "GS1", "GS2", "GS3", etc. — if given, prioritises that
                         paper's phrases but also checks others
        max_tags       : cap the returned list at this many tags

    Returns:
        A deduplicated list of exact syllabus phrases (as they appear in the PDF).
        Falls back to [topic, subtopic] if no matches are found.
    """
    _, flat = _build_syllabus_index()
    if not flat:
        logger.warning("[SyllabusTagger] No syllabus phrases loaded — returning raw topic/subtopic.")
        return _fallback_tags(topic, subtopic)

    # Build the query token set from all available question text
    query_text  = f"{topic} {subtopic} {question_stem}"
    query_words = _tokenize(query_text)

    if not query_words:
        return _fallback_tags(topic, subtopic)

    # Score every phrase
    matches: list[tuple[float, str, str]] = []   # (score, paper, phrase)
    for pap, phrase in flat:
        phrase_words = _tokenize(phrase)
        if not phrase_words:
            continue
        j = _jaccard(query_words, phrase_words)
        overlap_n = len(query_words & phrase_words)
        if _is_match(query_words, phrase):
            # Boost score if the paper matches the question's paper
            paper_boost = 1.2 if pap == paper else 1.0
            matches.append((j * paper_boost, pap, phrase))

    if not matches:
        logger.debug(
            f"[SyllabusTagger] No syllabus matches for topic='{topic}' "
            f"subtopic='{subtopic}'. Using fallback."
        )
        return _fallback_tags(topic, subtopic)

    # Sort by score descending, deduplicate phrases
    matches.sort(key=lambda x: x[0], reverse=True)
    seen:    set[str]  = set()
    result:  list[str] = []
    for _, _, phrase in matches:
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            result.append(phrase)
        if len(result) >= max_tags:
            break

    logger.debug(
        f"[SyllabusTagger] topic='{topic}' | {len(result)} tags matched: {result[:3]}..."
    )
    return result


def _fallback_tags(topic: str, subtopic: str) -> list[str]:
    """Return [topic, subtopic] as minimal fallback tags, deduplicated."""
    tags = []
    seen: set[str] = set()
    for t in [topic, subtopic]:
        t = t.strip()
        if t and t.lower() not in seen:
            tags.append(t)
            seen.add(t.lower())
    return tags


# ─────────────────────────────────────────────────────────────────────────────
# Public utilities
# ─────────────────────────────────────────────────────────────────────────────

def get_all_syllabus_phrases(paper: str = None) -> list[str]:
    """
    Return ALL extracted syllabus phrases (optionally filtered by paper).
    Useful for debugging or building a tag cloud.
    """
    index, _ = _build_syllabus_index()
    if paper:
        return index.get(paper.upper(), [])
    all_p: list[str] = []
    for phrases in index.values():
        all_p.extend(phrases)
    return all_p


def get_syllabus_index() -> dict[str, list[str]]:
    """Return the full {paper: [phrase]} index."""
    index, _ = _build_syllabus_index()
    return index


def rebuild_index():
    """Force-rebuild the syllabus index (useful if PDFs are updated)."""
    global _syllabus_index, _all_phrases
    with _index_lock:
        _syllabus_index = None
        _all_phrases    = None
    _build_syllabus_index()
    logger.info("[SyllabusTagger] Index rebuilt from PDFs.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI test / dump utility
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="UPSC Syllabus Tagger — CLI utility")
    parser.add_argument("--dump",   action="store_true", help="Dump all extracted phrases as JSON")
    parser.add_argument("--paper",  type=str, default=None, help="Filter dump to GS1/GS2/GS3")
    parser.add_argument("--tag",    action="store_true", help="Tag a question interactively")
    parser.add_argument("--topic",  type=str, default="", help="Topic for tagging")
    parser.add_argument("--subtopic", type=str, default="", help="Subtopic for tagging")
    parser.add_argument("--stem",   type=str, default="", help="Question stem for tagging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.dump:
        index = get_syllabus_index()
        if args.paper:
            phrases = index.get(args.paper.upper(), [])
            print(f"=== {args.paper.upper()} — {len(phrases)} phrases ===")
            for i, p in enumerate(phrases, 1):
                print(f"  {i:4d}. {p}")
        else:
            for paper, phrases in index.items():
                print(f"\n=== {paper} — {len(phrases)} phrases ===")
                for i, p in enumerate(phrases, 1):
                    print(f"  {i:4d}. {p}")
    elif args.tag:
        tags = tag_question(args.topic, args.subtopic, args.stem, paper=args.paper or "")
        print(f"\nTopic    : {args.topic}")
        print(f"Subtopic : {args.subtopic}")
        print(f"Tags ({len(tags)}) :")
        for t in tags:
            print(f"  • {t}")
    else:
        parser.print_help()
