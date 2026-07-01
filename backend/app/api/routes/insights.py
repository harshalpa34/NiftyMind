from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from app.auth.dependencies import CurrentUser
from app.rag.corrective_rag import corrective_rag

router = APIRouter(prefix="/company-insights", tags=["Corporate Intelligence RAG"])

class CompanyInsightsQuery(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=50, description="Company stock symbol, e.g. INFY, TCS")
    question: str = Field(..., min_length=5, description="Question about company earnings, guidance, or risks")
    top_k: int = Field(4, ge=1, le=10, description="Number of source chunks to retrieve")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Confidence threshold for vector retrieval")

@router.post("", status_code=status.HTTP_200_OK)
async def api_get_company_insights(
    query: CompanyInsightsQuery,
    current_user: CurrentUser
):
    """
    Query the Corporate Intelligence RAG pipeline for a specific company symbol.
    
    Searches earnings transcripts, annual reports, and investor presentations
    to answer company-specific fundamentals questions.
    """
    try:
        # Call the existing corrective RAG pipeline, passing the ticker as a filter
        result = await corrective_rag.ask(
            question=query.question,
            top_k=query.top_k,
            confidence_threshold=query.confidence_threshold,
            filter_company=query.ticker.upper().strip()
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query execution failed: {str(e)}"
        )
