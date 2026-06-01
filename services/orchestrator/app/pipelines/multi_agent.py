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

    async def run_stream(  # type: ignore[override]
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
        import time as _time

        agent_names = ["Researcher", "Critic", "Editor"]
        agent_descs = [
            "Mechanism of action and pharmacokinetics",
            "Clinical risks, contraindications and adverse effects",
            "Dosing, monitoring and management guidelines",
        ]
        per_top_k = max(top_k // len(_AGENT_PERSPECTIVES), 3)

        # Stream each agent's search as a think step
        per_agent_results: list[list[dict]] = []
        for i, (pq, name, desc) in enumerate(
            zip(
                [p.format(query=query) for p in _AGENT_PERSPECTIVES],
                agent_names,
                agent_descs,
                strict=False,
            )
        ):
            yield self._sse_search_start()
            t0 = _time.monotonic()
            agent_chunks = await self._agent_retrieve(pq, project_id, per_top_k, alpha)
            per_agent_results.append(agent_chunks)
            yield self._sse_think(
                step=i,
                label=f"Agent: {name}",
                text=f"{desc}. Found {len(agent_chunks)} fragments.",
                duration_ms=int((_time.monotonic() - t0) * 1000),
            )

        # Aggregate + rerank
        seen: set[str] = set()
        merged: list[dict] = []
        for chunks in per_agent_results:
            for chunk in chunks:
                cid = chunk.get("chunk_id", "")
                if cid not in seen:
                    seen.add(cid)
                    merged.append(chunk)

        logger.info("multi_agent aggregation", total_unique_chunks=len(merged))
        t_rerank = _time.monotonic()
        reranked = await self._rerank(query, merged, rerank_top_n)
        yield self._sse_search_done(reranked)
        yield self._sse_think(
            step=len(_AGENT_PERSPECTIVES),
            label="Merging and reranking",
            text=f"Merged {len(merged)} unique fragments → selected top {len(reranked)}.",
            duration_ms=int((_time.monotonic() - t_rerank) * 1000),
        )

        async for chunk in self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        ):
            yield chunk
