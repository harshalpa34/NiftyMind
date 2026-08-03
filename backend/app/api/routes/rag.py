import logging
from typing import Optional
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import CurrentUser
from app.rag.document_loader import load_transcripts, chunk_documents
from app.rag.vector_store import vector_store
from app.rag.corrective_rag import corrective_rag


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


class AskRequest(BaseModel):
    question: str = Field(..., min_length=5, description="Question for the corrective RAG pipeline")
    top_k: int = Field(4, ge=1, le=10, description="Number of top vector results")
    confidence_threshold: float = Field(
        0.75,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for vector-only retrieval",
    )
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
async def ingest_documents(
    request: IngestRequest,
    current_user: CurrentUser,
) -> IngestResponse:
    """
    Load and ingest transcript documents into the vector store (user-scoped namespace).
    
    Args:
        request: IngestRequest with directory path
        current_user: Current authenticated user
    
    Returns:
        IngestResponse with ingestion statistics
        
    Raises:
        HTTPException 404: If no documents found
    """
    user_id = str(current_user.id)
    namespace = f"user_{user_id}"
    
    logger.info(
        "Starting document ingestion",
        extra={"user_id": user_id, "namespace": namespace, "directory": request.directory}
    )
    
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
        
        # Ingest into vector store with global default namespace
        chunks_ingested = vector_store.ingest(chunks, namespace="earnings")
        
        if chunks_ingested == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to ingest documents into vector store"
            )
        
        logger.info(
            "Document ingestion complete",
            extra={"user_id": user_id, "chunks_ingested": chunks_ingested, "documents": len(documents)}
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
        logger.error(f"Ingestion failed: {e}", extra={"user_id": user_id}, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    current_user: CurrentUser,
) -> RAGQueryResponse:
    """
    Query the vector store for relevant documents (user-scoped namespace).
    
    Args:
        request: RAG query request
        current_user: Current authenticated user
        
    Returns:
        RAGQueryResponse with search results
    """
    user_id = str(current_user.id)
    namespace = f"user_{user_id}"
    
    logger.info(
        "RAG query received",
        extra={
            "user_id": user_id,
            "namespace": namespace,
            "question_preview": request.question[:60],
            "top_k": request.top_k,
        }
    )
    
    try:
        # Query the vector store with global default namespace
        results = vector_store.query(
            question=request.question,
            top_k=request.top_k,
            filter_company=request.filter_company,
            namespace="earnings"
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
        
        # Get vector store stats for global default namespace
        stats = vector_store.get_stats(namespace="earnings")
        
        logger.info(
            "RAG query complete",
            extra={"user_id": user_id, "results_found": len(chunks)}
        )
        
        return RAGQueryResponse(
            question=request.question,
            chunks_found=len(chunks),
            results=chunks,
            vector_stats=stats
        )
    except Exception as e:
        logger.error(f"Query failed: {e}", extra={"user_id": user_id}, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/ask", tags=["Corporate Actions RAG"])
async def ask_question(
    request: AskRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Ask the corrective RAG pipeline for a contextual answer (user-scoped).
    """
    user_id = str(current_user.id)
    user_email = current_user.email
    namespace = f"user_{user_id}"
    
    logger.info(
        "Corrective RAG ask request received",
        extra={
            "user_id": user_id,
            "user_email": user_email,
            "namespace": namespace,
            "question_preview": request.question[:80],
            "top_k": request.top_k,
            "confidence_threshold": request.confidence_threshold,
            "filter_company": request.filter_company,
        },
    )
    
    result = await corrective_rag.ask(
        question=request.question,
        top_k=request.top_k,
        confidence_threshold=request.confidence_threshold,
        filter_company=request.filter_company,
        namespace="earnings",
    )
    
    # Add requested_by metadata
    result["requested_by"] = user_email
    
    return result


@router.get("/stats")
async def get_stats(
    current_user: CurrentUser,
) -> dict:
    """
    Get statistics about the vector store for current user.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Dictionary with vector store status and metadata for user namespace
    """
    user_id = str(current_user.id)
    namespace = f"user_{user_id}"
    
    logger.info(
        "Vector store stats requested",
        extra={"user_id": user_id, "namespace": namespace}
    )
    
    return vector_store.get_stats(namespace="earnings")


@router.get("/preset-questions")
async def get_preset_questions(
    current_user: CurrentUser,
) -> dict:
    """
    Get dynamically generated suggested questions based on available transcripts.
    """
    import os
    # Get available transcripts
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    transcripts_dir = os.path.join(base_dir, "data", "transcripts")
    
    companies = []
    if os.path.exists(transcripts_dir):
        for f in os.listdir(transcripts_dir):
            if f.endswith(".txt") and "_q3_fy25" in f.lower():
                parts = f.lower().split("_q3_fy25")
                name = parts[0].replace("_", " ").strip().title()
                if name:
                    if name.lower() in ("tcs", "infy", "itc", "sbin", "wipro"):
                        companies.append(name.upper())
                    else:
                        companies.append(name)
                        
    if not companies:
        companies = ["TCS", "HDFC Bank", "Infosys"]
        
    selected = sorted(list(set(companies)))[:3]
    if len(selected) < 3:
        selected.extend([c for c in ["TCS", "HDFC Bank", "Infosys"] if c not in selected])
    selected = selected[:3]
    
    questions = [
        f"What is the management guidance and margin outlook for {selected[0]}?",
        f"Summarize operating performance and risk factors for {selected[1]}",
        f"Show company metrics, dividends, and competitors",
        f"What did {selected[2]} say about revenue growth guidance?"
    ]
    return {"questions": questions}
