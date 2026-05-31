from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.orchestrator_schemas import Conversation, ConversationMessage


async def list_conversations(
    project_id: str,
    db: AsyncIOMotorDatabase,
    limit: int = 50,
) -> list[Conversation]:
    cursor = (
        db["conversations"].find({"project_id": project_id}).sort("updated_at", -1).limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [Conversation(**d) for d in docs]


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
) -> Conversation:
    if conversation_id:
        doc = await db["conversations"].find_one({"_id": conversation_id})
        if doc:
            return Conversation(**doc)

    conv = Conversation(project_id=project_id, rag_mode=rag_mode)
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
