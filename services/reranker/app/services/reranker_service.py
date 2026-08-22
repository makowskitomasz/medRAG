import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import torch
from sentence_transformers import CrossEncoder

from app.schemas.reranker_schemas import ChunkInput, RerankRequest, RerankResponse

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)
_model: CrossEncoder | None = None


def _best_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_model(model_name: str) -> CrossEncoder:
    global _model
    if _model is None:
        device = _best_device()
        logger.info("loading reranker model", extra={"model": model_name, "device": device})
        _model = CrossEncoder(model_name, device=device)
        logger.info("reranker model loaded", extra={"device": device})
    return _model


def _score_pairs(model: CrossEncoder, query: str, texts: list[str]) -> list[float]:
    pairs = [[query, text] for text in texts]
    raw = model.predict(pairs)
    scores: list[float] = raw.tolist() if hasattr(raw, "tolist") else list(raw)
    return scores


async def rerank(request: RerankRequest, model_name: str) -> RerankResponse:
    if not request.chunks:
        return RerankResponse(chunks=[])

    loop = asyncio.get_event_loop()
    model = await loop.run_in_executor(_executor, _load_model, model_name)

    texts = [c.content for c in request.chunks]
    scores = await loop.run_in_executor(_executor, _score_pairs, model, request.query, texts)

    scored: list[tuple[float, ChunkInput]] = sorted(
        zip(scores, request.chunks, strict=False), key=lambda x: x[0], reverse=True
    )
    top = [chunk.model_copy(update={"score": score}) for score, chunk in scored[: request.top_n]]
    return RerankResponse(chunks=top)
