from datetime import datetime
from enum import StrEnum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    FAILED = "failed"


class StatusHistoryEntry(BaseModel):
    status: DocumentStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str | None = None
    error: str | None = None


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str
    filename: str
    content_hash: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    status_history: list[StatusHistoryEntry] = Field(default_factory=list)
    extracted_text: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    document_id: str
    project_id: str
    chunk_index: int
    content: str
    page: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    weaviate_id: str | None = None

    model_config = {"populate_by_name": True}
