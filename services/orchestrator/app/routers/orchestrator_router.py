import math

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
    delete_conversation,
    get_conversation_by_id,
    list_conversations,
    rename_conversation,
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
    x_user_id: str | None = Header(default=None),
) -> QueryResponse:
    return await handle_query(request, db, http_client, settings, x_trace_id, user_id=x_user_id)


@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_trace_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> StreamingResponse:
    gen = await handle_query_stream(
        request, db, http_client, settings, x_trace_id, user_id=x_user_id
    )
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---- Conversation history endpoints ----


class ConversationSummary(BaseModel):
    id: str
    project_id: str
    user_id: str | None
    rag_mode: str
    title: str | None
    message_count: int
    first_user_message: str | None
    #: Start of the latest assistant reply — lets the history list show context
    #: without loading every message of every conversation.
    last_message_preview: str | None
    created_at: str
    updated_at: str


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    total: int
    page: int
    limit: int
    pages: int


class ConversationDetail(BaseModel):
    id: str
    project_id: str
    user_id: str | None
    rag_mode: str
    title: str | None
    messages: list[ConversationMessage]
    total_messages: int
    created_at: str
    updated_at: str


class RenameConversationRequest(BaseModel):
    title: str


_PREVIEW_CHARS = 160


def _to_summary(conv: Conversation) -> ConversationSummary:
    first_msg = next((m.content for m in conv.messages if m.role == "user"), None)
    last_reply = next(
        (m.content for m in reversed(conv.messages) if m.role != "user"),
        None,
    )
    if last_reply and len(last_reply) > _PREVIEW_CHARS:
        last_reply = last_reply[:_PREVIEW_CHARS].rstrip() + "…"
    return ConversationSummary(
        id=conv.id,
        project_id=conv.project_id,
        user_id=conv.user_id,
        rag_mode=conv.rag_mode,
        title=conv.title,
        message_count=len(conv.messages),
        first_user_message=first_msg,
        last_message_preview=last_reply,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


def _to_detail(conv: Conversation, messages: list[ConversationMessage]) -> ConversationDetail:
    return ConversationDetail(
        id=conv.id,
        project_id=conv.project_id,
        user_id=conv.user_id,
        rag_mode=conv.rag_mode,
        title=conv.title,
        messages=messages,
        total_messages=len(conv.messages),
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("/conversations", response_model=ConversationPage)
async def list_conversations_endpoint(
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    q: str | None = Query(default=None, description="Search titles and message bodies"),
    rag_mode: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_role: str = Header(default="user"),
) -> ConversationPage:
    convs, total = await list_conversations(
        project_id,
        db,
        limit,
        user_id=x_user_id,
        role=x_user_role,
        page=page,
        search=q,
        rag_mode=rag_mode,
    )
    return ConversationPage(
        items=[_to_summary(c) for c in convs],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, math.ceil(total / limit)),
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_endpoint(
    conversation_id: str,
    limit: int = Query(
        default=0,
        ge=0,
        le=500,
        description="Return only the newest N messages; 0 returns all.",
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConversationDetail:
    conv = await get_conversation_by_id(conversation_id, db)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = conv.messages[-limit:] if limit else conv.messages
    return _to_detail(conv, messages)


@router.patch("/conversations/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation_endpoint(
    conversation_id: str,
    body: RenameConversationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_role: str = Header(default="user"),
) -> ConversationSummary:
    conv = await get_conversation_by_id(conversation_id, db)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    _assert_may_modify(conv, x_user_id, x_user_role)
    title = body.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title must not be empty"
        )
    updated = await rename_conversation(conversation_id, title[:200], db)
    assert updated is not None
    return _to_summary(updated)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_endpoint(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_role: str = Header(default="user"),
) -> None:
    conv = await get_conversation_by_id(conversation_id, db)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    _assert_may_modify(conv, x_user_id, x_user_role)
    await delete_conversation(conversation_id, db)


def _assert_may_modify(conv: Conversation, user_id: str | None, role: str) -> None:
    """Owners and admins may rename or delete; everyone else gets 403."""
    if role == "admin" or (conv.user_id and conv.user_id == user_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation")
