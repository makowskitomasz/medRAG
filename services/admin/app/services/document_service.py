import math

from app.repositories import document_repository
from app.schemas.document_schemas import (
    DocumentResponse,
    PaginatedDocumentsResponse,
    StatusHistoryEntry,
)


async def list_documents(
    project_id: str,
    page: int,
    limit: int,
    status: str | None,
) -> PaginatedDocumentsResponse:
    docs, total = await document_repository.list_by_project(project_id, page, limit, status)
    items = [
        DocumentResponse(
            document_id=str(doc["_id"]),
            filename=doc["filename"],
            status=doc["status"],
            created_at=doc["created_at"],
            status_history=[StatusHistoryEntry(**e) for e in doc.get("status_history", [])],
            file_size=doc.get("stats", {}).get("file_size"),
            page_count=doc.get("stats", {}).get("page_count"),
            chunk_count=doc.get("stats", {}).get("chunk_count"),
        )
        for doc in docs
    ]
    return PaginatedDocumentsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=max(1, math.ceil(total / limit)),
    )
