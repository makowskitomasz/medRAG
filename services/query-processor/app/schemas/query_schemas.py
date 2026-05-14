from pydantic import BaseModel


class QueryRewriteRequest(BaseModel):
    query: str
    context: str = ""


class QueryRewriteResponse(BaseModel):
    original_query: str
    rewritten_query: str


class HyDERequest(BaseModel):
    query: str


class HyDEResponse(BaseModel):
    query: str
    hypothetical_document: str


class DecomposeRequest(BaseModel):
    query: str


class DecomposeResponse(BaseModel):
    original_query: str
    sub_questions: list[str]


class TriageRequest(BaseModel):
    query: str


class TriageResponse(BaseModel):
    complexity: str  # simple | standard | complex | multi_hop
    conflict_risk: str  # low | medium | high
    route: str  # one of RagMode values
