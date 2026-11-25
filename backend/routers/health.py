"""Health check endpoint for Render and monitoring."""

from datetime import datetime, timezone
from fastapi import APIRouter

from backend.config import get_settings
from backend.schemas.models import HealthResponse
from backend.services.graph_service import check_neo4j_connectivity

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health_check() -> HealthResponse:
    settings = get_settings()
    neo4j_ok = check_neo4j_connectivity() if settings.neo4j_configured else False
    overall_status = "ok" if (neo4j_ok and settings.groq_configured) else "degraded"
    return HealthResponse(
        status=overall_status,
        environment=settings.environment,
        neo4j_connected=neo4j_ok,
        groq_configured=settings.groq_configured,
        model_name=settings.model_name,
        auth_enabled=bool(settings.backend_api_token),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
