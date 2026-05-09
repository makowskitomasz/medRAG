from medrag_shared import get_logger
from medrag_shared.amqp import publish
from medrag_shared.models.document import Chunk
from medrag_shared.models.project import ChunkingStrategy

from app.adapters.chunking_adapter import get_chunker
from app.repositories import chunk_repository, document_repository, project_repository

logger = get_logger(__name__)


async def chunk(document_id: str, project_id: str, trace_id: str | None) -> None:
    logger.info("chunking document", document_id=document_id)

    doc = await document_repository.find_by_id(document_id)
    if not doc or not doc.get("extracted_text"):
        logger.error("document or text not found", document_id=document_id)
        return

    project = await project_repository.find_by_id(project_id)
    strategy = (
        project.get("settings", {}).get("chunking_strategy", ChunkingStrategy.RECURSIVE)
        if project
        else ChunkingStrategy.RECURSIVE
    )

    chunker = get_chunker(strategy)
    texts = chunker.split(doc["extracted_text"])

    chunks = [
        Chunk(document_id=document_id, project_id=project_id, chunk_index=i, content=text)
        for i, text in enumerate(texts)
    ]

    await chunk_repository.insert_many(chunks)
    await document_repository.update_chunked(document_id, len(chunks), trace_id)

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
