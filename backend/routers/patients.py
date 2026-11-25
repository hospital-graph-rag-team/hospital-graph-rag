"""Patient directory, profile, timeline, lab trends, follow-ups, and subgraph endpoints."""

from typing import Any, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.schemas.models import (
    KnowledgeGraphResponse,
    PatientFollowupsResponse,
    PatientLabTrendsResponse,
    PatientListResponse,
    PatientProfileResponse,
    PatientTimelineResponse,
)
from backend.security import (
    enforce_api_rate_limit,
    sanitize_error_message,
    validate_patient_id,
    verify_backend_token,
)
from backend.services.graph_service import (
    get_neo4j_driver,
    get_patient_graph,
    get_patient_profile_enriched,
    get_patients_directory_enriched,
)
from src.graph.retrieval import get_followup_comparison, get_lab_trends, get_patient_profile, get_patient_timeline

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["Patients"],
    dependencies=[Depends(verify_backend_token), Depends(enforce_api_rate_limit)],
)


@router.get("", response_model=PatientListResponse, summary="List and filter patients")
def list_patients(
    search: Optional[str] = Query(default=None, max_length=100),
    condition: Optional[str] = Query(default=None, max_length=80),
    gender: Optional[str] = Query(default=None, max_length=20),
    sort_by: Literal["patient_id", "name", "visit_count", "latest_visit_date", "age"] = Query(default="patient_id"),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    driver: Any = Depends(get_neo4j_driver),
) -> PatientListResponse:
    try:
        patients = get_patients_directory_enriched(
            driver=driver,
            search=search,
            condition=condition,
            gender=gender,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PatientListResponse(total=len(patients), patients=patients)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve patient directory."),
        )


@router.get("/{patient_id}", response_model=PatientProfileResponse, summary="Get patient demographic profile")
def read_patient_profile(
    patient_id: str,
    driver: Any = Depends(get_neo4j_driver),
) -> PatientProfileResponse:
    pid = validate_patient_id(patient_id)
    try:
        profile = get_patient_profile_enriched(driver=driver, patient_id=pid)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve patient profile."),
        )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {pid} not found.")
    return profile


@router.get("/{patient_id}/timeline", response_model=PatientTimelineResponse, summary="Get chronological patient timeline")
def read_patient_timeline(
    patient_id: str,
    driver: Any = Depends(get_neo4j_driver),
) -> PatientTimelineResponse:
    pid = validate_patient_id(patient_id)
    try:
        profile = get_patient_profile(pid, driver=driver)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {pid} not found.")
        visits = get_patient_timeline(pid, driver=driver)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve patient timeline."),
        )
    return PatientTimelineResponse(patient_id=pid, visit_count=len(visits), visits=visits)


@router.get("/{patient_id}/lab-trends", response_model=PatientLabTrendsResponse, summary="Get patient biomarker trends")
def read_patient_lab_trends(
    patient_id: str,
    test_name: Optional[str] = Query(default=None, max_length=80),
    driver: Any = Depends(get_neo4j_driver),
) -> PatientLabTrendsResponse:
    pid = validate_patient_id(patient_id)
    try:
        profile = get_patient_profile(pid, driver=driver)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {pid} not found.")
        trends = get_lab_trends(pid, test_name=test_name, driver=driver)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve laboratory trends."),
        )
    return PatientLabTrendsResponse(patient_id=pid, trends=trends)


@router.get("/{patient_id}/followups", response_model=PatientFollowupsResponse, summary="Get consecutive follow-up comparisons")
def read_patient_followups(
    patient_id: str,
    driver: Any = Depends(get_neo4j_driver),
) -> PatientFollowupsResponse:
    pid = validate_patient_id(patient_id)
    try:
        profile = get_patient_profile(pid, driver=driver)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {pid} not found.")
        followups = get_followup_comparison(pid, driver=driver)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to retrieve follow-up comparisons."),
        )
    return PatientFollowupsResponse(patient_id=pid, transition_count=len(followups), followups=followups)


@router.get("/{patient_id}/graph", response_model=KnowledgeGraphResponse, summary="Get patient knowledge graph subgraph")
def read_patient_graph(
    patient_id: str,
    driver: Any = Depends(get_neo4j_driver),
) -> KnowledgeGraphResponse:
    pid = validate_patient_id(patient_id)
    try:
        graph = get_patient_graph(driver=driver, patient_id=pid)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitize_error_message(exc, fallback="Failed to build patient knowledge graph."),
        )
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient {pid} not found.")
    return graph
