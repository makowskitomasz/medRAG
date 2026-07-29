from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

# Chunks with score below this are considered low-relevance.
_RELEVANCE_THRESHOLD = 0.3
# Minimum fraction of chunks that must be relevant; otherwise trigger fallback.
_MIN_RELEVANT_FRACTION = 0.3


class CorrectiveRagPipeline(RagPipeline):
    def _filter_relevant(self, chunks: list[dict]) -> list[dict]:
        return [c for c in chunks if (c.get("score") or 0.0) >= _RELEVANCE_THRESHOLD]

    async def _fallback_retrieve(
        self,
        query: str,
        project_id: str,
        top_k: int,
        alpha: float,
    ) -> list[dict]:
        # Fallback: broaden search with lower alpha (more BM25) and larger top_k.
        logger.info("corrective_rag triggering fallback retrieval", query=query)
        fallback_alpha = max(alpha - 0.3, 0.0)
        return await self._retrieve(query, project_id, top_k * 2, fallback_alpha)

    async def _get_chunks(
        self,
        query: str,
        project_id: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> list[dict]:
        chunks = await self._retrieve(query, project_id, top_k, alpha)
        relevant = self._filter_relevant(chunks)
        relevant_fraction = len(relevant) / len(chunks) if chunks else 0.0

        if relevant_fraction < _MIN_RELEVANT_FRACTION:
            logger.info(
                "corrective_rag low relevance",
                relevant=len(relevant),
                total=len(chunks),
                fraction=relevant_fraction,
            )
            fallback_chunks = await self._fallback_retrieve(query, project_id, top_k, alpha)
            # Merge original + fallback, deduplicate by chunk_id.
            seen: set[str] = set()
            merged: list[dict] = []
            for c in chunks + fallback_chunks:
                cid = c.get("chunk_id", "")
                if cid not in seen:
                    seen.add(cid)
                    merged.append(c)
            chunks = merged

        return await self._rerank(query, chunks, rerank_top_n)

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

        yield self._sse_search_start()
        t0 = _time.monotonic()
        chunks = await self._retrieve(query, project_id, top_k, alpha)
        relevant = self._filter_relevant(chunks)
        relevant_fraction = len(relevant) / len(chunks) if chunks else 0.0
        yield self._sse_think(
            step=0,
            label="Relevance check",
            text=(
                f"{len(relevant)} of {len(chunks)} fragments scored above "
                f"{_RELEVANCE_THRESHOLD} ({relevant_fraction:.0%} relevant)."
            ),
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )

        step = 1
        if relevant_fraction < _MIN_RELEVANT_FRACTION:
            logger.info(
                "corrective_rag low relevance",
                relevant=len(relevant),
                total=len(chunks),
                fraction=relevant_fraction,
            )
            t1 = _time.monotonic()
            fallback_chunks = await self._fallback_retrieve(query, project_id, top_k, alpha)
            seen: set[str] = set()
            merged: list[dict] = []
            for c in chunks + fallback_chunks:
                cid = c.get("chunk_id", "")
                if cid not in seen:
                    seen.add(cid)
                    merged.append(c)
            yield self._sse_think(
                step=step,
                label="Corrective fallback",
                text=(
                    f"Relevance below {_MIN_RELEVANT_FRACTION:.0%} — broadened the search "
                    f"(more keyword weight, doubled top_k) and added "
                    f"{len(merged) - len(chunks)} new fragments."
                ),
                duration_ms=int((_time.monotonic() - t1) * 1000),
            )
            chunks = merged
            step += 1
        else:
            yield self._sse_think(
                step=step,
                label="No correction needed",
                text="Retrieval quality is sufficient — skipping the fallback search.",
                duration_ms=0,
            )
            step += 1

        t2 = _time.monotonic()
        reranked = await self._rerank(query, chunks, rerank_top_n)
        yield self._sse_search_done(reranked)
        yield self._sse_think(
            step=step,
            label="Reranking",
            text=f"Reranked {len(chunks)} fragments → selected top {len(reranked)}.",
            duration_ms=int((_time.monotonic() - t2) * 1000),
        )

        async for chunk in self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        ):
            yield chunk
