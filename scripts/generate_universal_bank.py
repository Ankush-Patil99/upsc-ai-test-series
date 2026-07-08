import os
import sys
import json
import time
from sqlalchemy.orm import Session
from datetime import datetime

# Adjust path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.models import SessionLocal, UniversalQuestionBank
from src.mcq_generation.generator import LangGraphMCQGenerator
from langchain_huggingface import HuggingFaceEmbeddings
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

print("Loading Embedding Model...")
embeddings = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])

print("Initializing LangGraph MCQ Generator...")
generator = LangGraphMCQGenerator()

def generate_and_store_questions(subject: str, topics: list, count_per_topic: int):
    db: Session = SessionLocal()
    
    total_generated = 0
    for topic in topics:
        print(f"\n--- Generating {count_per_topic} questions for Topic: {topic} ---")
        for i in range(count_per_topic):
            print(f"Attempt {i+1}/{count_per_topic} for {topic}...")
            
            try:
                # To encourage variety, we can append a random sub-focus or just rely on the LLM's temperature
                # Since LangGraphMCQGenerator uses "medium" default, we'll randomize difficulty slightly
                difficulties = ["medium", "hard", "hard"]
                diff = difficulties[i % len(difficulties)]
                
                # We can modify the topic slightly to force variety
                variation = f"{topic} (Focus on varied sub-themes, obscure facts, or analytical statements)"
                
                result = generator.generate(topic=variation, difficulty=diff)
                
                mcq = result.get("mcq", {})
                mains_fact = result.get("mains_facts", "")
                
                question_text = mcq.get("question")
                options = mcq.get("options", [])
                correct = mcq.get("correct")
                explanation = mcq.get("explanation", "")
                
                if not question_text or not options or not correct:
                    print(f"Failed to generate valid MCQ structure. Skipping. Result: {mcq}")
                    continue
                
                # Check if question already exists
                existing = db.query(UniversalQuestionBank).filter(UniversalQuestionBank.question == question_text).first()
                if existing:
                    print("Duplicate question detected. Skipping.")
                    continue
                
                print(f"Generated Question: {question_text}")
                
                # Embed question for semantic search
                embed_text = f"Subject: {subject}. Topic: {topic}. Question: {question_text} Options: {', '.join(options)}"
                vector = embeddings.embed_query(embed_text)
                
                # Insert into database
                q_entry = UniversalQuestionBank(
                    subject=subject,
                    topic=topic,
                    question=question_text,
                    options_json=json.dumps(options),
                    correct_option=correct,
                    rationale=explanation,
                    mains_hint=mains_fact,
                    difficulty=diff,
                    embedding=vector
                )
                
                db.add(q_entry)
                db.commit()
                total_generated += 1
                
                print(f"Successfully saved to database! (Total: {total_generated})")
                
            except Exception as e:
                print(f"Error during generation: {e}")
                db.rollback()
            
            # Sleep to respect rate limits
            time.sleep(2)
            
    db.close()
    print(f"\nFinished. Successfully generated and stored {total_generated} questions.")

if __name__ == "__main__":
    # Starting with History & Art and Culture
    history_topics = [
        "Indus Valley Civilization",
        "Vedic Period",
        "Mauryan Empire",
        "Gupta Empire",
        "Delhi Sultanate",
        "Mughal Empire",
        "Indian National Congress",
        "Gandhian Era"
    ]
    
    art_culture_topics = [
        "Temple Architecture (Nagara and Dravida)",
        "Buddhism and Jainism Philosophy",
        "Classical Dances of India",
        "Mughal Architecture and Paintings"
    ]
    
    # We generate 2 questions per topic for this initial run. 
    # The user can scale this up to 100+ per topic for their 11000 question dataset.
    print("=== STARTING BATCH GENERATION FOR HISTORY ===")
    generate_and_store_questions("Ancient and Medieval History", history_topics[:2], count_per_topic=2)
    
    print("\n=== STARTING BATCH GENERATION FOR ART & CULTURE ===")
    generate_and_store_questions("Art and Culture", art_culture_topics[:1], count_per_topic=2)
