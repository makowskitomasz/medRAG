from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.config.settings import Settings, settings
from app.schemas.generation_schemas import (
    EvaluationRequest,
    EvaluationResult,
    GenerationRequest,
    GenerationResult,
)
from app.services.generation_service import (
    evaluate_answer,
    generate,
    generate_stream,
    get_llm_client,
)

router = APIRouter()


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
    return await generate(request, client, cfg.llm_model, cfg.llm_max_tokens, cfg.llm_temperature)


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate(
    request: EvaluationRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> EvaluationResult:
    return await evaluate_answer(request, client, cfg.llm_model)


@router.post("/generate/stream")
async def generate_answer_stream(
    request: GenerationRequest,
    cfg: Settings = Depends(get_settings),
    client: AsyncOpenAI = Depends(get_client),
) -> StreamingResponse:
    return StreamingResponse(
        generate_stream(request, client, cfg.llm_model, cfg.llm_max_tokens, cfg.llm_temperature),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
