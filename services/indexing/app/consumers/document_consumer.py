from typing import Any

from medrag_shared.logging import bind_trace_id

from app.services import indexing_service


async def handle_chunks_embedded(payload: dict[str, Any], trace_id: str | None) -> None:
    if trace_id:
        bind_trace_id(trace_id)
    await indexing_service.index(
        document_id=payload["document_id"],
        project_id=payload["project_id"],
        embeddings=payload.get("embeddings", []),
        trace_id=trace_id,
    )
