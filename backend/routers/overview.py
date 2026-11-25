"""Hospital overview dashboard endpoints."""

from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.schemas.models import OverviewResponse
from backend.security import enforce_api_rate_limit, sanitize_error_message, verify_backend_token
from backend.services.graph_service import get_neo4j_driver, get_overview_data

router = APIRouter(
    prefix="/api/v1",
    tags=["Overview"],
    dependencies=[Depends(verify_backend_token), Depends(enforce_api_rate_limit)],
)


@router.get("/overview", response_model=OverviewResponse, summary="Get cohort overview statistics")
def read_overview(
    time_range: Literal["all", "12m", "6m", "2024", "2023"] = Query(
        default="all",
        description="Time window applied to the visits-over-time series.",
    ),
    driver: Any = Depends(get_neo4j_driver),
) -> OverviewResponse:
    try:
        return get_overview_data(driver=driver, time_range=time_range)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve hospital overview from Neo4j."),
        )
