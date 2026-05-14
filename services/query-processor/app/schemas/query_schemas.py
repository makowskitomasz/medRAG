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
