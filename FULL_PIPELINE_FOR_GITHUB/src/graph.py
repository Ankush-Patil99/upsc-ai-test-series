"""
graph.py — Final LangGraph pipeline wiring for UPSC AI Engine V2.0

Architecture (blueprint Section 2 & 4):
  Node 1 (Input Controller)    → Node 2 (Content Researcher)
  Node 2                       → Node 3 (Question Drafter)
  Node 3                       → Node 4 (Distractor Engineer)
  Node 4                       → Node 5 (Structure Formatter)
  Node 5                       → Node 6 (QA Orchestrator)
  Node 6 → APPROVE             → END (write output JSON)
  Node 6 → RETRY (max 3)       → targeted node (per Section 5.2 routing table)
  Node 6 → HARD FAIL (>3 tries)→ END (logged as FAILED)

Checkpointing: LangGraph SqliteSaver for crash recovery.
"""

import logging
import os

from langgraph.graph import StateGraph, END
# from langgraph_checkpoint_sqlite import SqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from src.state import QuestionState
from src.config import CHECKPOINT_DB_PATH, MAX_RETRIES, QA_PASS_THRESHOLD
from src.nodes.node_6_orchestrator import RETRY_ROUTE_MAP

from src.nodes.node_1_controller   import input_controller_node
from src.nodes.node_2_researcher   import content_researcher_node
from src.nodes.node_3_drafter      import question_drafter_node
from src.nodes.node_4_engineer     import distractor_engineer_node
from src.nodes.node_5_formatter    import structure_formatter_node
from src.nodes.node_6_orchestrator import qa_orchestrator_node

from src.utils import setup_logger
logger = setup_logger(__name__)

# Node name constants (matches RETRY_ROUTE_MAP values)
NODE_CONTROLLER  = "input_controller"
NODE_RESEARCHER  = "content_researcher"
NODE_DRAFTER     = "question_drafter"
NODE_ENGINEER    = "distractor_engineer"
NODE_FORMATTER   = "structure_formatter"
NODE_ORCHESTRATOR= "qa_orchestrator"


def route_after_qa(state: QuestionState) -> str:
    """
    Conditional routing after Node 6 (QA Orchestrator).
    Implements the retry routing table from blueprint Section 5.2.

    Returns:
        - END             if approved or max retries exceeded
        - node_name (str) to route back to for targeted retry
    """
    approved     = state.get("approved", False)
    retry_count  = state.get("retry_count", 0)
    qa_flags     = state.get("qa_flags", [])

    # ── Approved → done ──────────────────────────────────────────────────────
    if approved:
        logger.info(f"[Graph] Question APPROVED. qa_score={state.get('qa_score'):.4f}. Routing to END.")
        return END

    # ── Hard fail: exceeded max retries ──────────────────────────────────────
    if retry_count > MAX_RETRIES:
        logger.warning(f"[Graph] Hard FAIL — {retry_count} retries exhausted. Routing to END.")
        return END

    # ── Targeted retry: find worst dimension in qa_flags ─────────────────────
    # qa_flags contains the names of failing dimensions (worst first)
    # Map each flag to its responsible node using RETRY_ROUTE_MAP
    for flag in qa_flags:
        target_node = RETRY_ROUTE_MAP.get(flag)
        if target_node:
            logger.info(f"[Graph] RETRY → Routing back to '{target_node}' due to flag '{flag}'.")
            return target_node

    # ── Fallback: re-draft if no specific flag matches ────────────────────────
    logger.info(f"[Graph] No specific flag matched. Defaulting retry to '{NODE_DRAFTER}'.")
    return NODE_DRAFTER


def build_graph(use_checkpointing: bool = True):
    """
    Builds and compiles the full 6-node LangGraph pipeline.

    Args:
        use_checkpointing: If True, attaches SqliteSaver for crash recovery.

    Returns:
        Compiled LangGraph app ready for .invoke() or .stream()
    """
    workflow = StateGraph(QuestionState)

    # ── Register all 6 nodes ─────────────────────────────────────────────────
    workflow.add_node(NODE_CONTROLLER,   input_controller_node)
    workflow.add_node(NODE_RESEARCHER,   content_researcher_node)
    workflow.add_node(NODE_DRAFTER,      question_drafter_node)
    workflow.add_node(NODE_ENGINEER,     distractor_engineer_node)
    workflow.add_node(NODE_FORMATTER,    structure_formatter_node)
    workflow.add_node(NODE_ORCHESTRATOR, qa_orchestrator_node)

    # ── Set entry point ───────────────────────────────────────────────────────
    workflow.set_entry_point(NODE_CONTROLLER)

    # ── Linear path (first pass) ──────────────────────────────────────────────
    workflow.add_edge(NODE_CONTROLLER,   NODE_RESEARCHER)
    workflow.add_edge(NODE_RESEARCHER,   NODE_DRAFTER)
    workflow.add_edge(NODE_DRAFTER,      NODE_ENGINEER)
    workflow.add_edge(NODE_ENGINEER,     NODE_FORMATTER)
    workflow.add_edge(NODE_FORMATTER,    NODE_ORCHESTRATOR)

    # ── Conditional routing after QA ──────────────────────────────────────────
    # Maps each possible return value of route_after_qa to a destination
    workflow.add_conditional_edges(
        NODE_ORCHESTRATOR,
        route_after_qa,
        {
            NODE_CONTROLLER:  NODE_CONTROLLER,
            NODE_RESEARCHER:  NODE_RESEARCHER,
            NODE_DRAFTER:     NODE_DRAFTER,
            NODE_ENGINEER:    NODE_ENGINEER,
            NODE_FORMATTER:   NODE_FORMATTER,
            END:              END,
        }
    )

    # ── Compile with optional checkpointing ──────────────────────────────────
    if use_checkpointing:
        os.makedirs(os.path.dirname(CHECKPOINT_DB_PATH), exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        app = workflow.compile(checkpointer=checkpointer)
        logger.info(f"[Graph] Pipeline compiled WITH checkpointing → {CHECKPOINT_DB_PATH}")
    else:
        app = workflow.compile()
        logger.info("[Graph] Pipeline compiled WITHOUT checkpointing.")

    return app
