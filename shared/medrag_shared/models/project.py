from datetime import UTC, datetime
from enum import StrEnum

from bson import ObjectId
from pydantic import BaseModel, Field


class ChunkingStrategy(StrEnum):
    FIXED_512 = "fixed_512"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


class EmbeddingProvider(StrEnum):
    LOCAL_BGE = "local_bge"
    COHERE = "cohere"
    OPENAI = "openai"


class RagMode(StrEnum):
    VANILLA = "vanilla"
    HYDE = "hyde"
    QUERY_REWRITING = "query_rewriting"
    SELF_REFLECTION = "self_reflection"
    MULTI_AGENT = "multi_agent"
    CORRECTIVE_RAG = "corrective_rag"
    ITERATIVE_MULTIHOP = "iterative_multihop"
    MADAM_RAG = "madam_rag"
    RARE_RAG = "rare_rag"


class ProjectSettings(BaseModel):
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    embedding_provider: EmbeddingProvider = EmbeddingProvider.LOCAL_BGE
    rag_mode: RagMode = RagMode.VANILLA
    hybrid_alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    top_k: int = Field(default=20, ge=1, le=100)
    rerank_top_n: int = Field(default=5, ge=1, le=20)
    # Per-project Jinja2 prompt overrides. Keys match template slugs
    # (e.g. "generate_system", "evaluate_system"). Empty = use file defaults.
    prompt_overrides: dict[str, str] = Field(default_factory=dict)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    description: str = ""
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"populate_by_name": True}
