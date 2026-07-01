import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser
from app.graph.graph_schema import setup_constraints, ingest_knowledge_graph
from app.graph.graph_query import graph_query
from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Corporate Actions RAG"])


class GraphQueryRequest(BaseModel):
    question: str
    ticker: Optional[str] = None


@router.post("/graph/ingest")
async def ingest_graph(
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """Ingest knowledge graph (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Starting knowledge graph ingestion",
        extra={"user_id": user_id}
    )
    
    try:
        setup_constraints()
        stats = ingest_knowledge_graph()
        
        logger.info(
            "Knowledge graph ingestion complete",
            extra={"user_id": user_id, "stats": stats}
        )
        
        return {"ok": True, "stats": stats}
    except Exception as e:
        logger.error(
            "Knowledge graph ingestion failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/company/{ticker}")
async def company_overview(
    ticker: str,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """Get company overview from graph (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Company overview requested",
        extra={"user_id": user_id, "ticker": ticker}
    )
    
    try:
        res = graph_query.get_company_overview(ticker)
        if not res:
            raise HTTPException(status_code=404, detail="Company not found")
        
        logger.info(
            "Company overview retrieved",
            extra={"user_id": user_id, "ticker": ticker}
        )
        
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Company overview query failed",
            extra={"user_id": user_id, "ticker": ticker, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/actions")
async def corporate_actions(
    current_user: CurrentUser,
    ticker: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """Get corporate actions from graph (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Corporate actions requested",
        extra={"user_id": user_id, "ticker": ticker, "action_type": action_type}
    )
    
    try:
        results = graph_query.get_corporate_actions(ticker=ticker, action_type=action_type)
        
        logger.info(
            "Corporate actions retrieved",
            extra={"user_id": user_id, "count": len(results)}
        )
        
        return results
    except Exception as e:
        logger.error(
            "Corporate actions query failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/metrics")
async def metrics(
    current_user: CurrentUser,
    metric_type: str = Query(...),
    min_value: Optional[float] = Query(None),
    quarter: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """Get financial metrics from graph (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Metrics query requested",
        extra={"user_id": user_id, "metric_type": metric_type, "min_value": min_value, "quarter": quarter}
    )
    
    try:
        results = graph_query.get_companies_by_metric(
            metric_type,
            min_value=min_value,
            quarter=quarter
        )
        
        logger.info(
            "Metrics retrieved",
            extra={"user_id": user_id, "count": len(results)}
        )
        
        return results
    except Exception as e:
        logger.error(
            "Metrics query failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/competitors/{ticker}")
async def competitors(
    ticker: str,
    current_user: CurrentUser,
) -> List[Dict[str, Any]]:
    """Get competitor information from graph (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Competitors query requested",
        extra={"user_id": user_id, "ticker": ticker}
    )
    
    try:
        results = graph_query.get_competitors(ticker)
        
        logger.info(
            "Competitors retrieved",
            extra={"user_id": user_id, "ticker": ticker, "count": len(results)}
        )
        
        return results
    except Exception as e:
        logger.error(
            "Competitors query failed",
            extra={"user_id": user_id, "ticker": ticker, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/query")
async def graph_nl_query(
    req: GraphQueryRequest,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """Natural language query to graph (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Natural language graph query requested",
        extra={"user_id": user_id, "question_preview": req.question[:80]}
    )
    
    try:
        results = graph_query.natural_language_to_graph(req.question)
        
        logger.info(
            "Natural language query results retrieved",
            extra={"user_id": user_id, "count": len(results)}
        )
        
        return {"question": req.question, "count": len(results), "results": results}
    except Exception as e:
        logger.error(
            "Natural language graph query failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats")
async def graph_stats(
    current_user: CurrentUser,
) -> Dict[str, Any]:
    """Get graph statistics (authenticated users only)."""
    user_id = str(current_user.id)
    logger.info(
        "Graph stats requested",
        extra={"user_id": user_id}
    )
    
    try:
        connected = neo4j_client.is_connected()
        stats = graph_query.get_graph_stats() if connected else {}
        
        logger.info(
            "Graph stats retrieved",
            extra={"user_id": user_id, "connected": connected}
        )
        
        return {"connected": connected, "stats": stats}
    except Exception as e:
        logger.error(
            "Graph stats query failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
