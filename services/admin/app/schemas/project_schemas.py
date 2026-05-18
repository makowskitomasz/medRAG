from datetime import datetime

from medrag_shared.models.project import (
    ChunkingStrategy,
    EmbeddingProvider,
    ProjectSettings,
    RagMode,
)
from pydantic import BaseModel, Field


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: ProjectSettings | None = None


class UpdateSettingsRequest(BaseModel):
    """Granular PATCH — only provided fields are updated."""

    chunking_strategy: ChunkingStrategy | None = None
    embedding_provider: EmbeddingProvider | None = None
    rag_mode: RagMode | None = None
    hybrid_alpha: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1, le=100)
    rerank_top_n: int | None = Field(default=None, ge=1, le=20)
    prompt_overrides: dict[str, str] | None = None


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
    created_by: str
    created_at: datetime


# --- Settings options schema (for frontend dropdowns / sliders) ---


class EnumOption(BaseModel):
    value: str
    label: str
    description: str


class FieldConstraint(BaseModel):
    type: str  # "float" | "int"
    min: float
    max: float
    step: float
    default: float
    description: str


class PromptSlot(BaseModel):
    slug: str
    label: str
    description: str
    default_template: str


class SettingsOptions(BaseModel):
    rag_modes: list[EnumOption]
    chunking_strategies: list[EnumOption]
    embedding_providers: list[EnumOption]
    hybrid_alpha: FieldConstraint
    top_k: FieldConstraint
    rerank_top_n: FieldConstraint
    prompt_slots: list[PromptSlot]


class ReindexResponse(BaseModel):
    project_id: str
    documents_queued: int
