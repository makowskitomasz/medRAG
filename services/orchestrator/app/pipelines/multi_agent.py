import asyncio
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

# Each agent reformulates the query from a different angle to maximise recall diversity.
_AGENT_PERSPECTIVES = [
    "mechanism of action and pharmacokinetics: {query}",
    "clinical risks, contraindications and adverse effects: {query}",
    "dosing, monitoring and management guidelines: {query}",
]


class MultiAgentPipeline(RagPipeline):
    async def _agent_retrieve(
        self,
        perspective_query: str,
        project_id: str,
        top_k: int,
        alpha: float,
    ) -> list[dict]:
        try:
            return await self._retrieve(perspective_query, project_id, top_k, alpha)
        except Exception as exc:
            logger.warning("agent retrieval failed", query=perspective_query, error=str(exc))
            return []

    async def _aggregate_chunks(
        self,
        query: str,
        project_id: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> list[dict]:
        perspective_queries = [p.format(query=query) for p in _AGENT_PERSPECTIVES]
        per_agent_top_k = max(top_k // len(perspective_queries), 3)

        results = await asyncio.gather(
            *[
                self._agent_retrieve(pq, project_id, per_agent_top_k, alpha)
                for pq in perspective_queries
            ]
        )

        seen: set[str] = set()
        merged: list[dict] = []
        for chunks in results:
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id not in seen:
                    seen.add(chunk_id)
                    merged.append(chunk)

        logger.info("multi_agent aggregation", total_unique_chunks=len(merged))
        return await self._rerank(query, merged, rerank_top_n)

    async def run(
        self,
        query: str,
        project_id: str,
        conversation_id: str,
        conversation_history: list[dict],
        rag_mode: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> QueryResponse:
        reranked = await self._aggregate_chunks(query, project_id, top_k, alpha, rerank_top_n)
        answer, citations = await self._generate(query, reranked, conversation_history)
        return QueryResponse(
            conversation_id=conversation_id,
            answer=answer,
            citations=citations,
            rag_mode=rag_mode,
        )

    async def run_stream(
        self,
        query: str,
        project_id: str,
        conversation_id: str,
        conversation_history: list[dict],
        rag_mode: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> AsyncGenerator[str, None]:
        reranked = await self._aggregate_chunks(query, project_id, top_k, alpha, rerank_top_n)
        return self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        )
