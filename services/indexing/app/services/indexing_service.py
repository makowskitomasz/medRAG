from typing import Any

from medrag_shared import get_logger

from app.adapters.weaviate_adapter import build_objects
from app.config import settings
from app.connectors.weaviate_connector import get_client
from app.repositories import chunk_repository, document_repository

logger = get_logger(__name__)


async def index(
    document_id: str,
    project_id: str,
    embeddings: list[dict[str, Any]],
    trace_id: str | None,
) -> None:
    logger.info("indexing chunks", document_id=document_id, count=len(embeddings))

    chunk_ids = [e["chunk_id"] for e in embeddings]
    chunks = await chunk_repository.find_by_ids(chunk_ids)
    chunk_map = {c["_id"]: c for c in chunks}

    objects = build_objects(embeddings, chunk_map, document_id, project_id)

    if objects:
        client = get_client()
        collection = client.collections.get(settings.weaviate_collection)
        result = collection.data.insert_many(objects)
        for emb, obj_uuid in zip(embeddings, result.uuids.values(), strict=False):
            await chunk_repository.update_weaviate_id(emb["chunk_id"], str(obj_uuid))

    await document_repository.update_indexed(document_id, trace_id)
    logger.info("chunks indexed", document_id=document_id, count=len(objects))
