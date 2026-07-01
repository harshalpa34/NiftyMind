import logging
import time
from typing import Optional

from pinecone import Pinecone, ServerlessSpec
from langchain_core.documents import Document

from app.config import get_settings
from app.rag.embeddings import get_embeddings, get_query_embeddings

logger   = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Pinecone Configuration
# Namespace strategy: store all transcripts in default namespace for now.
# Step 3 introduces per-company namespacing via Neo4j graph metadata.
# ---------------------------------------------------------------------------
DEFAULT_NAMESPACE = "earnings"
EMBEDDING_DIMENSION = settings.embedding_dimension    # Must match Pinecone index config


class PineconeVectorStoreService:
    """
    Production vector store using Pinecone serverless.

    Migration from ChromaDB:
    - Same public interface: ingest(), query(), get_stats()
    - Pinecone requires explicit vector IDs and embeddings
    - Metadata filtering uses Pinecone's native filter syntax
    - Namespacing isolates document sets (per-company in Step 3)

    The Strategy Pattern in action:
    - ChromaDB (Step 1) and Pinecone (Step 2) implement identical interfaces
    - Routes and services never changed — only this file
    - In a real codebase this would be an abstract base class
    """

    def __init__(self):
        self._client: Optional[Pinecone] = None
        self._index  = None

    def _initialize(self) -> None:
        """
        Lazily initializes Pinecone client and connects to index.
        Called before every operation — safe to call multiple times.
        """
        if self._index is not None:
            return

        if not settings.pinecone_api_key:
            raise ValueError(
                "PINECONE_API_KEY not set in .env — "
                "get your key from app.pinecone.io"
            )

        self._client = Pinecone(api_key=settings.pinecone_api_key)
        self._index  = self._client.Index(settings.pinecone_index_name)

        # Verify connection by fetching index stats
        stats = self._index.describe_index_stats()

        logger.info(
            "Pinecone connected",
            extra={
                "index":        settings.pinecone_index_name,
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension":    EMBEDDING_DIMENSION,
            },
        )

    def ingest(self, chunks: list[Document], namespace: str = DEFAULT_NAMESPACE) -> int:
        """
        Embeds and upserts document chunks into Pinecone.

        Pinecone upsert is idempotent — re-ingesting the same chunk_id
        updates it rather than creating a duplicate. Safe to run multiple times.

        Batches in groups of 100 — Pinecone's recommended batch size.
        
        Args:
            chunks: List of Document chunks to ingest
            namespace: Pinecone namespace (default: DEFAULT_NAMESPACE)
        """
        if not chunks:
            logger.warning("No chunks to ingest", extra={"namespace": namespace})
            return 0

        self._initialize()

        logger.info(
            "Starting Pinecone ingestion",
            extra={"chunks": len(chunks), "namespace": namespace},
        )

        embedder   = get_embeddings()
        texts      = [c.page_content for c in chunks]
        embeddings = []
        for i, text in enumerate(texts):
            emb = embedder.embed_documents([text])
            embeddings.append(emb[0])
            logger.debug(
                "Chunk embedded",
                extra={"chunk": i + 1, "total": len(texts)},
            )
        logger.info(
            "All embeddings generated",
            extra={"count": len(embeddings)},
        )
        # Build Pinecone vector records
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = chunk.metadata.get("chunk_id", f"chunk_{i}")

            # Pinecone metadata must be flat key-value pairs
            # Convert all values to strings to avoid type issues
            metadata = {
                k: str(v)
                for k, v in chunk.metadata.items()
                if v is not None
            }
            metadata["text"] = chunk.page_content    # Store text in metadata too

            vectors.append({
                "id":     vector_id,
                "values": embedding,
                "metadata": metadata,
            })

        # Upsert in batches of 100 (Pinecone recommendation)
        batch_size     = 100
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i: i + batch_size]
            self._index.upsert(
                vectors=batch,
                namespace=namespace,
            )
            total_upserted += len(batch)
            logger.debug(
                "Batch upserted",
                extra={"batch": i // batch_size + 1, "vectors": len(batch), "namespace": namespace},
            )

        logger.info(
            "Pinecone ingestion complete",
            extra={
                "vectors_upserted": total_upserted,
                "namespace": namespace,
            },
        )

        return total_upserted

    def query(
        self,
        question: str,
        top_k: int = 4,
        filter_company: Optional[str] = None,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> list[Document]:
        """
        Semantic similarity search over Pinecone index.

        Uses query embeddings (retrieval_query task type) for better
        asymmetric retrieval — short query vs long document chunks.

        Company filtering: Pinecone supports exact metadata filters.
        For partial match (e.g. "TCS" matching "Tata Consultancy Services"),
        we fetch extra results and post-filter in Python.
        
        Args:
            question: Query question
            top_k: Number of top results (default: 4)
            filter_company: Optional company filter (default: None)
            namespace: Pinecone namespace (default: DEFAULT_NAMESPACE)
        """
        self._initialize()

        try:
            # Embed the question
            embedder        = get_query_embeddings()
            query_embedding = embedder.embed_query(question)

            # Fetch extra results when filtering (for post-filter headroom)
            fetch_k = top_k * 4 if filter_company else top_k

            query_response = self._index.query(
                vector=query_embedding,
                top_k=fetch_k,
                namespace=namespace,
                include_metadata=True,
            )

            # Convert Pinecone matches to LangChain Documents
            documents = []
            for match in query_response.get("matches", []):
                metadata = dict(match.get("metadata", {}))
                content  = metadata.pop("text", "")    # Extract stored text

                documents.append(Document(
                    page_content=content,
                    metadata={
                        **metadata,
                        "score": round(match.get("score", 0.0), 4),
                    },
                ))

            # Post-filter by company (case-insensitive substring match)
            if filter_company:
                documents = [
                    d for d in documents
                    if filter_company.lower() in
                       d.metadata.get("company", "").lower()
                ][:top_k]

            logger.info(
                "Pinecone query complete",
                extra={
                    "question_preview": question[:60],
                    "results_found":    len(documents),
                    "filter_company":   filter_company,
                    "namespace":        namespace,
                    "top_score": documents[0].metadata.get("score") if documents else None,
                },
            )

            return documents

        except Exception as exc:
            logger.error(
                "Pinecone query failed",
                extra={"error": str(exc), "namespace": namespace},
                exc_info=True,
            )
            return []

    def get_stats(self, namespace: str = DEFAULT_NAMESPACE) -> dict:
        """Returns Pinecone index statistics for a given namespace.
        
        Args:
            namespace: Pinecone namespace (default: DEFAULT_NAMESPACE)
        """
        try:
            self._initialize()
            stats = self._index.describe_index_stats()

            namespace_stats = stats.get("namespaces", {}).get(
                namespace, {}
            )

            return {
                "status":        "ready",
                "backend":       "pinecone",
                "index":         settings.pinecone_index_name,
                "total_vectors": stats.get("total_vector_count", 0),
                "namespace":     namespace,
                "namespace_vectors": namespace_stats.get("vector_count", 0),
                "dimension":     EMBEDDING_DIMENSION,
            }

        except Exception as exc:
            logger.error(
                "Failed to get Pinecone stats",
                extra={"error": str(exc), "namespace": namespace},
            )
            return {"status": "error", "backend": "pinecone", "vectors": 0}


# --- Module-level singleton ---
vector_store = PineconeVectorStoreService()
