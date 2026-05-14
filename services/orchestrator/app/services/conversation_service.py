from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.orchestrator_schemas import Conversation, ConversationMessage


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
