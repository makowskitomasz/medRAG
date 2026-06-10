from pydantic import BaseModel, Field, field_validator


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
    prompt_overrides: dict[str, str] = {}
    llm_model: str | None = None


class Citation(BaseModel):
    chunk_id: str
    filename: str | None = None
    page: int | None = None
    snippet: str
    relevance: float | None = None


class GenerationResult(BaseModel):
    answer: str
    citations: list[Citation]
    input_tokens: int = 0
    output_tokens: int = 0


class EvaluationRequest(BaseModel):
    query: str
    answer: str
    chunks: list[ContextChunk]
    prompt_overrides: dict[str, str] = {}
    llm_model: str | None = None


class EvaluationResult(BaseModel):
    score: float
    reasoning: str
    input_tokens: int = 0
    output_tokens: int = 0

    model_config = {
        "json_schema_extra": {"required": ["score", "reasoning", "input_tokens", "output_tokens"]}
    }


class ConflictDetectionRequest(BaseModel):
    chunks: list[ContextChunk]
    prompt_overrides: dict[str, str] = {}


class ConflictDetectionResult(BaseModel):
    has_conflict: bool
    confidence: float
    reasoning: str
    input_tokens: int = 0
    output_tokens: int = 0

    model_config = {
        "json_schema_extra": {
            "required": ["has_conflict", "confidence", "reasoning", "input_tokens", "output_tokens"]
        }
    }


class CorrectnessRequest(BaseModel):
    query: str
    answer: str
    gold_answer: str
    llm_model: str | None = None


class CorrectnessResult(BaseModel):
    score: float = Field(description="Correctness score between 0.0 and 1.0")
    reasoning: str
    input_tokens: int = 0
    output_tokens: int = 0

    model_config = {
        "json_schema_extra": {"required": ["score", "reasoning", "input_tokens", "output_tokens"]}
    }

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
