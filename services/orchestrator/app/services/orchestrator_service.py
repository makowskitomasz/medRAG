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
) -> QueryResponse:
    project_settings = await get_project_settings(request.project_id, db)
    rag_mode = project_settings.rag_mode

    conversation = await get_or_create_conversation(
        request.conversation_id, request.project_id, rag_mode.value, db
    )
    history = build_history(conversation)

    overrides = dict(project_settings.prompt_overrides)
    pipeline = get_pipeline(rag_mode, http_client, settings, overrides)
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

    await append_messages(conversation.id, request.query, result.answer, db)
    await _publish_query_completed(result, request, trace_id)
    return result


async def handle_query_stream(
    request: QueryRequest,
    db: AsyncIOMotorDatabase,
    http_client: httpx.AsyncClient,
    settings,  # type: ignore[type-arg]
    trace_id: str | None = None,
) -> AsyncGenerator[str, None]:
    project_settings = await get_project_settings(request.project_id, db)
    rag_mode = project_settings.rag_mode

    conversation = await get_or_create_conversation(
        request.conversation_id, request.project_id, rag_mode.value, db
    )
    history = build_history(conversation)

    overrides = dict(project_settings.prompt_overrides)
    pipeline = get_pipeline(rag_mode, http_client, settings, overrides)

    answer_parts: list[str] = []

    async def _stream() -> AsyncGenerator[str, None]:
        async for chunk in pipeline.run_stream(
            query=request.query,
            project_id=request.project_id,
            conversation_id=conversation.id,
            conversation_history=history,
            rag_mode=rag_mode.value,
            top_k=project_settings.top_k,
            alpha=project_settings.hybrid_alpha,
            rerank_top_n=project_settings.rerank_top_n,
        ):
            if '"type": "token"' in chunk:
                import json

                try:
                    data = json.loads(chunk[6:])
                    answer_parts.append(data.get("content", ""))
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
) -> None:
    try:
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
            },
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.warning("failed to publish query.completed", error=str(exc))
