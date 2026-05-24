import logging
from typing import Optional

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

from app.config import get_settings


logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = "data/chroma_db"
COLLECTION_NAME = "earnings_transcripts"


class LangChainEmbeddingAdapter(EmbeddingFunction):
    """Adapter to use LangChain GoogleGenerativeAIEmbeddings with ChromaDB"""
    
    def __init__(self, embeddings: GoogleGenerativeAIEmbeddings):
        self.embeddings = embeddings
    
    def __call__(self, input: Documents) -> Embeddings:
        """
        Embed documents using LangChain's GoogleGenerativeAIEmbeddings
        
        Args:
            input: List of documents to embed
            
        Returns:
            List of embeddings (list of floats)
        """
        try:
            return [self.embeddings.embed_query(text) for text in input]
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise


class ChromaVectorStoreService:
    """Service for managing ChromaDB vector store operations."""
    
    def __init__(self):
        self._client = None
        self._collection = None
    
    def _initialize(self):
        """
        Initialize ChromaDB client and collection if not already done.
        """
        if self._client is not None:
            return  # Already initialized
        
        try:
            # Create persistent client
            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            
            # Create embedding function using LangChain's GoogleGenerativeAIEmbeddings
            settings = get_settings()
            langchain_embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=settings.gemini_api_key
            )
            embedding_fn = LangChainEmbeddingAdapter(langchain_embeddings)
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(
                "ChromaDB initialized",
                extra={
                    "persist_dir": CHROMA_PERSIST_DIR,
                    "collection": COLLECTION_NAME
                }
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def ingest(self, chunks: list[Document]) -> int:
        """
        Ingest document chunks into the vector store.
        
        Args:
            chunks: List of Document chunks to ingest
            
        Returns:
            Number of chunks ingested
        """
        if not chunks:
            return 0
        
        try:
            self._initialize()
            
            # Build lists for upsert
            ids = [
                chunk.metadata.get("chunk_id", f"chunk_{i}")
                for i, chunk in enumerate(chunks)
            ]
            documents = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            
            # Upsert into collection (idempotent)
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(
                "Ingestion complete",
                extra={"chunks_ingested": len(chunks)}
            )
            
            return len(chunks)
        except Exception as e:
            logger.error(f"Failed to ingest chunks: {e}")
            return 0
    
    def query(
        self,
        question: str,
        top_k: int = 4,
        filter_company: Optional[str] = None
    ) -> list[Document]:
        """
        Query the vector store for relevant documents.
        
        Args:
            question: Query string
            top_k: Number of top results to return
            filter_company: Optional company filter for results
            
        Returns:
            List of relevant Document chunks
        """
        try:
            self._initialize()
            
            # Build where filter for company if provided
            where = None
            if filter_company:
                where = {"company": {"$eq": filter_company}}
            
            # Query the collection
            results = self._collection.query(
                query_texts=[question],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert results to Document objects
            documents = []
            if results["documents"] and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    doc = Document(
                        page_content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i]
                    )
                    documents.append(doc)
            
            logger.info(
                "Query executed",
                extra={
                    "question_preview": question[:50],
                    "results_count": len(documents),
                    "filter_company": filter_company
                }
            )
            
            return documents
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def get_stats(self) -> dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with store status and metadata
        """
        try:
            self._initialize()
            count = self._collection.count()
            return {
                "status": "ready",
                "vectors": count,
                "persist_dir": CHROMA_PERSIST_DIR,
                "collection": COLLECTION_NAME
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "status": "empty",
                "vectors": 0
            }


# Module-level singleton
vector_store = ChromaVectorStoreService()
