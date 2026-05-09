from typing import Any

from medrag_shared import get_logger
from medrag_shared.amqp import publish
from medrag_shared.logging import bind_trace_id
from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db

from app.providers.base import BaseEmbeddingProvider

logger = get_logger(__name__)


async def handle_document_chunked(
    payload: dict[str, Any],
    trace_id: str | None,
    provider: BaseEmbeddingProvider,
    batch_size: int = 32,
) -> None:
    document_id: str = payload["document_id"]
    project_id: str = payload["project_id"]
    chunk_ids: list[str] = payload.get("chunk_ids", [])

    if trace_id:
        bind_trace_id(trace_id)

    logger.info("embedding chunks", document_id=document_id, count=len(chunk_ids))
    db = get_db()

    chunks = await db.chunks.find({"_id": {"$in": chunk_ids}}).to_list(len(chunk_ids))
    if not chunks:
        logger.warning("no chunks found", document_id=document_id)
        return

    # batch embed
    embedded: list[dict[str, Any]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        vectors = provider.embed(texts)
        for chunk, vector in zip(batch, vectors, strict=True):
            embedded.append({"chunk_id": chunk["_id"], "vector": vector})

    entry = StatusHistoryEntry(status=DocumentStatus.EMBEDDED, trace_id=trace_id)
    await db.documents.update_one(
        {"_id": document_id},
        {
            "$set": {"status": DocumentStatus.EMBEDDED},
            "$push": {"status_history": entry.model_dump()},
        },
    )

    await publish(
        exchange_name="documents",
        routing_key="chunks.embedded",
        payload={"document_id": document_id, "project_id": project_id, "embeddings": embedded},
        trace_id=trace_id,
    )
    logger.info("chunks embedded", document_id=document_id, count=len(embedded))
