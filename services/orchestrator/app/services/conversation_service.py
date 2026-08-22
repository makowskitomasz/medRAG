import re
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.orchestrator_schemas import Conversation, ConversationMessage


async def ensure_conversation_indexes() -> None:
    """Back the paginated history queries, which sort by `updated_at` on every call."""
    from app.connectors import get_db_instance

    conversations = get_db_instance()["conversations"]
    await conversations.create_index([("project_id", 1), ("updated_at", -1)])
    await conversations.create_index([("user_id", 1), ("updated_at", -1)])


def _visibility_query(
    project_id: str | None,
    user_id: str | None,
    role: str,
) -> dict:
    query: dict = {}
    if project_id:
        query["project_id"] = project_id
    if role != "admin" and user_id:
        query["user_id"] = user_id
    return query


async def list_conversations(
    project_id: str | None,
    db: AsyncIOMotorDatabase,
    limit: int = 50,
    user_id: str | None = None,
    role: str = "user",
    page: int = 1,
    search: str | None = None,
    rag_mode: str | None = None,
) -> tuple[list[Conversation], int]:
    """Return one page of conversations, newest first, plus the total match count.

    `project_id` is optional so the history view can page across every project the
    caller may see instead of fetching each project in full and filtering client-side.
    """
    query = _visibility_query(project_id, user_id, role)
    if rag_mode:
        query["rag_mode"] = rag_mode
    if search:
        # Matches the stored title and any message body, so history search is not
        # limited to the first question of a conversation.
        escaped = re.escape(search)
        query["$or"] = [
            {"title": {"$regex": escaped, "$options": "i"}},
            {"messages.content": {"$regex": escaped, "$options": "i"}},
        ]

    total = await db["conversations"].count_documents(query)
    skip = max(0, (page - 1) * limit)
    cursor = db["conversations"].find(query).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [Conversation(**d) for d in docs], total


async def rename_conversation(
    conversation_id: str,
    title: str,
    db: AsyncIOMotorDatabase,
) -> Conversation | None:
    await db["conversations"].update_one(
        {"_id": conversation_id},
        {"$set": {"title": title, "updated_at": datetime.utcnow()}},
    )
    return await get_conversation_by_id(conversation_id, db)


async def delete_conversation(conversation_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db["conversations"].delete_one({"_id": conversation_id})
    return result.deleted_count > 0


async def get_conversation_by_id(
    conversation_id: str,
    db: AsyncIOMotorDatabase,
) -> Conversation | None:
    doc = await db["conversations"].find_one({"_id": conversation_id})
    return Conversation(**doc) if doc else None


async def get_or_create_conversation(
    conversation_id: str | None,
    project_id: str,
    rag_mode: str,
    db: AsyncIOMotorDatabase,
    user_id: str | None = None,
) -> Conversation:
    if conversation_id:
        doc = await db["conversations"].find_one({"_id": conversation_id})
        if doc:
            return Conversation(**doc)

    conv = Conversation(project_id=project_id, rag_mode=rag_mode, user_id=user_id)
    await db["conversations"].insert_one(conv.model_dump(by_alias=True))
    return conv


async def append_messages(
    conversation_id: str,
    user_query: str,
    assistant_answer: str,
    db: AsyncIOMotorDatabase,
    citations: list | None = None,
) -> None:
    from app.schemas.orchestrator_schemas import Citation as CitationSchema

    now = datetime.utcnow()
    parsed_citations = [
        CitationSchema(**c) if isinstance(c, dict) else c for c in (citations or [])
    ]
    messages = [
        ConversationMessage(role="user", content=user_query, timestamp=now).model_dump(),
        ConversationMessage(
            role="assistant", content=assistant_answer, citations=parsed_citations, timestamp=now
        ).model_dump(),
    ]
    await db["conversations"].update_one(
        {"_id": conversation_id},
        {"$push": {"messages": {"$each": messages}}, "$set": {"updated_at": now}},
    )


def build_history(conversation: Conversation) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in conversation.messages[-10:]]
