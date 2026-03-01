import os
import logging
from typing import List, Optional
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Default connection string for local dev (matches docker-compose)
DEFAULT_CONNECTION_STRING = "postgresql+psycopg://ks_los:secure_password@localhost:5432/ks_los_db"
COLLECTION_NAME = "credit_policies"

class KnowledgeBase:
    """
    Manages the RAG system: Ingestion and Retrieval of Policy Documents.
    Uses PGVector (Postgres) and Ollama (nomic-embed-text) for local, private, scientific retrieval.
    """
    
    def __init__(self, connection_string: str = DEFAULT_CONNECTION_STRING):
        self.connection_string = connection_string
        # Use nomic-embed-text for high-quality retrieval
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=COLLECTION_NAME,
            connection=self.connection_string,
            use_jsonb=True,
        )
        
        # Ensure tables and collection exist
        try:
            self.vector_store.create_tables_if_not_exists()
            self.vector_store.create_collection()
        except Exception as e:
            logger.warning(f"Could not initialize PGVector tables/collection (might already exist or connection failed): {e}")

    def ingest_document(self, file_path: str):
        """
        Reads a markdown file, splits it, and adds it to the vector store.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        logger.info(f"Ingesting document: {file_path}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Metadata for citation/traceability
            metadata = {"source": os.path.basename(file_path)}
            
            # Scientific splitting: overlapping chunks to preserve context
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n## ", "\n", " ", ""]
            )
            
            docs = splitter.create_documents([text], metadatas=[metadata])
            
            # Add to vector store
            self.vector_store.add_documents(docs)
            logger.info(f"Successfully added {len(docs)} chunks to Knowledge Base.")
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {e}")
            raise

    def query(self, query_text: str, k: int = 3) -> List[Document]:
        """
        Retrieves relevant documents for a given query using cosine similarity.
        """
        # Similarity search
        try:
            docs = self.vector_store.similarity_search(query_text, k=k)
            return docs
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def clear(self):
        """Clears the collection to ensure a clean state for experiments."""
        try:
            self.vector_store.delete_collection()
            # Recreate collection immediately after deletion so future operations work
            self.vector_store.create_collection()
            logger.info("Knowledge Base collection cleared.")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
