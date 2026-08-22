from typing import Any

from medrag_shared.logging import bind_trace_id

from app.services import chunking_service


async def handle_document_parsed(payload: dict[str, Any], trace_id: str | None) -> None:
    if trace_id:
        bind_trace_id(trace_id)
    await chunking_service.chunk(
        document_id=payload["document_id"],
        project_id=payload["project_id"],
        trace_id=trace_id,
    )
