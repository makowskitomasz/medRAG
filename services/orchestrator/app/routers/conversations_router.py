from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db
from app.schemas.orchestrator_schemas import (
    Conversation,
    ConversationSummary,
    UpdateConversationRequest,
)
from app.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
    update_conversation_title,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def get_conversations(
    project_id: str | None = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
) -> list[ConversationSummary]:
    return await list_conversations(project_id, x_user_id, db)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation_by_id(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
) -> Conversation:
    conv = await get_conversation(conversation_id, x_user_id, db)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: str,
    body: UpdateConversationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
) -> Conversation:
    ok = await update_conversation_title(conversation_id, x_user_id, body.title, db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv = await get_conversation(conversation_id, x_user_id, db)
    return conv  # type: ignore[return-value]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_conversation(
    conversation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_user_id: str | None = Header(default=None),
) -> None:
    ok = await delete_conversation(conversation_id, x_user_id, db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
