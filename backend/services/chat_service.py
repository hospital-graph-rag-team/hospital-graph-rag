"""Service layer for executing Clinical Graph RAG queries via src/rag/engine.py."""

import asyncio
from typing import Any, Dict, List, Optional

from backend.config import get_settings
from backend.schemas.models import (
    ChatRequest,
    ChatResponse,
    CitationValidationResult,
    RetrievedEvidenceItem,
    ToolCallItem,
)
from backend.security import sanitize_error_message, validate_optional_patient_id
from src.rag.engine import MODEL_NAME, run_clinical_query_detailed


async def execute_chat_query(request_body: ChatRequest) -> ChatResponse:
    """
    Validates inputs, isolates conversation history, and executes the ReAct Graph RAG engine
    inside a bounded worker thread so FastAPI remains non-blocking.
    """
    settings = get_settings()
    cleaned_query = request_body.query.strip()
    if len(cleaned_query) > settings.max_chat_query_length:
        cleaned_query = cleaned_query[: settings.max_chat_query_length]

    patient_id = validate_optional_patient_id(request_body.selected_patient_id)
    bounded_history: List[Dict[str, Any]] = [
        {"role": msg.role, "content": msg.content.strip()}
        for msg in request_body.conversation_history[-settings.max_history_messages :]
        if msg.content.strip()
    ]

    try:
        raw_result = await asyncio.wait_for(
            asyncio.to_thread(
                run_clinical_query_detailed,
                user_prompt=cleaned_query,
                conversation_history=bounded_history,
                selected_patient_id=patient_id,
            ),
            timeout=settings.chat_timeout_seconds,
        )
    except asyncio.TimeoutError:
        return ChatResponse(
            query=cleaned_query,
            patient_id=patient_id,
            status="error",
            answer="The AI assistant timed out while querying the knowledge graph or LLM provider. Please try a narrower question.",
            citations=[],
            citation_validation=CitationValidationResult(supported=[], unsupported=[], is_valid=True),
            tool_calls=[],
            retrieved_evidence=[],
            error="Request timed out",
            model_name=MODEL_NAME,
        )
    except Exception as exc:
        safe_err = sanitize_error_message(exc, fallback="Failed to process clinical query.")
        return ChatResponse(
            query=cleaned_query,
            patient_id=patient_id,
            status="error",
            answer="Unable to complete the clinical query due to an internal provider or database error.",
            citations=[],
            citation_validation=CitationValidationResult(supported=[], unsupported=[], is_valid=True),
            tool_calls=[],
            retrieved_evidence=[],
            error=safe_err,
            model_name=MODEL_NAME,
        )

    raw_error = raw_result.get("error")
    safe_error = sanitize_error_message(raw_error) if raw_error else None
    raw_answer = raw_result.get("answer") or ""
    if raw_result.get("status") == "error" and raw_error:
        raw_answer = sanitize_error_message(raw_answer, fallback="Unable to complete the clinical query.")

    val = raw_result.get("citation_validation") or {}
    return ChatResponse(
        query=cleaned_query,
        patient_id=patient_id,
        status=raw_result.get("status", "success"),
        answer=raw_answer,
        citations=raw_result.get("citations") or [],
        citation_validation=CitationValidationResult(
            supported=val.get("supported") or [],
            unsupported=val.get("unsupported") or [],
            is_valid=bool(val.get("is_valid", True)),
        ),
        tool_calls=[
            ToolCallItem(
                tool=tc.get("tool", "unknown"),
                arguments=tc.get("arguments") or {},
                summary=tc.get("summary", ""),
            )
            for tc in (raw_result.get("tool_calls") or [])
        ],
        retrieved_evidence=[
            RetrievedEvidenceItem(
                tool=ev.get("tool", "unknown"),
                data=ev.get("data"),
            )
            for ev in (raw_result.get("retrieved_evidence") or [])
        ],
        error=safe_error,
        model_name=MODEL_NAME,
    )
