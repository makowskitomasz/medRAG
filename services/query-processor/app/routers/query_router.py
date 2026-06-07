import instructor
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
from app.services.llm_client import get_instructor_client, get_llm_client
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


def get_iclient(cfg: Settings = Depends(get_settings)) -> instructor.AsyncInstructor:
    return get_instructor_client(cfg.llm_base_url, cfg.resolved_api_key)


@router.post("/rewrite", response_model=QueryRewriteResponse)
async def rewrite(
    request: QueryRewriteRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> QueryRewriteResponse:
    rewritten, inp, out = await rewrite_query(
        request.query,
        request.context,
        client,
        request.llm_model or cfg.llm_model,
        request.prompt_overrides,
    )
    return QueryRewriteResponse(
        original_query=request.query,
        rewritten_query=rewritten,
        input_tokens=inp,
        output_tokens=out,
    )


@router.post("/hyde", response_model=HyDEResponse)
async def hyde(
    request: HyDERequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> HyDEResponse:
    doc, inp, out = await generate_hypothetical_document(
        request.query, client, request.llm_model or cfg.llm_model, request.prompt_overrides
    )
    return HyDEResponse(
        query=request.query,
        hypothetical_document=doc,
        input_tokens=inp,
        output_tokens=out,
    )


@router.post("/decompose", response_model=DecomposeResponse)
async def decompose(
    request: DecomposeRequest,
    cfg: Settings = Depends(get_settings),
    iclient: instructor.AsyncInstructor = Depends(get_iclient),
) -> DecomposeResponse:
    sub_questions, inp, out = await decompose_query(
        request.query,
        iclient,
        request.llm_model or cfg.llm_model,
        prompt_overrides=request.prompt_overrides,
    )
    return DecomposeResponse(
        original_query=request.query,
        sub_questions=sub_questions,
        input_tokens=inp,
        output_tokens=out,
    )


@router.post("/triage", response_model=TriageResponse)
async def triage(
    request: TriageRequest,
    cfg: Settings = Depends(get_settings),
    iclient: instructor.AsyncInstructor = Depends(get_iclient),
) -> TriageResponse:
    result = await triage_query(
        request.query, iclient, request.llm_model or cfg.llm_model, request.prompt_overrides
    )
    return TriageResponse(
        complexity=result["complexity"],
        conflict_risk=result["conflict_risk"],
        route=result["route"],
        input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
    )
