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


_DECOMPOSE_SYSTEM = (
    "You are a medical research assistant. Break down the complex medical question into "
    "2-4 simpler sub-questions that together cover the original question. "
    'Return JSON only: {"sub_questions": ["...", "..."]}. '
    "Each sub-question should be self-contained and answerable independently."
)

_TRIAGE_SYSTEM = (
    "You are a medical query classifier. Classify the query and return routing decision. "
    "complexity: 'simple' (single fact), 'standard' (one topic), 'complex' (multi-factor), "
    "'multi_hop' (requires chaining evidence). "
    "conflict_risk: 'low' (clear consensus), 'medium' (some variation), "
    "'high' (known contradictions). "
    "route: one of vanilla|hyde|query_rewriting|self_reflection|multi_agent|corrective_rag|"
    "iterative_multihop|madam_rag. "
    'Return JSON only: {"complexity": "...", "conflict_risk": "...", "route": "..."}'
)


async def decompose_query(query: str, client: AsyncOpenAI, model: str) -> list[str]:
    import json
    import re

    raw = await chat_complete(client, model, _DECOMPOSE_SYSTEM, query)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(raw)
        return [str(q) for q in data.get("sub_questions", [query])]
    except Exception:
        return [query]


async def triage_query(query: str, client: AsyncOpenAI, model: str) -> dict:
    import json
    import re

    raw = await chat_complete(client, model, _TRIAGE_SYSTEM, query)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except Exception:
        return {"complexity": "standard", "conflict_risk": "low", "route": "vanilla"}
