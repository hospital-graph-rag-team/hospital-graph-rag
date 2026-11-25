"""Condition list and observational medication analytics endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.schemas.models import ConditionsResponse, MedicationAnalyticsResponse
from backend.security import enforce_api_rate_limit, sanitize_error_message, verify_backend_token
from backend.services.graph_service import get_conditions_summary, get_neo4j_driver
from src.graph.retrieval import get_medication_outcomes

router = APIRouter(
    prefix="/api/v1",
    tags=["Analytics"],
    dependencies=[Depends(verify_backend_token), Depends(enforce_api_rate_limit)],
)


@router.get("/conditions", response_model=ConditionsResponse, summary="List tracked chronic conditions")
def read_conditions(driver: Any = Depends(get_neo4j_driver)) -> ConditionsResponse:
    try:
        conditions = get_conditions_summary(driver=driver)
        return ConditionsResponse(conditions=conditions)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve conditions."),
        )


@router.get(
    "/analytics/medications",
    response_model=MedicationAnalyticsResponse,
    summary="Get synthetic observational medication outcomes for a condition",
)
def read_medication_analytics(
    condition: str = Query(..., min_length=2, max_length=80),
    driver: Any = Depends(get_neo4j_driver),
) -> MedicationAnalyticsResponse:
    cleaned = condition.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Condition must be non-empty.")
    try:
        result = get_medication_outcomes(cleaned, driver=driver)
        return MedicationAnalyticsResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to compute medication analytics."),
        )
