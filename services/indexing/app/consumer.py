from typing import Any

import weaviate.classes as wvc
from medrag_shared import get_logger
from medrag_shared.logging import bind_trace_id
from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db

from app.config import settings
from app.weaviate_client import get_client

logger = get_logger(__name__)


async def handle_chunks_embedded(payload: dict[str, Any], trace_id: str | None) -> None:
    document_id: str = payload["document_id"]
    project_id: str = payload["project_id"]
    embeddings: list[dict[str, Any]] = payload.get("embeddings", [])

    if trace_id:
        bind_trace_id(trace_id)

    logger.info("indexing chunks", document_id=document_id, count=len(embeddings))
    db = get_db()
    client = get_client()
    collection = client.collections.get(settings.weaviate_collection)

    chunk_ids = [e["chunk_id"] for e in embeddings]
    chunks = await db.chunks.find({"_id": {"$in": chunk_ids}}).to_list(len(chunk_ids))
    chunk_map = {c["_id"]: c for c in chunks}

    objects = []
    for emb in embeddings:
        chunk = chunk_map.get(emb["chunk_id"])
        if not chunk:
            continue
        objects.append(
            wvc.data.DataObject(
                properties={
                    "chunk_id": emb["chunk_id"],
                    "document_id": document_id,
                    "project_id": project_id,
                    "content": chunk.get("content", ""),
                    "chunk_index": chunk.get("chunk_index", 0),
                },
                vector=emb["vector"],
            )
        )

    if objects:
        result = collection.data.insert_many(objects)
        # update weaviate_id in mongo for each chunk
        for emb, obj_uuid in zip(embeddings, result.uuids.values(), strict=False):
            await db.chunks.update_one(
                {"_id": emb["chunk_id"]},
                {"$set": {"weaviate_id": str(obj_uuid)}},
            )

    entry = StatusHistoryEntry(status=DocumentStatus.INDEXED, trace_id=trace_id)
    await db.documents.update_one(
        {"_id": document_id},
        {
            "$set": {"status": DocumentStatus.INDEXED},
            "$push": {"status_history": entry.model_dump()},
        },
    )
    logger.info("chunks indexed", document_id=document_id, count=len(objects))
