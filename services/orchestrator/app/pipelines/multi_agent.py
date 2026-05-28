import asyncio
import time
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

_AGENT_PERSPECTIVES = [
    ("Researcher", "mechanism of action and pharmacokinetics: {query}"),
    ("Critic", "clinical risks, contraindications and adverse effects: {query}"),
    ("Editor", "dosing, monitoring and management guidelines: {query}"),
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
        perspective_queries = [p.format(query=query) for _, p in _AGENT_PERSPECTIVES]
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
        t0 = time.monotonic()
        yield self._sse("meta", {"conversationId": conversation_id, "ragMode": rag_mode})

        per_agent_top_k = max(top_k // len(_AGENT_PERSPECTIVES), 3)

        for agent_name, perspective_template in _AGENT_PERSPECTIVES:
            pq = perspective_template.format(query=query)
            yield self._sse(
                "think",
                {"step": f"Agent: {agent_name}", "note": pq},
            )

        yield self._sse("search", {"status": "searching", "query": query})

        perspective_queries = [p.format(query=query) for _, p in _AGENT_PERSPECTIVES]
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

        yield self._sse("search", {"status": "reranking", "found": len(merged)})
        logger.info("multi_agent aggregation", total_unique_chunks=len(merged))

        reranked = await self._rerank(query, merged, rerank_top_n)
        yield self._sse("search", {"status": "done", "kept": len(reranked)})

        async for event in self._timed_stream(
            query, reranked, conversation_history, conversation_id, rag_mode, t0
        ):
            yield event
