from datetime import datetime

from medrag_shared.models.document import DocumentStatus
from pydantic import BaseModel


class StatusHistoryEntry(BaseModel):
    status: DocumentStatus
    timestamp: datetime
    trace_id: str | None = None
    error: str | None = None


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    created_at: datetime
    status_history: list[StatusHistoryEntry] = []
    file_size: int | None = None
    page_count: int | None = None
    chunk_count: int | None = None


class PaginatedDocumentsResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    limit: int
    pages: int
