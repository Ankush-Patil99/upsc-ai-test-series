from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
import json

class BaseParser:
    def parse(self, source: str) -> list[Document]:
        raise NotImplementedError

class PDFParser(BaseParser):
    def parse(self, source: str) -> list[Document]:
        """Loads and parses PDF using LangChain PyPDFLoader."""
        loader = PyPDFLoader(source)
        return loader.load()

class SyllabusJSONParser(BaseParser):
    def parse(self, source: str) -> list[Document]:
        """Parses a structured JSON syllabus into LangChain Documents."""
        with open(source, 'r', encoding='utf-8') as f:
            data = json.load(f)
        docs = []
        # Fallback dummy logic. Assuming data is a list of dicts.
        if isinstance(data, list):
            for item in data:
                content = json.dumps(item)
                docs.append(Document(page_content=content, metadata={"source": source, "type": "syllabus"}))
        return docs
