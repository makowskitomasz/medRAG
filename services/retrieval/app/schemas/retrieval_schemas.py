from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str
    project_id: str
    top_k: int = Field(default=20, ge=1, le=100)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    query_vector: list[float] | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    project_id: str
    content: str
    score: float
    chunk_index: int
    page: int | None = None
    document_title: str | None = None
    filename: str | None = None


class RetrievalResponse(BaseModel):
    chunks: list[RetrievedChunk]
    total: int
