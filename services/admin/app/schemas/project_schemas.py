from medrag_shared.models.project import (
    ChunkingStrategy,
    EmbeddingProvider,
    ProjectSettings,
    RagMode,
)
from pydantic import BaseModel


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: ProjectSettings | None = None


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    embedding_provider: EmbeddingProvider = EmbeddingProvider.LOCAL_BGE
    rag_mode: RagMode = RagMode.VANILLA
    hybrid_alpha: float = 0.5
    top_k: int = 20
    rerank_top_n: int = 5


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    settings: ProjectSettings
