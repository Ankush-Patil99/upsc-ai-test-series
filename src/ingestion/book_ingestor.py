import os
import yaml
from uuid import uuid4
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

def ingest_pdf_book(temp_file_path: str, filename: str) -> int:
    """
    Takes a massive reference PDF file, shreds it natively, 
    and embeds it instantly into PGVector for explicit DeepSeek retrieval.
    """
    print(f"[Reference Ingest] Extracting raw strings from {filename} via PyPDFLoader...")
    loader = PyPDFLoader(temp_file_path)
    docs = loader.load()
    
    for doc in docs:
        doc.metadata["source_name"] = filename
        
    print(f"[Reference Ingest] Embedding {len(docs)} pages into primary PGVector database...")
    from langchain_community.vectorstores import PGVector
    embeddings = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
    
    try:
        PGVector.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name="upsc_collection",
            connection_string=config["db"]["postgres_url"],
        )
    except Exception as insert_err:
        print(f"Database insertion failed: {insert_err}")
        raise
        
    print(f"[Reference Ingest] Database insertion entirely completed.")
    return len(docs)
