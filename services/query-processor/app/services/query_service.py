import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.services.llm_client import chat_complete
from app.services.prompt_loader import render

_MAX_RETRIES = 2
_AVAILABLE_MODES = [
    "vanilla",
    "hyde",
    "query_rewriting",
    "self_reflection",
    "multi_agent",
    "corrective_rag",
    "iterative_multihop",
    "madam_rag",
]


class _RewriteResult(BaseModel):
    rewritten_query: str = Field(description="The improved, medically specific query.")


class _DecomposeResult(BaseModel):
    sub_questions: list[str] = Field(
        description="List of self-contained sub-questions covering the original query.",
        min_length=1,
        max_length=4,
    )


class _TriageResult(BaseModel):
    complexity: str = Field(description="One of: simple, standard, complex, multi_hop.")
    conflict_risk: str = Field(description="One of: low, medium, high.")
    route: str = Field(description="RAG pipeline mode to use.")


async def rewrite_query(
    query: str,
    context: str,
    client: AsyncOpenAI,
    model: str,
    prompt_overrides: dict[str, str] | None = None,
) -> tuple[str, int, int]:
    """Returns (rewritten_query, input_tokens, output_tokens)."""
    system = (prompt_overrides or {}).get("rewrite_system") or render(
        "rewrite_system.j2", domain="drug interactions"
    )
    user_msg = f"Query: {query}"
    if context:
        user_msg += f"\n\nConversation context:\n{context}"
    return await chat_complete(client, model, system, user_msg)


async def generate_hypothetical_document(
    query: str,
    client: AsyncOpenAI,
    model: str,
    prompt_overrides: dict[str, str] | None = None,
) -> tuple[str, int, int]:
    """Returns (hypothetical_document, input_tokens, output_tokens)."""
    system = (prompt_overrides or {}).get("hyde_system") or render(
        "hyde_system.j2", domain="drug interactions and pharmacology"
    )
    return await chat_complete(client, model, system, query)


async def decompose_query(
    query: str,
    client: instructor.AsyncInstructor,
    model: str,
    max_sub_questions: int = 4,
    prompt_overrides: dict[str, str] | None = None,
) -> tuple[list[str], int, int]:
    """Returns (sub_questions, input_tokens, output_tokens)."""
    system = (prompt_overrides or {}).get("decompose_system") or render(
        "decompose_system.j2",
        max_sub_questions=max_sub_questions,
        domain="drug interactions and pharmacology",
    )
    result, completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Decompose this question: {query}"},
        ],
        response_model=_DecomposeResult,
        max_retries=_MAX_RETRIES,
    )
    usage = completion.usage
    return (
        result.sub_questions,
        usage.prompt_tokens if usage else 0,
        usage.completion_tokens if usage else 0,
    )


async def triage_query(
    query: str,
    client: instructor.AsyncInstructor,
    model: str,
    prompt_overrides: dict[str, str] | None = None,
) -> dict:
    """Returns triage dict with input_tokens and output_tokens."""
    system = (prompt_overrides or {}).get("triage_system") or render(
        "triage_system.j2", available_modes=_AVAILABLE_MODES
    )
    result, completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Classify and route this query: {query}"},
        ],
        response_model=_TriageResult,
        max_retries=_MAX_RETRIES,
    )
    usage = completion.usage
    return {
        "complexity": result.complexity,
        "conflict_risk": result.conflict_risk,
        "route": result.route,
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
    }
