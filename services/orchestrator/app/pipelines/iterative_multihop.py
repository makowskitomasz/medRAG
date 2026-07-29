import asyncio
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

_MAX_SUB_QUESTIONS = 4


class IterativeMultiHopPipeline(RagPipeline):
    async def _decompose(self, query: str) -> list[str]:
        data = await self._tracked_post(
            f"{self.settings.query_processor_url}/decompose",
            {"query": query},
        )
        return data.get("sub_questions", [query])[:_MAX_SUB_QUESTIONS]

    async def _retrieve_for_subquestion(
        self, sub_q: str, project_id: str, top_k: int, alpha: float
    ) -> list[dict]:
        try:
            return await self._retrieve(sub_q, project_id, top_k, alpha)
        except Exception as exc:
            logger.warning("multihop sub-question retrieval failed", sub_q=sub_q, error=str(exc))
            return []

    async def _get_chunks(
        self, query: str, project_id: str, top_k: int, alpha: float, rerank_top_n: int
    ) -> list[dict]:
        sub_questions = await self._decompose(query)
        logger.info("iterative_multihop decomposed", n_sub_questions=len(sub_questions))

        per_hop_top_k = max(top_k // len(sub_questions), 3)
        results = await asyncio.gather(
            *[
                self._retrieve_for_subquestion(sq, project_id, per_hop_top_k, alpha)
                for sq in sub_questions
            ]
        )

        seen: set[str] = set()
        merged: list[dict] = []
        for chunks in results:
            for chunk in chunks:
                cid = chunk.get("chunk_id", "")
                if cid not in seen:
                    seen.add(cid)
                    merged.append(chunk)

        logger.info("iterative_multihop aggregated", unique_chunks=len(merged))
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
        reranked = await self._get_chunks(query, project_id, top_k, alpha, rerank_top_n)
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

        yield self._sse_think(
            step=0,
            label="Decomposing the question",
            text="Splitting the question into independently answerable sub-questions…",
            duration_ms=0,
        )
        t0 = _time.monotonic()
        sub_questions = await self._decompose(query)
        logger.info("iterative_multihop decomposed", n_sub_questions=len(sub_questions))
        yield self._sse_think(
            step=0,
            label=f"Decomposition — {len(sub_questions)} sub-questions",
            text="\n".join(f"{i + 1}. {sq}" for i, sq in enumerate(sub_questions)),
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )

        # Hops run sequentially here (unlike run()) so each one can be reported live.
        yield self._sse_search_start()
        per_hop_top_k = max(top_k // len(sub_questions), 3)
        results: list[list[dict]] = []
        for i, sub_q in enumerate(sub_questions):
            t_hop = _time.monotonic()
            hop_chunks = await self._retrieve_for_subquestion(
                sub_q, project_id, per_hop_top_k, alpha
            )
            results.append(hop_chunks)
            yield self._sse_think(
                step=i + 1,
                label=f"Hop {i + 1}/{len(sub_questions)}",
                text=f"{sub_q} → found {len(hop_chunks)} fragments.",
                duration_ms=int((_time.monotonic() - t_hop) * 1000),
            )

        seen: set[str] = set()
        merged: list[dict] = []
        for chunks in results:
            for chunk in chunks:
                cid = chunk.get("chunk_id", "")
                if cid not in seen:
                    seen.add(cid)
                    merged.append(chunk)

        logger.info("iterative_multihop aggregated", unique_chunks=len(merged))
        t_rerank = _time.monotonic()
        reranked = await self._rerank(query, merged, rerank_top_n)
        yield self._sse_search_done(reranked)
        yield self._sse_think(
            step=len(sub_questions) + 1,
            label="Merging and reranking",
            text=f"Merged {len(merged)} unique fragments → selected top {len(reranked)}.",
            duration_ms=int((_time.monotonic() - t_rerank) * 1000),
        )

        async for chunk in self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        ):
            yield chunk
