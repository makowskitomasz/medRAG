import json
from collections.abc import AsyncGenerator

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.schemas.generation_schemas import (
    ClaimVerdict,
    ConflictDetectionRequest,
    ConflictDetectionResult,
    ContextChunk,
    CorrectnessRequest,
    CorrectnessResult,
    EvaluationRequest,
    EvaluationResult,
    ExtractRequest,
    ExtractResult,
    GenerationRequest,
    GenerationResult,
    VerifyClaimsRequest,
    VerifyClaimsResult,
)
from app.services.citation_extractor import extract_citations
from app.services.prompt_builder import build_messages
from app.services.prompt_loader import render

_MAX_RETRIES = 2
_MAX_CLAIMS = 10

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


def _messages_for(request: GenerationRequest) -> list[dict]:
    return build_messages(
        request.query,
        request.chunks,
        request.conversation_history,
        request.prompt_overrides,
        evidence_notes=request.evidence_notes,
        task_instructions=request.task_instructions,
    )


async def generate(
    request: GenerationRequest,
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
) -> GenerationResult:
    messages = _messages_for(request)
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
    messages = _messages_for(request)
    full_answer: list[str] = []

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        # Without this the streamed response carries no usage at all, so every
        # streamed answer was recorded with a token count of zero.
        stream_options={"include_usage": True},
    )

    reasoning_parts: list[str] = []
    reasoning_emitted = 0
    input_tokens = 0
    output_tokens = 0

    async for chunk in stream:  # type: ignore[assignment]
        # The usage-bearing chunk arrives last and has no choices, so read it
        # before the guard below skips the chunk.
        usage = getattr(chunk, "usage", None)
        if usage:
            input_tokens = usage.prompt_tokens or 0
            output_tokens = usage.completion_tokens or 0
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Reasoning models (e.g. gpt-oss) stream a long chain-of-thought in
        # `delta.reasoning` before any answer content. Surface it as `think`
        # events so the UI shows live progress instead of a frozen spinner.
        reasoning = getattr(delta, "reasoning", None)
        if reasoning:
            reasoning_parts.append(reasoning)
            reasoning_emitted += 1
            # Emit the first update immediately (fast switch to "thinking"),
            # then throttle to a cumulative update every few deltas.
            if reasoning_emitted == 1 or reasoning_emitted % 8 == 0:
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "think",
                            "step": 0,
                            "label": "Reasoning",
                            "text": "".join(reasoning_parts),
                        }
                    )
                    + "\n\n"
                )

        content = delta.content
        if content:
            full_answer.append(content)
            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

    answer = "".join(full_answer)
    citations = extract_citations(answer, request.chunks)
    citations_payload = [c.model_dump() for c in citations]
    yield (
        "data: "
        + json.dumps(
            {
                "type": "citations",
                "citations": citations_payload,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )
        + "\n\n"
    )
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


async def extract_finding(
    request: ExtractRequest,
    client: instructor.AsyncInstructor,
    model: str,
) -> ExtractResult:
    """One hop of a sequential retrieval chain: summarise evidence, refine the next hop."""
    has_next = bool(request.next_question_draft)
    system = render(
        "extract_system.j2",
        override=request.prompt_overrides.get("extract_system"),
        has_next=has_next,
    )
    parts = [f"Overall question: {request.query}", f"Current sub-question: {request.sub_question}"]
    if request.prior_findings:
        established = "\n".join(f"- {f}" for f in request.prior_findings)
        parts.append(f"Findings established so far:\n{established}")
    if has_next:
        parts.append(f"Draft of the next sub-question: {request.next_question_draft}")
    parts.append(f"Retrieved passages:\n{_format_context(request.chunks)}")

    result, completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(parts)},
        ],
        response_model=ExtractResult,
        max_retries=_MAX_RETRIES,
    )
    if not has_next:
        result.next_question = ""
    usage = completion.usage
    result.input_tokens = usage.prompt_tokens if usage else 0
    result.output_tokens = usage.completion_tokens if usage else 0
    return result


class _ClaimList(BaseModel):
    claims: list[str] = Field(description="Atomic, self-contained factual claims.")

    model_config = {"json_schema_extra": {"required": ["claims"]}}


class _ClaimVerdicts(BaseModel):
    verdicts: list[ClaimVerdict] = Field(description="One verdict per claim, in the given order.")

    model_config = {"json_schema_extra": {"required": ["verdicts"]}}


async def verify_claims(
    request: VerifyClaimsRequest,
    client: instructor.AsyncInstructor,
    model: str,
) -> VerifyClaimsResult:
    """Claim-level grounding check: extract atomic claims, then verify each against context."""
    extract_system = render(
        "claim_extract_system.j2",
        override=request.prompt_overrides.get("claim_extract_system"),
        max_claims=_MAX_CLAIMS,
    )
    claim_list, claim_completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": extract_system},
            {"role": "user", "content": f"Answer:\n{request.answer}"},
        ],
        response_model=_ClaimList,
        max_retries=_MAX_RETRIES,
    )
    usage = claim_completion.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0

    claims = [c.strip() for c in claim_list.claims[:_MAX_CLAIMS] if c.strip()]
    if not claims:
        # No factual content to audit (e.g. an explicit "I don't know"): treat as grounded.
        return VerifyClaimsResult(
            claims=[],
            grounding_score=1.0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    verify_system = render(
        "claim_verify_system.j2",
        override=request.prompt_overrides.get("claim_verify_system"),
    )
    numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, start=1))
    verdicts_result, verify_completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": verify_system},
            {
                "role": "user",
                "content": (f"Passages:\n{_format_context(request.chunks)}\n\nClaims:\n{numbered}"),
            },
        ],
        response_model=_ClaimVerdicts,
        max_retries=_MAX_RETRIES,
    )
    usage = verify_completion.usage
    input_tokens += usage.prompt_tokens if usage else 0
    output_tokens += usage.completion_tokens if usage else 0

    # The model may return fewer verdicts than claims; unmatched claims count as unsupported.
    verdicts = verdicts_result.verdicts[: len(claims)]
    supported = sum(1 for v in verdicts if v.supported)
    return VerifyClaimsResult(
        claims=verdicts,
        grounding_score=supported / len(claims),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


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
