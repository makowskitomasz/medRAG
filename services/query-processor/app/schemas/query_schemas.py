from pydantic import BaseModel


class QueryRewriteRequest(BaseModel):
    query: str
    context: str = ""
    llm_model: str | None = None
    prompt_overrides: dict[str, str] = {}


class QueryRewriteResponse(BaseModel):
    original_query: str
    rewritten_query: str
    input_tokens: int = 0
    output_tokens: int = 0


class HyDERequest(BaseModel):
    query: str
    llm_model: str | None = None
    prompt_overrides: dict[str, str] = {}


class HyDEResponse(BaseModel):
    query: str
    hypothetical_document: str
    input_tokens: int = 0
    output_tokens: int = 0


class DecomposeRequest(BaseModel):
    query: str
    llm_model: str | None = None
    prompt_overrides: dict[str, str] = {}


class DecomposeResponse(BaseModel):
    original_query: str
    sub_questions: list[str]
    input_tokens: int = 0
    output_tokens: int = 0


class TriageRequest(BaseModel):
    query: str
    llm_model: str | None = None
    prompt_overrides: dict[str, str] = {}


class TriageResponse(BaseModel):
    complexity: str  # simple | standard | complex | multi_hop
    conflict_risk: str  # low | medium | high
    route: str  # one of RagMode values
    input_tokens: int = 0
    output_tokens: int = 0
