from fastapi import APIRouter, Depends
from openai import AsyncOpenAI

from app.config.settings import Settings, settings
from app.schemas.query_schemas import (
    HyDERequest,
    HyDEResponse,
    QueryRewriteRequest,
    QueryRewriteResponse,
)
from app.services.llm_client import get_llm_client
from app.services.query_service import generate_hypothetical_document, rewrite_query

router = APIRouter()


def get_settings() -> Settings:
    return settings


def get_client(cfg: Settings = Depends(get_settings)) -> AsyncOpenAI:
    return get_llm_client(cfg.llm_base_url, cfg.resolved_api_key)


@router.post("/rewrite", response_model=QueryRewriteResponse)
async def rewrite(
    request: QueryRewriteRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> QueryRewriteResponse:
    rewritten = await rewrite_query(request.query, request.context, client, cfg.llm_model)
    return QueryRewriteResponse(original_query=request.query, rewritten_query=rewritten)


@router.post("/hyde", response_model=HyDEResponse)
async def hyde(
    request: HyDERequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> HyDEResponse:
    doc = await generate_hypothetical_document(request.query, client, cfg.llm_model)
    return HyDEResponse(query=request.query, hypothetical_document=doc)
