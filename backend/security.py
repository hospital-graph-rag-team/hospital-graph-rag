"""Security, authentication, input validation, rate limiting, and error sanitization."""

from collections import defaultdict, deque
import hmac
import re
import threading
import time
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request, status

from backend.config import get_settings

PATIENT_ID_PATTERN = re.compile(r"^P\d{2,6}$")
SENSITIVE_PATTERNS = [
    re.compile(r"neo4j(?:\+ssc|\+s)?://[^\s\"']+", re.IGNORECASE),
    re.compile(r"bolt(?:\+ssc|\+s)?://[^\s\"']+", re.IGNORECASE),
    re.compile(r"gsk_[A-Za-z0-9_\-]+"),
    re.compile(r"(?:password|secret|token|api_key)\s*[=:]\s*[^\s,;]+", re.IGNORECASE),
]


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter keyed by client IP and route scope."""

    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please wait before sending additional requests.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


api_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
chat_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)


def get_client_identifier(request: Request) -> str:
    """Extracts a bounded client identifier from X-Forwarded-For or socket address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first_hop = forwarded.split(",")[0].strip()
        if first_hop:
            return first_hop[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


def verify_backend_token(request: Request) -> None:
    """
    Enforces server-to-server token authentication for private API routes.

    Accepts either `X-Backend-Token` or `Authorization: Bearer <token>`.
    In production, fails closed if BACKEND_API_TOKEN is unconfigured.
    """
    settings = get_settings()
    expected = settings.backend_api_token

    if not expected:
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backend authentication is not configured.",
            )
        return

    provided = request.headers.get("x-backend-token", "").strip()
    if not provided:
        auth_header = request.headers.get("authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:].strip()

    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: missing or invalid backend authentication token.",
        )


def enforce_api_rate_limit(request: Request) -> None:
    """Applies general API sliding window rate limiting per client."""
    settings = get_settings()
    client_id = get_client_identifier(request)
    api_rate_limiter.check(f"api:{client_id}", settings.api_rate_limit_per_minute)


def enforce_chat_rate_limit(request: Request) -> None:
    """Applies stricter sliding window rate limiting for Groq-backed AI Assistant requests."""
    settings = get_settings()
    client_id = get_client_identifier(request)
    chat_rate_limiter.check(f"chat:{client_id}", settings.chat_rate_limit_per_minute)


def validate_patient_id(patient_id: str) -> str:
    """Validates patient identifier format (e.g., P101) to prevent malformed query inputs."""
    cleaned = (patient_id or "").strip()
    if not PATIENT_ID_PATTERN.fullmatch(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid patient_id format. Expected identifier such as P101.",
        )
    return cleaned


def validate_optional_patient_id(patient_id: Optional[str]) -> Optional[str]:
    """Validates optional patient identifier context."""
    if patient_id is None:
        return None
    cleaned = patient_id.strip()
    if not cleaned:
        return None
    return validate_patient_id(cleaned)


def sanitize_error_message(exc_or_msg: object, fallback: str = "An unexpected internal error occurred.") -> str:
    """Redacts URIs, API keys, secrets, and overly verbose trace details from error messages."""
    text = str(exc_or_msg or "").strip()
    if not text:
        return fallback
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    if len(text) > 280:
        text = text[:277] + "..."
    return text
