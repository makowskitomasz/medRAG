from typing import Any

from medrag_shared import get_logger
from medrag_shared.amqp import publish
from medrag_shared.logging import bind_trace_id
from medrag_shared.models.document import Chunk, DocumentStatus, StatusHistoryEntry
from medrag_shared.models.project import ChunkingStrategy
from medrag_shared.mongo import get_db

from app.strategies.fixed import FixedChunker
from app.strategies.recursive import RecursiveChunker

logger = get_logger(__name__)


def _get_chunker(strategy: str) -> Any:
    if strategy == ChunkingStrategy.FIXED_512:
        return FixedChunker(chunk_size=512, overlap=50)
    return RecursiveChunker(chunk_size=512, overlap=50)


async def handle_document_parsed(payload: dict[str, Any], trace_id: str | None) -> None:
    document_id: str = payload["document_id"]
    project_id: str = payload["project_id"]

    if trace_id:
        bind_trace_id(trace_id)

    logger.info("chunking document", document_id=document_id)
    db = get_db()

    doc = await db.documents.find_one({"_id": document_id})
    if not doc or not doc.get("extracted_text"):
        logger.error("document or text not found", document_id=document_id)
        return

    project = await db.projects.find_one({"_id": project_id})
    strategy = (
        project.get("settings", {}).get("chunking_strategy", ChunkingStrategy.RECURSIVE)
        if project
        else ChunkingStrategy.RECURSIVE
    )

    chunker = _get_chunker(strategy)
    texts = chunker.split(doc["extracted_text"])

    chunks = [
        Chunk(
            document_id=document_id,
            project_id=project_id,
            chunk_index=i,
            content=text,
        )
        for i, text in enumerate(texts)
    ]

    if chunks:
        await db.chunks.insert_many([c.model_dump(by_alias=True) for c in chunks])

    entry = StatusHistoryEntry(status=DocumentStatus.CHUNKED, trace_id=trace_id)
    await db.documents.update_one(
        {"_id": document_id},
        {
            "$set": {"status": DocumentStatus.CHUNKED, "stats.chunk_count": len(chunks)},
            "$push": {"status_history": entry.model_dump()},
        },
    )

    await publish(
        exchange_name="documents",
        routing_key="document.chunked",
        payload={
            "document_id": document_id,
            "project_id": project_id,
            "chunk_ids": [c.id for c in chunks],
        },
        trace_id=trace_id,
    )
    logger.info("document chunked", document_id=document_id, chunks=len(chunks))
