from pydantic import BaseModel, Field


class ChunkInput(BaseModel):
    chunk_id: str
    content: str
    score: float = 0.0
    document_id: str = ""
    project_id: str = ""
    chunk_index: int = 0
    page: int | None = None
    document_title: str | None = None
    filename: str | None = None


class RerankRequest(BaseModel):
    query: str
    chunks: list[ChunkInput]
    top_n: int = Field(default=5, ge=1, le=20)


class RerankResponse(BaseModel):
    chunks: list[ChunkInput]
