import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.config.settings import settings
from app.dependencies import get_db, get_http_client
from app.schemas.orchestrator_schemas import (
    Conversation,
    ConversationMessage,
    QueryRequest,
    QueryResponse,
)
from app.services.conversation_service import (
    get_conversation_by_id,
    list_conversations,
)
from app.services.orchestrator_service import handle_query, handle_query_stream

router = APIRouter()


# ---- Query endpoints ----


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_trace_id: str | None = Header(default=None),
) -> QueryResponse:
    return await handle_query(request, db, http_client, settings, x_trace_id)


@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_trace_id: str | None = Header(default=None),
) -> StreamingResponse:
    gen = await handle_query_stream(request, db, http_client, settings, x_trace_id)
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---- Conversation history endpoints ----


class ConversationSummary(BaseModel):
    id: str
    project_id: str
    rag_mode: str
    message_count: int
    first_user_message: str | None
    created_at: str
    updated_at: str


class ConversationDetail(BaseModel):
    id: str
    project_id: str
    rag_mode: str
    messages: list[ConversationMessage]
    created_at: str
    updated_at: str


def _to_summary(conv: Conversation) -> ConversationSummary:
    first_msg = next((m.content for m in conv.messages if m.role == "user"), None)
    return ConversationSummary(
        id=conv.id,
        project_id=conv.project_id,
        rag_mode=conv.rag_mode,
        message_count=len(conv.messages),
        first_user_message=first_msg,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


def _to_detail(conv: Conversation) -> ConversationDetail:
    return ConversationDetail(
        id=conv.id,
        project_id=conv.project_id,
        rag_mode=conv.rag_mode,
        messages=conv.messages,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations_endpoint(
    project_id: str = Query(..., description="Filter by project ID"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[ConversationSummary]:
    convs = await list_conversations(project_id, db, limit)
    return [_to_summary(c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_endpoint(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConversationDetail:
    conv = await get_conversation_by_id(conversation_id, db)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _to_detail(conv)
