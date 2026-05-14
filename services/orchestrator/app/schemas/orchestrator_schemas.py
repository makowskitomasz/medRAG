from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    project_id: str
    query: str
    conversation_id: str | None = None
    stream: bool = False


class Citation(BaseModel):
    chunk_id: str
    filename: str | None = None
    page: int | None = None
    snippet: str


class QueryResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[Citation]
    rag_mode: str


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str
    user_id: str | None = None
    messages: list[ConversationMessage] = Field(default_factory=list)
    rag_mode: str = "vanilla"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
