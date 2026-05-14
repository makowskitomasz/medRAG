from fastapi import APIRouter, Depends

from app.config.settings import Settings, settings
from app.schemas.reranker_schemas import RerankRequest, RerankResponse
from app.services.reranker_service import rerank

router = APIRouter()


def get_settings() -> Settings:
    return settings


@router.post("/rerank", response_model=RerankResponse)
async def rerank_chunks(
    request: RerankRequest,
    cfg: Settings = Depends(get_settings),
) -> RerankResponse:
    return await rerank(request, cfg.reranker_model)
