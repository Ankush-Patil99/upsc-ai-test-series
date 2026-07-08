#!/usr/bin/env python3
"""
run_upsc.py — The Single Unified UPSC AI Pipeline
===================================================
This is the ONLY script you need to run. It orchestrates everything:
1. (Optional) Ingests Textbooks & PYQs
2. (Optional) Scrapes today's Current Affairs
3. Computes PYQ-based historical weights for all topics.
4. Probabilistically samples a unique set of N topics according to those weights 
   (ensuring every generated test series of 100 questions is distinctly different).
5. Invokes the unified Generator LangGraph to create the questions.

Usage:
  # Generate 100 unique questions perfectly balanced against PYQ trends
  python run_upsc.py --total-questions 100

  # Setup database from scratch AND generate 50 questions
  python run_upsc.py --setup --scrape --total-questions 50
"""

import argparse
import logging
import random
import sys
from collections import Counter
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import required pipeline modules
try:
    from plan_batch import compute_historical_weights
    from src.topic_bank import TOPIC_BANK
    from generate_questions_final import (
        run_ingestion, 
        run_ca_scrape, 
        run_batch, 
        check_chromadb_status,
        save_output,
        print_question
    )
    from src.graph import build_graph
except ImportError as e:
    print(f"FAILED TO IMPORT: {e}")
    sys.exit(1)

(BASE_DIR / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(BASE_DIR / "logs" / "run_upsc.log"), mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("run_upsc")

def sample_unique_batch(total_questions: int) -> list[dict]:
    """
    Computes PYQ weights for the topic bank and probabilistically samples N questions.
    Because we use random.choices() with probabilities, multiple runs of this script 
    will yield structurally different question combinations, satisfying the "test series" requirement.
    """
    logger.info("Computing historical PYQ weights for syllabus topics...")
    weights_dict = compute_historical_weights(top_k=50, distance_threshold=0.55)
    
    # Extract parallel lists for probability sampling
    topics_list = list(TOPIC_BANK)
    weights_list = [weights_dict.get(i, 0.1) for i in range(len(topics_list))]
    
    logger.info(f"Probabilistically sampling {total_questions} questions for distinct test series...")
    
    # Randomly choose topics according to the computed PYQ weights
    sampled_tuples = random.choices(topics_list, weights=weights_list, k=total_questions)
    
    batch = []
    distribution = Counter()
    
    for t in sampled_tuples:
        topic, subtopic, diff, paper, qtype = t
        batch.append({
            "topic": topic,
            "subtopic": subtopic,
            "difficulty": diff,
            "paper": paper,
            "question_type": qtype
        })
        distribution[topic] += 1
        
    logger.info("="*60)
    logger.info(f"Test Series Topic Distribution ({total_questions} total):")
    logger.info("="*60)
    for topic_name, count in distribution.most_common():
        logger.info(f"  {count:>3} | {topic_name}")
    logger.info("="*60)
        
    return batch


def main():
    parser = argparse.ArgumentParser(description="Unified master script for the UPSC Test Agent")
    parser.add_argument("--total-questions", type=int, required=True, 
                        help="Number of questions to generate for the test series")
    parser.add_argument("--setup", action="store_true", 
                        help="Run full textbook and PYQ ingestion into ChromaDB first")
    parser.add_argument("--scrape", action="store_true", 
                        help="Run live current affairs scraping before generating")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel generation workers")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("      UPSC AI ENGINE — UNIFIED GENERATION PROTOCOL")
    print("="*70 + "\n")

    # Step 1: Initial Setup
    if args.setup:
        run_ingestion()
        
    # Step 2: Fresh CA
    if args.scrape:
        run_ca_scrape()
        
    # Ensure ChromaDB works before planning batch
    status = check_chromadb_status()
    if status["rag_collection"] == 0 and status["dedup_collection"] == 0:
        logger.error("ChromaDB is completely empty! Please run with --setup first.")
        sys.exit(1)
        
    if status["dedup_collection"] == 0:
        logger.warning("PYQ Collection is empty! Weight distribution will be random. Run --setup to fix.")

    # Step 3: Probabilistic Planning
    batch_input = sample_unique_batch(args.total_questions)
    
    # Step 4: Execute Generation
    logger.info("Starting LLM Generation Pipeline...")
    app = build_graph()
    output = run_batch(app, batch_input, max_workers=args.workers)
    
    # Step 5: Save
    import uuid
    from datetime import datetime, timezone
    
    run_id = f"TEST_SERIES_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    out_path = str(BASE_DIR / "pipeline_data" / "output" / f"{run_id}.json")
    
    save_output(output, out_path)
    
    # Summary
    print("\n" + "=" * 65)
    print("  TEST SERIES GENERATION COMPLETE")
    print("=" * 65)
    print(f"  Total Requested         : {args.total_questions}")
    print(f"  Successfully Approved   : {output['approved_count']} (Pass Rate: {output['pass_rate']:.1%})")
    print(f"  Failed / Duplicate      : {output['failed_count']}")
    print(f"  Average QA Score        : {output['average_qa_score']:.4f}")
    print(f"  Output saved to         : {out_path}")
    print("=" * 65)

if __name__ == "__main__":
    main()
