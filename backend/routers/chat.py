"""AI Assistant ReAct Graph RAG chat endpoint."""

from fastapi import APIRouter, Depends

from backend.schemas.models import ChatRequest, ChatResponse
from backend.security import enforce_chat_rate_limit, verify_backend_token
from backend.services.chat_service import execute_chat_query

router = APIRouter(
    prefix="/api/v1",
    tags=["AI Assistant"],
    dependencies=[Depends(verify_backend_token), Depends(enforce_chat_rate_limit)],
)


@router.post("/chat", response_model=ChatResponse, summary="Run a Clinical Graph RAG query")
async def run_chat(request_body: ChatRequest) -> ChatResponse:
    return await execute_chat_query(request_body)
