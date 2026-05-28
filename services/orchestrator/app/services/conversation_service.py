from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.orchestrator_schemas import Conversation, ConversationMessage, ConversationSummary


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
) -> None:
    now = datetime.utcnow()
    messages = [
        ConversationMessage(role="user", content=user_query, timestamp=now).model_dump(),
        ConversationMessage(role="assistant", content=assistant_answer, timestamp=now).model_dump(),
    ]
    await db["conversations"].update_one(
        {"_id": conversation_id},
        {"$push": {"messages": {"$each": messages}}, "$set": {"updated_at": now}},
    )


def build_history(conversation: Conversation) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in conversation.messages[-10:]]


async def list_conversations(
    project_id: str | None,
    user_id: str | None,
    db: AsyncIOMotorDatabase,
    limit: int = 50,
) -> list[ConversationSummary]:
    query: dict = {}
    if project_id:
        query["project_id"] = project_id
    if user_id:
        query["user_id"] = user_id

    cursor = db["conversations"].find(query).sort("updated_at", -1).limit(limit)
    results = []
    async for doc in cursor:
        results.append(
            ConversationSummary(
                id=doc["_id"],
                project_id=doc["project_id"],
                title=doc.get("title"),
                rag_mode=doc.get("rag_mode", "vanilla"),
                message_count=len(doc.get("messages", [])),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
            )
        )
    return results


async def get_conversation(
    conversation_id: str,
    user_id: str | None,
    db: AsyncIOMotorDatabase,
) -> Conversation | None:
    query: dict = {"_id": conversation_id}
    if user_id:
        query["user_id"] = user_id
    doc = await db["conversations"].find_one(query)
    return Conversation(**doc) if doc else None


async def update_conversation_title(
    conversation_id: str,
    user_id: str | None,
    title: str | None,
    db: AsyncIOMotorDatabase,
) -> bool:
    query: dict = {"_id": conversation_id}
    if user_id:
        query["user_id"] = user_id
    result = await db["conversations"].update_one(
        query,
        {"$set": {"title": title, "updated_at": datetime.utcnow()}},
    )
    return result.matched_count > 0


async def delete_conversation(
    conversation_id: str,
    user_id: str | None,
    db: AsyncIOMotorDatabase,
) -> bool:
    query: dict = {"_id": conversation_id}
    if user_id:
        query["user_id"] = user_id
    result = await db["conversations"].delete_one(query)
    return result.deleted_count > 0
