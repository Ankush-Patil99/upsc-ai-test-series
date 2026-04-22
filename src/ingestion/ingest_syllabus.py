import os
import yaml
from uuid import uuid4
from langchain_core.documents import Document
from langchain_postgres.vectorstores import PGVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

# Load config
load_dotenv()
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

print("Loading local embeddings model...")
embeddings = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])

print("Connecting to PGVector...")
connection = config["db"]["postgres_url"]
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="upsc_collection",
    connection=connection,
    use_jsonb=True,
)

from src.ingestion.syllabus_extractor import GS2LevelExtractor
extractor = GS2LevelExtractor()
taxonomy = extractor.extract_from_text("")

docs = []
for item in taxonomy:
    topic = item["topic"]
    subtopic = item["subtopic"]
    text_representation = f"Syllabus Structural Definition: Topic: {topic} | Subtopic: {subtopic}"
    doc = Document(
        page_content=text_representation,
        metadata={"source": "syllabus_pdf", "type": "syllabus_structure", "topic": topic, "subtopic": subtopic}
    )
    docs.append(doc)

print(f"Adding {len(docs)} structural syllabus topics to the Vector Database...")
vector_store.add_documents(docs, ids=[str(uuid4()) for _ in range(len(docs))])
print("Syllabus Taxonomy inserted safely.")
