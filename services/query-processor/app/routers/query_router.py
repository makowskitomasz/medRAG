from fastapi import APIRouter, Depends
from openai import AsyncOpenAI

from app.config.settings import Settings, settings
from app.schemas.query_schemas import (
    DecomposeRequest,
    DecomposeResponse,
    HyDERequest,
    HyDEResponse,
    QueryRewriteRequest,
    QueryRewriteResponse,
    TriageRequest,
    TriageResponse,
)
from app.services.llm_client import get_llm_client
from app.services.query_service import (
    decompose_query,
    generate_hypothetical_document,
    rewrite_query,
    triage_query,
)

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


@router.post("/decompose", response_model=DecomposeResponse)
async def decompose(
    request: DecomposeRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> DecomposeResponse:
    sub_questions = await decompose_query(request.query, client, cfg.llm_model)
    return DecomposeResponse(original_query=request.query, sub_questions=sub_questions)


@router.post("/triage", response_model=TriageResponse)
async def triage(
    request: TriageRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> TriageResponse:
    result = await triage_query(request.query, client, cfg.llm_model)
    return TriageResponse(
        complexity=result.get("complexity", "standard"),
        conflict_risk=result.get("conflict_risk", "low"),
        route=result.get("route", "vanilla"),
    )
