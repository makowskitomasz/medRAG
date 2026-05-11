from pydantic import BaseModel


class ContextChunk(BaseModel):
    chunk_id: str
    content: str
    score: float = 0.0
    document_id: str = ""
    filename: str | None = None
    page: int | None = None


class GenerationRequest(BaseModel):
    query: str
    chunks: list[ContextChunk]
    conversation_history: list[dict] = []


class Citation(BaseModel):
    chunk_id: str
    filename: str | None = None
    page: int | None = None
    snippet: str


class GenerationResult(BaseModel):
    answer: str
    citations: list[Citation]
