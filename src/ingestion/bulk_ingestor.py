import os
import yaml
from uuid import uuid4
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

def run_bulk_ingestion(directory_path: str, base_dir: str, is_pyq: bool = False):
    print(f"\n[Bulk Ingestor] Scanning directory: {directory_path}")
    if not os.path.exists(directory_path):
        print("Directory does not exist.")
        return
        
    pdfs = []
    for root, dirs, files in os.walk(directory_path):
        for f in files:
            if f.endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    
    embeddings = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
    
    log_path = os.path.join(base_dir, "ingestion_checkpoint.log")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            completed_files = set(f.read().splitlines())
    else:
        completed_files = set()
    
    for full_path in pdfs:
        pdf_name = os.path.basename(full_path)
        if pdf_name in completed_files:
            print(f"-> Skipping: {pdf_name} (Already firmly ingested).")
            continue
            
        print(f"-> Extracting: {pdf_name}...")
        try:
            loader = PyPDFLoader(full_path)
            docs = loader.load()
            
            for doc in docs:
                doc.metadata["source_name"] = pdf_name
                # Store boolean-string for PGVector metadata filtering
                doc.metadata["is_pyq"] = "true" if is_pyq else "false"
                
            print(f"   Embedding {len(docs)} pages to PGVector Database...")
            try:
                PGVector.from_documents(
                    documents=docs,
                    embedding=embeddings,
                    collection_name="upsc_collection",
                    connection_string=config["db"]["postgres_url"],
                )
                print(f"   Success: {pdf_name} embedded.")
                
                # Checkpoint Write-to-Disk Memory State for fault-tolerance
                with open(log_path, "a") as f:
                    f.write(pdf_name + "\n")
                    
            except Exception as e:
                print(f"   Database insertion failed for {pdf_name}: {e}")
                
        except Exception as file_e:
            print(f"   Failed to read PDF {pdf_name}: {file_e}")

if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    books_dir = os.path.join(base_dir, "books")
    pyqs_dir = os.path.join(base_dir, "pyqs")
    
    os.makedirs(books_dir, exist_ok=True)
    os.makedirs(pyqs_dir, exist_ok=True)
    
    print("Beginning Bulk Ingestion Protocol...")
    run_bulk_ingestion(books_dir, base_dir, is_pyq=False)
    run_bulk_ingestion(pyqs_dir, base_dir, is_pyq=True)
    print("\nBulk Ingestion Finished!\n")
