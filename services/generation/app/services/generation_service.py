import json
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.schemas.generation_schemas import (
    ConflictDetectionRequest,
    ConflictDetectionResult,
    EvaluationRequest,
    EvaluationResult,
    GenerationRequest,
    GenerationResult,
)
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


_EVAL_SYSTEM = (
    "You are an evaluator. Given a query, an answer, and the source context chunks, "
    "score how well the answer addresses the query using only information from the context. "
    'Reply with JSON only: {"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}. '
    "1.0 = fully answered with context support. 0.0 = not answered or hallucinated."
)


async def evaluate_answer(
    request: EvaluationRequest,
    client: AsyncOpenAI,
    model: str,
) -> EvaluationResult:
    import re

    context = "\n\n".join(f"[SOURCE_{i + 1}] {c.content}" for i, c in enumerate(request.chunks))
    messages = [
        {"role": "system", "content": _EVAL_SYSTEM},
        {
            "role": "user",
            "content": f"Query: {request.query}\n\nAnswer: {request.answer}\n\nContext:\n{context}",
        },
    ]
    response = await client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=200,
        temperature=0.0,
    )
    raw = response.choices[0].message.content or '{"score": 1.0, "reasoning": ""}'
    # Strip markdown code fences if present.
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        import json

        data = json.loads(raw)
        return EvaluationResult(score=float(data["score"]), reasoning=data.get("reasoning", ""))
    except Exception:
        return EvaluationResult(score=1.0, reasoning="parse error — defaulting to sufficient")


_CONFLICT_SYSTEM = (
    "You are a medical evidence analyst. Review the provided source chunks and determine if they "
    "contain conflicting medical information about the same topic. "
    "Look for contradictions in dosing, contraindications, efficacy, or safety recommendations. "
    "Reply with JSON only: "
    '{"has_conflict": <bool>, "confidence": <float 0.0-1.0>, "reasoning": "<one sentence>"}.'
)


async def detect_conflict(
    request: ConflictDetectionRequest,
    client: AsyncOpenAI,
    model: str,
) -> ConflictDetectionResult:
    import re

    context = "\n\n".join(f"[SOURCE_{i + 1}] {c.content}" for i, c in enumerate(request.chunks))
    messages = [
        {"role": "system", "content": _CONFLICT_SYSTEM},
        {"role": "user", "content": f"Evaluate these medical sources for conflicts:\n\n{context}"},
    ]
    response = await client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=200,
        temperature=0.0,
    )
    _default = '{"has_conflict": false, "confidence": 0.5, "reasoning": ""}'
    raw = response.choices[0].message.content or _default
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(raw)
        return ConflictDetectionResult(
            has_conflict=bool(data.get("has_conflict", False)),
            confidence=float(data.get("confidence", 0.5)),
            reasoning=data.get("reasoning", ""),
        )
    except Exception:
        return ConflictDetectionResult(has_conflict=False, confidence=0.5, reasoning="parse error")
