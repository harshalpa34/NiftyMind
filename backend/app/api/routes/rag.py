import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.document_loader import load_transcripts, chunk_documents
from app.rag.vector_store import vector_store


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["Corporate Actions RAG"])


# ============================================================================
# Pydantic Models
# ============================================================================

class IngestResponse(BaseModel):
    """Response for document ingestion."""
    status: str
    documents_loaded: int
    chunks_ingested: int
    message: str


class IngestRequest(BaseModel):
    """Request for document ingestion."""
    directory: str = Field(
        "data/transcripts",
        description="Directory containing transcript files"
    )


class RAGQueryRequest(BaseModel):
    """Request for RAG query."""
    question: str = Field(..., min_length=5, description="Query question")
    top_k: int = Field(4, ge=1, le=10, description="Number of top results")
    filter_company: Optional[str] = Field(None, description="Optional company filter")


class RAGChunk(BaseModel):
    """Single result chunk from RAG query."""
    content: str
    company: str
    quarter: str
    source: str
    chunk_id: str


class RAGQueryResponse(BaseModel):
    """Response for RAG query."""
    question: str
    chunks_found: int
    results: list[RAGChunk]
    vector_stats: dict


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest_documents(request: IngestRequest) -> IngestResponse:
    """
    Load and ingest transcript documents into the vector store.
    
    Args:
        request: IngestRequest with directory path
    
    Returns:
        IngestResponse with ingestion statistics
        
    Raises:
        HTTPException 404: If no documents found
    """
    try:
        # Load transcripts from specified directory
        documents = load_transcripts(directory=request.directory)
        
        if not documents:
            raise HTTPException(
                status_code=404,
                detail=f"No transcript files found in {request.directory} directory"
            )
        
        # Chunk documents
        chunks = chunk_documents(documents)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="Failed to chunk documents"
            )
        
        # Ingest into vector store
        chunks_ingested = vector_store.ingest(chunks)
        
        if chunks_ingested == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to ingest documents into vector store"
            )
        
        return IngestResponse(
            status="success",
            documents_loaded=len(documents),
            chunks_ingested=chunks_ingested,
            message=f"Successfully ingested {chunks_ingested} chunks from {len(documents)} documents"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(request: RAGQueryRequest) -> RAGQueryResponse:
    """
    Query the vector store for relevant documents.
    
    Args:
        request: RAG query request
        
    Returns:
        RAGQueryResponse with search results
    """
    try:
        # Query the vector store
        results = vector_store.query(
            question=request.question,
            top_k=request.top_k,
            filter_company=request.filter_company
        )
        
        # Map results to RAGChunk objects
        chunks = []
        for doc in results:
            chunks.append(
                RAGChunk(
                    content=doc.page_content,
                    company=doc.metadata.get("company", "Unknown"),
                    quarter=doc.metadata.get("quarter", "Unknown"),
                    source=doc.metadata.get("source", "Unknown"),
                    chunk_id=doc.metadata.get("chunk_id", "Unknown")
                )
            )
        
        # Get vector store stats
        stats = vector_store.get_stats()
        
        return RAGQueryResponse(
            question=request.question,
            chunks_found=len(chunks),
            results=chunks,
            vector_stats=stats
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.get("/stats")
async def get_stats() -> dict:
    """
    Get statistics about the vector store.
    
    Returns:
        Dictionary with vector store status and metadata
    """
    return vector_store.get_stats()
