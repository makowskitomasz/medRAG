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
    # Intermediate findings / peer answers produced by upstream agents or hops.
    evidence_notes: list[str] = []
    # Role-specific instructions appended to the system prompt (agent, judge, synthesiser).
    task_instructions: str | None = None


class Citation(BaseModel):
    chunk_id: str
    #: SOURCE_N index as written in the answer. Only cited sources are returned, so
    #: this is NOT the position in this list — clients must match markers by `n`.
    n: int | None = None
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


class ExtractRequest(BaseModel):
    """Extract a focused intermediate finding from passages for one sub-question."""

    query: str
    sub_question: str
    chunks: list[ContextChunk]
    prior_findings: list[str] = []
    next_question_draft: str | None = None
    prompt_overrides: dict[str, str] = {}
    llm_model: str | None = None


class ExtractResult(BaseModel):
    finding: str = Field(description="Self-contained statement of what the passages establish.")
    next_question: str = Field(
        default="",
        description="Next sub-question rewritten with resolved entities; empty if none requested.",
    )
    input_tokens: int = 0
    output_tokens: int = 0

    model_config = {
        "json_schema_extra": {
            "required": ["finding", "next_question", "input_tokens", "output_tokens"]
        }
    }


class VerifyClaimsRequest(BaseModel):
    answer: str
    chunks: list[ContextChunk]
    prompt_overrides: dict[str, str] = {}
    llm_model: str | None = None


class ClaimVerdict(BaseModel):
    claim: str
    supported: bool


class VerifyClaimsResult(BaseModel):
    claims: list[ClaimVerdict] = Field(default_factory=list)
    grounding_score: float = 1.0
    input_tokens: int = 0
    output_tokens: int = 0


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
