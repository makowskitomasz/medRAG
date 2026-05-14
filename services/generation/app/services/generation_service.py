import json
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.schemas.generation_schemas import GenerationRequest, GenerationResult
from app.services.citation_extractor import extract_citations
from app.services.prompt_builder import build_messages

_client: AsyncOpenAI | None = None


def get_llm_client(base_url: str, api_key: str) -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _client


async def generate(
    request: GenerationRequest,
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
) -> GenerationResult:
    messages = build_messages(request.query, request.chunks, request.conversation_history)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    answer = response.choices[0].message.content or ""
    citations = extract_citations(answer, request.chunks)
    return GenerationResult(answer=answer, citations=citations)


async def generate_stream(
    request: GenerationRequest,
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
) -> AsyncGenerator[str, None]:
    """Yields SSE-formatted strings. Final event contains citations JSON."""
    messages = build_messages(request.query, request.chunks, request.conversation_history)
    full_answer: list[str] = []

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            full_answer.append(delta)
            yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

    answer = "".join(full_answer)
    citations = extract_citations(answer, request.chunks)
    citations_payload = [c.model_dump() for c in citations]
    yield f"data: {json.dumps({'type': 'citations', 'citations': citations_payload})}\n\n"
    yield "data: [DONE]\n\n"
