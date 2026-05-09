from typing import Any

from medrag_shared import get_logger
from medrag_shared.amqp import publish

from app.connectors.providers.base import BaseEmbeddingProvider
from app.repositories import chunk_repository, document_repository

logger = get_logger(__name__)


async def embed(
    document_id: str,
    project_id: str,
    chunk_ids: list[str],
    trace_id: str | None,
    provider: BaseEmbeddingProvider,
    batch_size: int = 32,
) -> None:
    logger.info("embedding chunks", document_id=document_id, count=len(chunk_ids))

    chunks = await chunk_repository.find_by_ids(chunk_ids)
    if not chunks:
        logger.warning("no chunks found", document_id=document_id)
        return

    embedded: list[dict[str, Any]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        vectors = provider.embed(texts)
        for chunk, vector in zip(batch, vectors, strict=True):
            embedded.append({"chunk_id": chunk["_id"], "vector": vector})

    await document_repository.update_embedded(document_id, trace_id)

    await publish(
        exchange_name="documents",
        routing_key="chunks.embedded",
        payload={"document_id": document_id, "project_id": project_id, "embeddings": embedded},
        trace_id=trace_id,
    )
    logger.info("chunks embedded", document_id=document_id, count=len(embedded))
