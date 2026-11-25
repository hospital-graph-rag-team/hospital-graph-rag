"""FastAPI application entrypoint for ClinicalGraph 2.0."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import analytics, chat, graph, health, overview, patients
from backend.services.graph_service import close_shared_driver, init_shared_driver


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.neo4j_configured:
        try:
            init_shared_driver()
        except Exception:
            # Allow startup even if Neo4j is transiently unavailable; /health reports degraded.
            pass
    try:
        yield
    finally:
        close_shared_driver()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ClinicalGraph 2.0 API",
        description=(
            "Read-only REST API for ClinicalGraph 2.0, exposing Neo4j synthetic hospital knowledge graph "
            "retrieval, longitudinal biomarker analytics, and the Groq ReAct Clinical RAG engine."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Backend-Token"],
    )

    app.include_router(health.router)
    app.include_router(overview.router)
    app.include_router(patients.router)
    app.include_router(graph.router)
    app.include_router(analytics.router)
    app.include_router(chat.router)

    return app


app = create_app()
