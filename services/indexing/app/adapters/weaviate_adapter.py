from typing import Any

import weaviate.classes as wvc


def build_objects(
    embeddings: list[dict[str, Any]],
    chunk_map: dict[str, dict],
    document_id: str,
    project_id: str,
) -> list[wvc.data.DataObject]:
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
    return objects
