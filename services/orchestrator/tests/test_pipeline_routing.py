from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from medrag_shared.models.project import RagMode

from app.pipelines.corrective_rag import CorrectiveRagPipeline
from app.pipelines.factory import get_pipeline
from app.pipelines.hyde import HydePipeline
from app.pipelines.iterative_multihop import IterativeMultiHopPipeline
from app.pipelines.madam_rag import _AGENTS, MadamRagPipeline
from app.pipelines.multi_agent import MultiAgentPipeline
from app.pipelines.query_rewriting import QueryRewritingPipeline
from app.pipelines.rare_rag import RareRagPipeline
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


def test_iterative_multihop_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(
        get_pipeline(RagMode.ITERATIVE_MULTIHOP, http, settings), IterativeMultiHopPipeline
    )


def test_madam_rag_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.MADAM_RAG, http, settings), MadamRagPipeline)


def test_rare_rag_mode_returns_correct_pipeline():
    http, settings = _mock_deps()
    assert isinstance(get_pipeline(RagMode.RARE_RAG, http, settings), RareRagPipeline)


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


@pytest.mark.asyncio
async def test_iterative_multihop_deduplicates_across_sub_questions():
    http = MagicMock()
    settings = MagicMock()
    settings.query_processor_url = "http://query-processor"
    pipeline = IterativeMultiHopPipeline(http, settings)

    shared = {"chunk_id": "c1", "content": "warfarin", "score": 0.9}
    unique = {"chunk_id": "c2", "content": "aspirin", "score": 0.7}

    pipeline._decompose = AsyncMock(return_value=["sub q1", "sub q2"])
    pipeline._retrieve = AsyncMock(side_effect=[[shared, unique], [shared]])
    pipeline._rerank = AsyncMock(return_value=[shared, unique])
    pipeline._generate = AsyncMock(return_value=("answer", []))

    result = await pipeline.run(
        query="complex drug interaction question",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="iterative_multihop",
        top_k=6,
        alpha=0.5,
        rerank_top_n=3,
    )

    rerank_chunks = pipeline._rerank.call_args[0][1]
    ids = [c["chunk_id"] for c in rerank_chunks]
    assert len(ids) == len(set(ids))
    assert result.answer == "answer"


@pytest.mark.asyncio
async def test_madam_rag_debates_then_judges():
    http = MagicMock()
    settings = MagicMock()
    pipeline = MadamRagPipeline(http, settings)

    chunks = [{"chunk_id": "c1", "content": "text", "score": 0.8}]

    pipeline._agent_retrieve = AsyncMock(return_value=chunks)
    pipeline._rerank = AsyncMock(return_value=chunks)
    pipeline._generate = AsyncMock(return_value=("answer", []))

    result = await pipeline.run(
        query="Is warfarin safe?",
        project_id="proj-1",
        conversation_id="conv-1",
        conversation_history=[],
        rag_mode="madam_rag",
        top_k=9,
        alpha=0.5,
        rerank_top_n=3,
    )

    # 2 candidate answers + 2 revisions + 1 judge
    assert pipeline._generate.await_count == 5
    assert result.answer == "answer"

    judge_kwargs = pipeline._generate.call_args.kwargs
    assert "judge" in judge_kwargs["task_instructions"].lower()
    assert len(judge_kwargs["evidence_notes"]) == 2


@pytest.mark.asyncio
async def test_madam_rag_revision_sees_opposing_answer():
    http = MagicMock()
    settings = MagicMock()
    pipeline = MadamRagPipeline(http, settings)

    chunks = [{"chunk_id": "c1", "content": "text", "score": 0.8}]
    pipeline._agent_retrieve = AsyncMock(return_value=chunks)
    pipeline._rerank = AsyncMock(return_value=chunks)
    pipeline._generate = AsyncMock(side_effect=[("draft-A", []), ("draft-B", []), ("x", [])] * 2)

    revised = await pipeline._revise(
        _AGENTS[0], "q", chunks, own="draft-A", other="draft-B", other_name="Skeptic"
    )

    notes = pipeline._generate.call_args.kwargs["evidence_notes"]
    assert any("draft-A" in n for n in notes)
    assert any("draft-B" in n and "Skeptic" in n for n in notes)
    assert revised == "draft-A"


@pytest.mark.asyncio
async def test_rare_rag_routes_and_returns_answer_when_grounded():
    http = MagicMock()
    settings = MagicMock()
    settings.query_processor_url = "http://query-processor"
    settings.retrieval_url = "http://retrieval"
    settings.generation_url = "http://generation"
    pipeline = RareRagPipeline(http, settings)

    chunks = [{"chunk_id": "c1", "content": "text", "score": 0.9}]

    pipeline._triage = AsyncMock(return_value="vanilla")
    pipeline._retrieve = AsyncMock(return_value=chunks)
    pipeline._verify_claims = AsyncMock(return_value=0.9)

    from app.schemas.orchestrator_schemas import QueryResponse

    mock_sub_response = QueryResponse(
        conversation_id="conv-1", answer="good answer", citations=[], rag_mode="vanilla"
    )

    with patch("app.pipelines.rare_rag.RareRagPipeline._get_sub_pipeline") as mock_get:
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_sub_response)
        mock_get.return_value = mock_pipeline

        result = await pipeline.run(
            query="Is aspirin safe with warfarin?",
            project_id="proj-1",
            conversation_id="conv-1",
            conversation_history=[],
            rag_mode="rare_rag",
            top_k=5,
            alpha=0.5,
            rerank_top_n=3,
        )

    assert result.answer == "good answer"
    assert result.abstained is False


@pytest.mark.asyncio
async def test_rare_rag_abstains_when_grounding_too_low():
    http = MagicMock()
    settings = MagicMock()
    settings.query_processor_url = "http://query-processor"
    settings.retrieval_url = "http://retrieval"
    settings.generation_url = "http://generation"
    pipeline = RareRagPipeline(http, settings)

    chunks = [{"chunk_id": "c1", "content": "text", "score": 0.1}]

    pipeline._triage = AsyncMock(return_value="vanilla")
    pipeline._retrieve = AsyncMock(return_value=chunks)
    pipeline._verify_claims = AsyncMock(return_value=0.1)

    from app.schemas.orchestrator_schemas import QueryResponse

    mock_sub_response = QueryResponse(
        conversation_id="conv-1", answer="uncertain answer", citations=[], rag_mode="vanilla"
    )

    with patch("app.pipelines.rare_rag.RareRagPipeline._get_sub_pipeline") as mock_get:
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_sub_response)
        mock_get.return_value = mock_pipeline

        result = await pipeline.run(
            query="Is aspirin safe with warfarin?",
            project_id="proj-1",
            conversation_id="conv-1",
            conversation_history=[],
            rag_mode="rare_rag",
            top_k=5,
            alpha=0.5,
            rerank_top_n=3,
        )

    assert result.abstained is True
    assert "cannot provide" in result.answer.lower()
