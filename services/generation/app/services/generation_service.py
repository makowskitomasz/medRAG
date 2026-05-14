import json
from collections.abc import AsyncGenerator

import instructor
from openai import AsyncOpenAI

from app.schemas.generation_schemas import (
    ConflictDetectionRequest,
    ConflictDetectionResult,
    ContextChunk,
    EvaluationRequest,
    EvaluationResult,
    GenerationRequest,
    GenerationResult,
)
from app.services.citation_extractor import extract_citations
from app.services.prompt_builder import build_messages
from app.services.prompt_loader import render

_MAX_RETRIES = 2

_raw_client: AsyncOpenAI | None = None
_instructor_client: instructor.AsyncInstructor | None = None


def get_llm_client(base_url: str, api_key: str) -> AsyncOpenAI:
    global _raw_client
    if _raw_client is None:
        _raw_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _raw_client


def get_instructor_client(base_url: str, api_key: str) -> instructor.AsyncInstructor:
    global _instructor_client
    if _instructor_client is None:
        raw = get_llm_client(base_url, api_key)
        _instructor_client = instructor.from_openai(raw, mode=instructor.Mode.JSON)
    return _instructor_client


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

    async for chunk in stream:  # type: ignore[assignment]
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            full_answer.append(delta)
            yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

    answer = "".join(full_answer)
    citations = extract_citations(answer, request.chunks)
    citations_payload = [c.model_dump() for c in citations]
    yield f"data: {json.dumps({'type': 'citations', 'citations': citations_payload})}\n\n"
    yield "data: [DONE]\n\n"


def _format_context(chunks: list[ContextChunk]) -> str:
    return "\n\n".join(f"[SOURCE_{i + 1}] {c.content}" for i, c in enumerate(chunks))


async def evaluate_answer(
    request: EvaluationRequest,
    client: instructor.AsyncInstructor,
    model: str,
) -> EvaluationResult:
    system = render("evaluate_system.j2", strict_mode=False)
    context = _format_context(request.chunks)
    return await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Query: {request.query}\n\nAnswer: {request.answer}\n\nContext:\n{context}"
                ),
            },
        ],
        response_model=EvaluationResult,
        max_retries=_MAX_RETRIES,
    )


async def detect_conflict(
    request: ConflictDetectionRequest,
    client: instructor.AsyncInstructor,
    model: str,
) -> ConflictDetectionResult:
    system = render("detect_conflict_system.j2", topic_hint=None)
    context = _format_context(request.chunks)
    return await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Evaluate these medical sources for conflicts:\n\n{context}",
            },
        ],
        response_model=ConflictDetectionResult,
        max_retries=_MAX_RETRIES,
    )
