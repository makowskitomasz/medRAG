import json
from collections.abc import AsyncGenerator

import instructor
from openai import AsyncOpenAI

from app.schemas.generation_schemas import (
    ConflictDetectionRequest,
    ConflictDetectionResult,
    ContextChunk,
    CorrectnessRequest,
    CorrectnessResult,
    EvaluationRequest,
    EvaluationResult,
    GenerationRequest,
    GenerationResult,
)
from app.services.citation_extractor import extract_citations
from app.services.prompt_builder import build_messages
from app.services.prompt_loader import render

_MAX_RETRIES = 2

_STRUCTURED_OUTPUTS_MODELS = {"openai/gpt-oss-120b"}

_raw_client: AsyncOpenAI | None = None
_instructor_clients: dict[instructor.Mode, instructor.AsyncInstructor] = {}


def get_llm_client(base_url: str, api_key: str) -> AsyncOpenAI:
    global _raw_client
    if _raw_client is None:
        _raw_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _raw_client


def get_instructor_client(
    base_url: str, api_key: str, model: str = ""
) -> instructor.AsyncInstructor:
    mode = (
        instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
        if model in _STRUCTURED_OUTPUTS_MODELS
        else instructor.Mode.JSON
    )
    if mode not in _instructor_clients:
        raw = get_llm_client(base_url, api_key)
        _instructor_clients[mode] = instructor.from_openai(raw, mode=mode)
    return _instructor_clients[mode]


async def generate(
    request: GenerationRequest,
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
) -> GenerationResult:
    messages = build_messages(
        request.query, request.chunks, request.conversation_history, request.prompt_overrides
    )
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    answer = response.choices[0].message.content or ""
    citations = extract_citations(answer, request.chunks)
    usage = response.usage
    return GenerationResult(
        answer=answer,
        citations=citations,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


async def generate_stream(
    request: GenerationRequest,
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
) -> AsyncGenerator[str, None]:
    """Yields SSE-formatted strings. Final event contains citations JSON."""
    messages = build_messages(
        request.query, request.chunks, request.conversation_history, request.prompt_overrides
    )
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
    system = render(
        "evaluate_system.j2",
        override=request.prompt_overrides.get("evaluate_system"),
        strict_mode=False,
    )
    context = _format_context(request.chunks)
    result, completion = await client.chat.completions.create_with_completion(
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
    usage = completion.usage
    result.input_tokens = usage.prompt_tokens if usage else 0
    result.output_tokens = usage.completion_tokens if usage else 0
    return result


async def detect_conflict(
    request: ConflictDetectionRequest,
    client: instructor.AsyncInstructor,
    model: str,
) -> ConflictDetectionResult:
    system = render(
        "detect_conflict_system.j2",
        override=request.prompt_overrides.get("detect_conflict_system"),
        topic_hint=None,
    )
    context = _format_context(request.chunks)
    result, completion = await client.chat.completions.create_with_completion(
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
    usage = completion.usage
    result.input_tokens = usage.prompt_tokens if usage else 0
    result.output_tokens = usage.completion_tokens if usage else 0
    return result


async def assess_correctness(
    request: CorrectnessRequest,
    client: instructor.AsyncInstructor,
    model: str,
) -> CorrectnessResult:
    system = render("correctness_system.j2")
    result, completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Question: {request.query}\n\n"
                    f"Gold answer: {request.gold_answer}\n\n"
                    f"Generated answer: {request.answer}"
                ),
            },
        ],
        response_model=CorrectnessResult,
        max_retries=_MAX_RETRIES,
    )
    usage = completion.usage
    result.input_tokens = usage.prompt_tokens if usage else 0
    result.output_tokens = usage.completion_tokens if usage else 0
    return result
