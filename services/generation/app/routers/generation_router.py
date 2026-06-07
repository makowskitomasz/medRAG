import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.config.settings import Settings, settings
from app.schemas.generation_schemas import (
    ConflictDetectionRequest,
    ConflictDetectionResult,
    CorrectnessRequest,
    CorrectnessResult,
    EvaluationRequest,
    EvaluationResult,
    GenerationRequest,
    GenerationResult,
)
from app.services.generation_service import (
    assess_correctness,
    detect_conflict,
    evaluate_answer,
    generate,
    generate_stream,
    get_instructor_client,
    get_llm_client,
)

router = APIRouter()
_logger = logging.getLogger(__name__)


def get_settings() -> Settings:
    return settings


def get_client(cfg: Settings = Depends(get_settings)) -> AsyncOpenAI:
    return get_llm_client(cfg.llm_base_url, cfg.resolved_api_key)


@router.post("/generate", response_model=GenerationResult)
async def generate_answer(
    request: GenerationRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> GenerationResult:
    model = request.llm_model or cfg.llm_model
    _logger.info("generate request model=%s", model)
    return await generate(request, client, model, cfg.llm_max_tokens, cfg.llm_temperature)


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate(
    request: EvaluationRequest,
    cfg: Settings = Depends(get_settings),
) -> EvaluationResult:
    model = request.llm_model or cfg.llm_model
    iclient = get_instructor_client(cfg.llm_base_url, cfg.resolved_api_key, model)
    return await evaluate_answer(request, iclient, model)


@router.post("/detect_conflict", response_model=ConflictDetectionResult)
async def conflict_detection(
    request: ConflictDetectionRequest,
    cfg: Settings = Depends(get_settings),
) -> ConflictDetectionResult:
    model = cfg.llm_model
    iclient = get_instructor_client(cfg.llm_base_url, cfg.resolved_api_key, model)
    return await detect_conflict(request, iclient, model)


@router.post("/correctness", response_model=CorrectnessResult)
async def correctness(
    request: CorrectnessRequest,
    cfg: Settings = Depends(get_settings),
) -> CorrectnessResult:
    model = request.llm_model or cfg.llm_model
    iclient = get_instructor_client(cfg.llm_base_url, cfg.resolved_api_key, model)
    return await assess_correctness(request, iclient, model)


@router.post("/generate/stream")
async def generate_answer_stream(
    request: GenerationRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> StreamingResponse:
    return StreamingResponse(
        generate_stream(
            request,
            client,
            request.llm_model or cfg.llm_model,
            cfg.llm_max_tokens,
            cfg.llm_temperature,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
