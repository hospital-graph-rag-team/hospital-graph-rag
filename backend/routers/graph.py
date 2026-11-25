"""Cohort-level knowledge graph exploration endpoints."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.schemas.models import KnowledgeGraphResponse
from backend.security import enforce_api_rate_limit, sanitize_error_message, verify_backend_token
from backend.services.graph_service import get_cohort_graph, get_neo4j_driver

router = APIRouter(
    prefix="/api/v1/graph",
    tags=["Knowledge Graph"],
    dependencies=[Depends(verify_backend_token), Depends(enforce_api_rate_limit)],
)


@router.get("/cohort", response_model=KnowledgeGraphResponse, summary="Get multi-patient cohort subgraph")
def read_cohort_graph(
    condition: Optional[str] = Query(default=None, max_length=80),
    limit: int = Query(default=6, ge=1, le=15),
    driver: Any = Depends(get_neo4j_driver),
) -> KnowledgeGraphResponse:
    try:
        return get_cohort_graph(driver=driver, condition=condition, limit_patients=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to build cohort knowledge graph."),
        )
