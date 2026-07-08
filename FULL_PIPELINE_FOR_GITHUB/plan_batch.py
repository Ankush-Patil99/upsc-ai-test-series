#!/usr/bin/env python3
"""
plan_batch.py — Dynamic PYQ-Weighted Queue Generator
======================================================
Reads the predefined topics from src/topic_bank.py and queries the ChromaDB
PYQ collection to determine the historical weight (frequency of occurrence) 
of each topic in past UPSC exams. 

It then generates a balanced queue of N questions matching that exact distribution 
and saves it to pipeline_data/topic_queue.json so you can run the pipeline.

Usage:
  python plan_batch.py --count 100
"""

import argparse
import json
import logging
import math
import sys
from collections import Counter
from pathlib import Path

# Fix paths to allow imports
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.topic_bank import TOPIC_BANK
from src.chroma_client import _get_collection, _encode_query, _collection_lock

(BASE_DIR / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(BASE_DIR / "logs" / "plan_batch.log"), mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("plan_batch")

def compute_historical_weights(top_k: int = 50, distance_threshold: float = 0.55) -> dict[int, float]:
    """
    Query ChromaDB for every topic in the TOPIC_BANK.
    Assign a weight to each index based on the similarity of matched PYQs.
    """
    collection = _get_collection()
    
    # Check if PYQ collection is populated
    with _collection_lock:
        try:
            probe = collection.get(where={"source_type": "PYQ"}, limit=1)
            if not probe["ids"]:
                logger.error("No PYQs found in ChromaDB! Please run data_ingestion.py first.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error accessing ChromaDB: {e}")
            sys.exit(1)
            
    logger.info(f"Scanning PYQ distributions for {len(TOPIC_BANK)} possible topics...")
    
    weights = {}
    for i, item in enumerate(TOPIC_BANK):
        topic, subtopic, diff, paper, qtype = item
        query_text = f"{topic} {subtopic} {paper} UPSC exam"
        
        try:
            query_vec = _encode_query(query_text)
            with _collection_lock:
                results = collection.query(
                    query_embeddings=query_vec,
                    n_results=top_k,
                    where={"source_type": "PYQ"},
                    include=["distances"]
                )
                
            distances = results.get("distances", [[]])[0]
            
            # Convert distances to similarity and sum up ones that pass a threshold
            # Cosine distance: 0 = identical. We want close matches.
            score = 0.0
            for d in distances:
                if d < distance_threshold:
                    # Weight scales linearly with closeness (d=0 -> score=1)
                    score += (distance_threshold - d) / distance_threshold
                    
            # Ensure every topic gets at least a tiny baseline weight (e.g., 0.1) 
            # so nothing is strictly 0 if the user asks for a huge number of questions.
            weights[i] = max(score, 0.1)
            
        except Exception as e:
            logger.warning(f"Failed to query {topic} - {subtopic}: {e}")
            weights[i] = 0.1

    return weights

def distribute_questions(weights: dict[int, float], total_questions: int) -> list[int]:
    """
    Distribute integer number of questions across indices based on continuous weights,
    ensuring exactly total_questions are returned.
    Using Highest Remainder (Hare-Niemeyer) Method.
    """
    total_weight = sum(weights.values())
    if total_weight == 0:
        # Fallback to uniform
        return [total_questions // len(weights)] * len(weights)
        
    counts = {}
    remainders = {}
    
    allocated = 0
    for i, w in weights.items():
        share = (w / total_weight) * total_questions
        counts[i] = int(math.floor(share))
        remainders[i] = share - counts[i]
        allocated += counts[i]
        
    # Distribute the remaining questions to the items with highest fractional remainder
    shortfall = total_questions - allocated
    sorted_remainders = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
    
    for i in range(shortfall):
        idx = sorted_remainders[i][0]
        counts[idx] += 1
        
    return counts

def generate_batch(count: int, out_file: Path = None) -> list[dict]:
    weights = compute_historical_weights()
    distribution = distribute_questions(weights, count)
    
    batch = []
    subject_counts = Counter()
    
    for i, (topic, subtopic, diff, paper, qtype) in enumerate(TOPIC_BANK):
        freq = distribution[i]
        for _ in range(freq):
            batch.append({
                "topic": topic,
                "subtopic": subtopic,
                "difficulty": diff,
                "paper": paper,
                "question_type": qtype
            })
            subject_counts[topic] += 1

    # Shuffle so it's not totally ordered
    import random
    random.shuffle(batch)
            
    if out_file:
        with open(out_file, "w") as f:
            json.dump(batch, f, indent=4)
            
        logger.info("="*60)
        logger.info(f"Generated PYQ-Weighted Queue: {len(batch)} questions")
        logger.info("="*60)
        for k, v in subject_counts.most_common():
            logger.info(f"  {v:>3} | {k}")
        logger.info("="*60)
        logger.info(f"Saved to: {out_file}")
        logger.info(f"Run it using: python generate_questions_final.py --batch {out_file}")
        
    return batch

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="Total questions to distribute")
    parser.add_argument("--output", type=str, default="pipeline_data/topic_queue.json")
    args = parser.parse_args()
    
    generate_batch(args.count, Path(args.output))
