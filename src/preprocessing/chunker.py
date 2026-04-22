from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class SemanticChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            is_separator_regex=False,
            separators=["\n\n", "\n", " ", ""]
        )
        
    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Splits LangChain documents into overlapping semantic chunks."""
        return self.text_splitter.split_documents(documents)
