import logging
from typing import Optional

import chromadb
from langchain_core.documents import Document

from app.config import get_settings
from app.rag.embeddings import get_embeddings, get_query_embeddings

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = "data/chroma_db"
COLLECTION_NAME = "earnings_transcripts"


class ChromaVectorStoreService:
    """Service for managing ChromaDB vector store operations."""

    def __init__(self):
        self._client = None
        self._collection = None

    def _initialize(self):
        """Initialize ChromaDB client and collection if not already done."""
        if self._client is not None:
            return

        try:
            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)

            logger.info(
                "ChromaDB initialized",
                extra={"persist_dir": CHROMA_PERSIST_DIR, "collection": COLLECTION_NAME}
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def ingest(self, chunks: list[Document]) -> int:
        """Ingest document chunks into the vector store."""
        if not chunks:
            return 0

        try:
            self._initialize()

            ids = [chunk.metadata.get("chunk_id", f"chunk_{i}") for i, chunk in enumerate(chunks)]
            documents = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            embedder = get_embeddings()
            embeddings = []
            for document in documents:
                single_emb = embedder.embed_documents([document])
                if isinstance(single_emb, list) and len(single_emb) == 1:
                    embeddings.append(single_emb[0])
                else:
                    embeddings.extend(single_emb)

            if len(embeddings) != len(documents):
                raise ValueError(
                    f"Embedding count {len(embeddings)} does not match document count {len(documents)}"
                )

            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
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
        """Query the vector store for relevant documents."""
        try:
            self._initialize()

            where = None
            if filter_company:
                where = {"company": {"$contains": filter_company}}

            query_embedding = get_query_embeddings().embed_query(question)

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            documents = []
            if results.get("documents") and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    documents.append(
                        Document(
                            page_content=results["documents"][0][i],
                            metadata=results["metadatas"][0][i]
                        )
                    )

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
        """Return vector store statistics."""
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
            return {"status": "empty", "vectors": 0}


# Module-level singleton
vector_store = ChromaVectorStoreService()
