from typing import Any

from medrag_shared.logging import bind_trace_id

from app.services import parser_service


async def handle_document_uploaded(payload: dict[str, Any], trace_id: str | None) -> None:
    if trace_id:
        bind_trace_id(trace_id)
    await parser_service.parse(
        document_id=payload["document_id"],
        tmp_path=payload["tmp_path"],
        project_id=payload["project_id"],
        trace_id=trace_id,
    )
