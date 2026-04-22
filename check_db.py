import yaml
from sqlalchemy import create_engine, text
import json

with open("configs/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

engine = create_engine(config["db"]["postgres_url"])
try:
    with engine.connect() as conn:
        total_chunks = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding")).scalar()
        print(f"=== DATABASE DIAGNOSTICS ===")
        print(f"Total Deep Learning Chunks (Paragraphs) in PGVector: {total_chunks}")
        
        pyq_count = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding WHERE cmetadata->>'is_pyq' = 'true'")).scalar()
        facts_count = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding WHERE cmetadata->>'is_pyq' = 'false'")).scalar()
        ca_count = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding WHERE cmetadata->>'source_url' IS NOT NULL")).scalar()
        
        print(f"Total Standard Book Paragraphs: {facts_count}")
        print(f"Total PYQ History Paragraphs: {pyq_count}")
        print(f"Total Current Affairs News Articles: {ca_count}")
        
        print("\nTop 5 Largest Processed Books (by mathematical chunks):")
        result = conn.execute(text("SELECT cmetadata->>'source_name' as source, count(*) FROM langchain_pg_embedding WHERE cmetadata->>'source_name' IS NOT NULL GROUP BY source ORDER BY count(*) DESC LIMIT 5")).fetchall()
        if not result:
            print("  (No books fully uploaded yet - or metadata schema mismatch)")
        for row in result:
            print(f" - {row[0]}: {row[1]} chunks.")
            
except Exception as e:
    print(f"Diagnostics Failed: {e}")
