"""Runtime configuration for the ClinicalGraph 2.0 FastAPI backend."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import List

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

for path_entry in (str(ROOT_DIR), str(SRC_DIR)):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)

load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)

DEFAULT_MODEL_NAME = "openai/gpt-oss-120b"


@dataclass(frozen=True)
class BackendSettings:
    """Immutable snapshot of backend runtime configuration."""

    environment: str
    backend_api_token: str
    cors_origins: List[str]
    api_rate_limit_per_minute: int
    chat_rate_limit_per_minute: int
    max_chat_query_length: int
    max_history_messages: int
    chat_timeout_seconds: float
    neo4j_configured: bool
    groq_configured: bool
    model_name: str


def _parse_origins(raw: str) -> List[str]:
    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


def _parse_positive_int(raw: str, default: int) -> int:
    try:
        val = int(raw)
        return val if val > 0 else default
    except (TypeError, ValueError):
        return default


def _parse_positive_float(raw: str, default: float) -> float:
    try:
        val = float(raw)
        return val if val > 0 else default
    except (TypeError, ValueError):
        return default


def get_settings() -> BackendSettings:
    """Reads current environment variables dynamically for testability and runtime clarity."""
    raw_env = os.getenv("ENVIRONMENT", "").strip().lower()
    vercel_env = os.getenv("VERCEL_ENV", "").strip().lower()
    if raw_env:
        environment = raw_env
    elif vercel_env == "production":
        environment = "production"
    else:
        environment = "development"
    backend_api_token = os.getenv("BACKEND_API_TOKEN", "").strip()
    cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    return BackendSettings(
        environment=environment,
        backend_api_token=backend_api_token,
        cors_origins=_parse_origins(cors_raw),
        api_rate_limit_per_minute=_parse_positive_int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "180"), 180),
        chat_rate_limit_per_minute=_parse_positive_int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "20"), 20),
        max_chat_query_length=_parse_positive_int(os.getenv("MAX_CHAT_QUERY_LENGTH", "1500"), 1500),
        max_history_messages=_parse_positive_int(os.getenv("MAX_HISTORY_MESSAGES", "6"), 6),
        chat_timeout_seconds=_parse_positive_float(os.getenv("CHAT_TIMEOUT_SECONDS", "45.0"), 45.0),
        neo4j_configured=bool(os.getenv("NEO4J_URI") and os.getenv("NEO4J_PASSWORD")),
        groq_configured=bool(os.getenv("GROQ_API_KEY")),
        model_name=os.getenv("GROQ_MODEL_NAME", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME,
    )
