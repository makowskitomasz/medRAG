import asyncio
import json
import time
from collections.abc import AsyncGenerator

import httpx
from medrag_shared import get_logger
from medrag_shared.amqp import publish
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
    rag_mode = project_settings.rag_mode

    conversation = await get_or_create_conversation(
        request.conversation_id, request.project_id, rag_mode.value, db, user_id
    )
    history = build_history(conversation)

    overrides = dict(project_settings.prompt_overrides)
    pipeline = get_pipeline(rag_mode, http_client, settings, overrides)

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

    await append_messages(conversation.id, request.query, result.answer, db)
    await _publish_query_completed(result, request, trace_id, latency_ms, project_settings.top_k)
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
    rag_mode = project_settings.rag_mode

    conversation = await get_or_create_conversation(
        request.conversation_id, request.project_id, rag_mode.value, db, user_id
    )
    history = build_history(conversation)

    overrides = dict(project_settings.prompt_overrides)
    pipeline = get_pipeline(rag_mode, http_client, settings, overrides)

    answer_parts: list[str] = []

    async def _stream() -> AsyncGenerator[str, None]:
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
        current_event: str | None = None
        async for chunk in stream:
            # Track current event type across the multi-line SSE frame
            for line in chunk.splitlines():
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: ") and current_event == "token":
                    try:
                        data = json.loads(line[6:])
                        answer_parts.append(data.get("text", ""))
                    except Exception:
                        pass
            yield chunk

        answer = "".join(answer_parts)
        await append_messages(conversation.id, request.query, answer, db)

    return _stream()


async def _publish_query_completed(
    result: QueryResponse,
    request: QueryRequest,
    trace_id: str | None,
    latency_ms: int = 0,
    top_k: int = 20,
) -> None:
    try:
        contexts = [c.snippet for c in result.citations]
        token_count = len(result.answer.split())
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
                "token_count": token_count,
                "contexts": contexts,
                "top_k": top_k,
                "gold_answer": request.gold_answer,
            },
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.warning("failed to publish query.completed", error=str(exc))
