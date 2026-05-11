from openai import AsyncOpenAI

from app.services.llm_client import chat_complete

_REWRITE_SYSTEM = (
    "You are a medical query optimization assistant. "
    "Rewrite the user's query to improve retrieval from a medical knowledge base. "
    "Make it more specific and use medical terminology where appropriate. "
    "Return only the rewritten query, nothing else."
)

_HYDE_SYSTEM = (
    "You are a medical expert. Generate a concise hypothetical document passage (2-3 sentences) "
    "that would answer the following question. This passage will be used for semantic retrieval. "
    "Return only the passage, nothing else."
)


async def rewrite_query(query: str, context: str, client: AsyncOpenAI, model: str) -> str:
    user_msg = f"Query: {query}"
    if context:
        user_msg += f"\n\nConversation context:\n{context}"
    return await chat_complete(client, model, _REWRITE_SYSTEM, user_msg)


async def generate_hypothetical_document(query: str, client: AsyncOpenAI, model: str) -> str:
    return await chat_complete(client, model, _HYDE_SYSTEM, query)
