from unittest.mock import AsyncMock, MagicMock

import pytest
from medrag_shared.models.project import RagMode

from app.pipelines.corrective_rag import CorrectiveRagPipeline
from app.pipelines.factory import get_pipeline
from app.pipelines.hyde import HydePipeline
from app.pipelines.multi_agent import MultiAgentPipeline
from app.pipelines.query_rewriting import QueryRewritingPipeline
from app.pipelines.self_reflection import SelfReflectionPipeline
from app.pipelines.vanilla import VanillaPipeline


def _mock_deps():
    return MagicMock(), MagicMock()


def test_vanilla_mode_returns_vanilla_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.VANILLA, http, settings), VanillaPipeline)


def test_hyde_mode_returns_hyde_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.HYDE, http, settings), HydePipeline)


def test_query_rewriting_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.QUERY_REWRITING, http, settings), QueryRewritingPipeline)


def test_self_reflection_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.SELF_REFLECTION, http, settings), SelfReflectionPipeline)


def test_multi_agent_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.MULTI_AGENT, http, settings), MultiAgentPipeline)


def test_corrective_rag_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.CORRECTIVE_RAG, http, settings), CorrectiveRagPipeline)


@pytest.mark.asyncio
async def test_self_reflection_stops_when_score_sufficient():
    http = MagicMock()
    settings = MagicMock()
    settings.retrieval_url = "http://retrieval"
    settings.reranker_url = "http://reranker"
    settings.generation_url = "http://generation"

    pipeline = SelfReflectionPipeline(http, settings)
    chunks = [{"chunk_id": "c1", "content": "Warfarin increases bleeding.", "score": 0.9}]

    pipeline._retrieve = AsyncMock(return_value=chunks)
    pipeline._rerank = AsyncMock(return_value=chunks)
    pipeline._generate = AsyncMock(return_value=("Warfarin increases bleeding risk.", []))
    pipeline._evaluate_answer = AsyncMock(return_value=0.9)

    result = await pipeline.run(
        query="What is warfarin risk?",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="self_reflection",
        top_k=5,
        alpha=0.5,
        rerank_top_n=3,
    )

    assert result.answer == "Warfarin increases bleeding risk."
    assert pipeline._retrieve.call_count == 1
    assert pipeline._evaluate_answer.call_count == 1


@pytest.mark.asyncio
async def test_self_reflection_retries_when_score_insufficient():
    http = MagicMock()
    settings = MagicMock()
    pipeline = SelfReflectionPipeline(http, settings)
    chunks = [{"chunk_id": "c1", "content": "text", "score": 0.5}]

    pipeline._retrieve = AsyncMock(return_value=chunks)
    pipeline._rerank = AsyncMock(return_value=chunks)
    pipeline._generate = AsyncMock(return_value=("answer", []))
    pipeline._evaluate_answer = AsyncMock(return_value=0.2)

    await pipeline.run(
        query="test query",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="self_reflection",
        top_k=5,
        alpha=0.5,
        rerank_top_n=3,
    )

    assert pipeline._retrieve.call_count == 2


@pytest.mark.asyncio
async def test_multi_agent_deduplicates_chunks():
    http = MagicMock()
    settings = MagicMock()
    pipeline = MultiAgentPipeline(http, settings)

    shared_chunk = {"chunk_id": "c1", "content": "shared", "score": 0.8}
    unique_chunk = {"chunk_id": "c2", "content": "unique", "score": 0.6}

    pipeline._retrieve = AsyncMock(
        side_effect=[
            [shared_chunk],
            [shared_chunk, unique_chunk],
            [shared_chunk],
        ]
    )
    pipeline._rerank = AsyncMock(return_value=[shared_chunk, unique_chunk])
    pipeline._generate = AsyncMock(return_value=("answer", []))

    result = await pipeline.run(
        query="drug interaction",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="multi_agent",
        top_k=9,
        alpha=0.5,
        rerank_top_n=3,
    )

    rerank_call_chunks = pipeline._rerank.call_args[0][1]
    chunk_ids = [c["chunk_id"] for c in rerank_call_chunks]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert result.answer == "answer"


@pytest.mark.asyncio
async def test_corrective_rag_triggers_fallback_on_low_relevance():
    http = MagicMock()
    settings = MagicMock()
    pipeline = CorrectiveRagPipeline(http, settings)

    low_score_chunks = [{"chunk_id": "c1", "content": "text", "score": 0.1}]
    fallback_chunks = [{"chunk_id": "c2", "content": "fallback", "score": 0.8}]

    pipeline._retrieve = AsyncMock(side_effect=[low_score_chunks, fallback_chunks])
    pipeline._rerank = AsyncMock(return_value=fallback_chunks)
    pipeline._generate = AsyncMock(return_value=("answer", []))

    await pipeline.run(
        query="test query",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="corrective_rag",
        top_k=5,
        alpha=0.5,
        rerank_top_n=3,
    )

    assert pipeline._retrieve.call_count == 2


@pytest.mark.asyncio
async def test_corrective_rag_no_fallback_when_relevant():
    http = MagicMock()
    settings = MagicMock()
    pipeline = CorrectiveRagPipeline(http, settings)

    good_chunks = [
        {"chunk_id": "c1", "content": "text", "score": 0.8},
        {"chunk_id": "c2", "content": "text", "score": 0.7},
    ]
    pipeline._retrieve = AsyncMock(return_value=good_chunks)
    pipeline._rerank = AsyncMock(return_value=good_chunks)
    pipeline._generate = AsyncMock(return_value=("answer", []))

    await pipeline.run(
        query="test query",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="corrective_rag",
        top_k=5,
        alpha=0.5,
        rerank_top_n=3,
    )

    assert pipeline._retrieve.call_count == 1
