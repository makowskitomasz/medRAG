from unittest.mock import MagicMock, patch

import pytest

from app.schemas.reranker_schemas import ChunkInput, RerankRequest
from app.services.reranker_service import rerank


def _make_chunk(chunk_id: str, content: str) -> ChunkInput:
    return ChunkInput(chunk_id=chunk_id, content=content, score=0.5)


@pytest.mark.asyncio
async def test_rerank_returns_top_n_sorted():
    chunks = [
        _make_chunk("c1", "Aspirin is an anticoagulant"),
        _make_chunk("c2", "Warfarin interacts with aspirin"),
        _make_chunk("c3", "Ibuprofen is an NSAID"),
    ]
    request = RerankRequest(query="aspirin warfarin interaction", chunks=chunks, top_n=2)

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.3, 0.9, 0.1]

    with patch("app.services.reranker_service._load_model", return_value=mock_model):
        result = await rerank(request, "BAAI/bge-reranker-v2-m3")

    assert len(result.chunks) == 2
    assert result.chunks[0].chunk_id == "c2"
    assert result.chunks[0].score == pytest.approx(0.9)
    assert result.chunks[1].chunk_id == "c1"


@pytest.mark.asyncio
async def test_rerank_empty_input():
    request = RerankRequest(query="test", chunks=[], top_n=5)
    result = await rerank(request, "BAAI/bge-reranker-v2-m3")
    assert result.chunks == []
