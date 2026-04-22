import os
import yaml
from uuid import uuid4
from langchain_community.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy import create_engine
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.agents.classifier import ClassifierAgent
from langchain_core.documents import Document

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

class CAUpdaterNode:
    def __init__(self):
        self.classifier = ClassifierAgent()
        self.embeddings = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            length_function=len
        )
        self.db_url = config["db"]["postgres_url"]
        
    def execute(self, raw_articles: list):
        print(f"\n[Updater] Processing {len(raw_articles)} raw Current Affairs structures...")
        
        # 1. Semantic Chunking
        documents = []
        for article in raw_articles:
            if not getattr(article, "page_content", None):
                continue
            text_chunks = self.text_splitter.split_text(article.page_content)
            for t in text_chunks:
                doc = Document(page_content=t, metadata={"source_url": article.metadata.get("source", "Unknown")})
                documents.append(doc)
                
        print(f"[Updater] Sliced articles into {len(documents)} semantic chunks. Booting Deduplication engine.")
                
        engine = create_engine(self.db_url, pool_pre_ping=True)
        try:
            vector_store = PGVector(
                embedding_function=self.embeddings,
                collection_name="upsc_collection",
                connection_string=self.db_url,
            )
            
            clean_docs_to_insert = []
            
            for doc in documents:
                # 2. Qwen Classification
                taxonomy = self.classifier.classify_content(doc.page_content)
                doc.metadata["topic"] = taxonomy.get("topic", "Current Affairs")
                doc.metadata["subtopic"] = taxonomy.get("subtopic", "General")
                
                # 3. Exact Deduplication
                try:
                    similar = vector_store.similarity_search_with_score(doc.page_content, k=1)
                    if similar and len(similar) > 0:
                        # PGVector L2 Output: Lower is closer. <0.15 represents almost identical overlapping news paragraphs
                        closest_distance = similar[0][1]
                        if closest_distance < 0.15:
                            continue # Skip embedding, we already possess this fact!
                except Exception as e:
                    pass # First insertion block
                    
                clean_docs_to_insert.append(doc)

            if len(clean_docs_to_insert) > 0:
                print(f"[Updater] Verified {len(clean_docs_to_insert)} structurally original facts. Inserting to core database via PGVector...")
                PGVector.from_documents(
                    documents=clean_docs_to_insert,
                    embedding=self.embeddings,
                    collection_name="upsc_collection",
                    connection_string=self.db_url,
                )
            else:
                print("[Updater] Deduplicator tripped: All scraped chunks perfectly overlapped with existing facts. Insertion skipped.")
                
        except Exception as deep_e:
            print(f"[Updater] Pipeline Sequence Critical Error: {deep_e}")
        finally:
            engine.dispose()
