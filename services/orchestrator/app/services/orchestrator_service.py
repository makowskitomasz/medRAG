import asyncio
import time
from collections.abc import AsyncGenerator

import httpx
from medrag_shared import get_logger
from medrag_shared.amqp import publish
from medrag_shared.models.project import RagMode
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.pipelines.factory import get_pipeline
from app.schemas.orchestrator_schemas import QueryRequest, QueryResponse
from app.services.conversation_service import (
    append_messages,
    build_history,
    get_or_create_conversation,
)
from app.services.project_service import get_project_settings

logger = get_logger(__name__)


async def handle_query(
    request: QueryRequest,
    db: AsyncIOMotorDatabase,
    http_client: httpx.AsyncClient,
    settings,  # type: ignore[type-arg]
    trace_id: str | None = None,
    user_id: str | None = None,
) -> QueryResponse:
    project_settings = await get_project_settings(request.project_id, db)
    rag_mode = (
        RagMode(request.rag_mode_override)
        if request.rag_mode_override
        else project_settings.rag_mode
    )

    conversation = await get_or_create_conversation(
        request.conversation_id, request.project_id, rag_mode.value, db, user_id=user_id
    )
    history = build_history(conversation)

    overrides = dict(project_settings.prompt_overrides)
    pipeline = get_pipeline(rag_mode, http_client, settings, overrides)
    pipeline.llm_model = project_settings.llm_model or None
    pipeline.max_hops = project_settings.max_hops

    t0 = time.monotonic()
    result = await pipeline.run(
        query=request.query,
        project_id=request.project_id,
        conversation_id=conversation.id,
        conversation_history=history,
        rag_mode=rag_mode.value,
        top_k=project_settings.top_k,
        alpha=project_settings.hybrid_alpha,
        rerank_top_n=project_settings.rerank_top_n,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    # Populate retrieved_filenames from all chunks passed to LLM (not just cited ones)
    result.retrieved_filenames = list(
        dict.fromkeys(c.get("filename", "") for c in pipeline._last_chunks if c.get("filename"))
    )

    await append_messages(
        conversation.id,
        request.query,
        result.answer,
        db,
        citations=[c.model_dump() for c in result.citations],
    )
    await _publish_query_completed(
        result,
        request,
        trace_id,
        latency_ms,
        project_settings.top_k,
        all_chunks=pipeline._last_chunks,
        input_tokens=pipeline._last_input_tokens,
        output_tokens=pipeline._last_output_tokens,
        llm_model=project_settings.llm_model or None,
    )
    return result


async def handle_query_stream(
    request: QueryRequest,
    db: AsyncIOMotorDatabase,
    http_client: httpx.AsyncClient,
    settings,  # type: ignore[type-arg]
    trace_id: str | None = None,
    user_id: str | None = None,
) -> AsyncGenerator[str, None]:
    project_settings = await get_project_settings(request.project_id, db)
    rag_mode = (
        RagMode(request.rag_mode_override)
        if request.rag_mode_override
        else project_settings.rag_mode
    )

    conversation = await get_or_create_conversation(
        request.conversation_id, request.project_id, rag_mode.value, db, user_id=user_id
    )
    history = build_history(conversation)

    overrides = dict(project_settings.prompt_overrides)
    pipeline = get_pipeline(rag_mode, http_client, settings, overrides)
    pipeline.llm_model = project_settings.llm_model or None
    pipeline.max_hops = project_settings.max_hops

    answer_parts: list[str] = []
    captured_citations: list[dict] = []

    async def _stream() -> AsyncGenerator[str, None]:
        import json

        stream = pipeline.run_stream(
            query=request.query,
            project_id=request.project_id,
            conversation_id=conversation.id,
            conversation_history=history,
            rag_mode=rag_mode.value,
            top_k=project_settings.top_k,
            alpha=project_settings.hybrid_alpha,
            rerank_top_n=project_settings.rerank_top_n,
        )
        if asyncio.iscoroutine(stream):
            stream = await stream
        async for chunk in stream:
            try:
                data = json.loads(chunk[6:].strip())
                if data.get("type") == "token":
                    answer_parts.append(data.get("content", data.get("text", "")))
                elif data.get("type") == "citations":
                    captured_citations.extend(data.get("citations", []))
            except Exception:
                pass
            yield chunk

        answer = "".join(answer_parts)
        await append_messages(
            conversation.id, request.query, answer, db, citations=captured_citations
        )

    return _stream()


async def _publish_query_completed(
    result: QueryResponse,
    request: QueryRequest,
    trace_id: str | None,
    latency_ms: int = 0,
    top_k: int = 20,
    all_chunks: list[dict] | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    llm_model: str | None = None,
) -> None:
    try:
        # Use ALL chunks passed to LLM for faithfulness (not just cited ones)
        contexts = [c.get("content", "") for c in (all_chunks or []) if c.get("content")]
        if not contexts:
            contexts = [c.snippet for c in result.citations]
        await publish(
            exchange_name="queries",
            routing_key="query.completed",
            payload={
                "conversation_id": result.conversation_id,
                "project_id": request.project_id,
                "query": request.query,
                "answer": result.answer,
                "rag_mode": result.rag_mode,
                "citations": [c.model_dump() for c in result.citations],
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "token_count": input_tokens + output_tokens,
                "contexts": contexts,
                "retrieved_filenames": result.retrieved_filenames,
                "top_k": top_k,
                "gold_answer": request.gold_answer,
                "gold_context_titles": request.gold_context_titles,
                "llm_model": llm_model,
            },
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.warning("failed to publish query.completed", error=str(exc))
