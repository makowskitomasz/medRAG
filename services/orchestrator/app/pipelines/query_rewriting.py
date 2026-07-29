from collections.abc import AsyncGenerator

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse


class QueryRewritingPipeline(RagPipeline):
    async def _rewrite_query(self, query: str, history: list[dict]) -> str:
        context = " ".join(m["content"] for m in history[-4:]) if history else ""
        data = await self._tracked_post(
            f"{self.settings.query_processor_url}/rewrite",
            {"query": query, "context": context},
        )
        return data["rewritten_query"]

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
        rewritten = await self._rewrite_query(query, conversation_history)
        chunks = await self._retrieve(rewritten, project_id, top_k, alpha)
        reranked = await self._rerank(query, chunks, rerank_top_n)
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
            label="Rewriting the query",
            text="Reformulating the question using the conversation history…",
            duration_ms=0,
        )
        t0 = _time.monotonic()
        rewritten = await self._rewrite_query(query, conversation_history)
        yield self._sse_think(
            step=0,
            label="Rewritten query",
            text=rewritten,
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )

        yield self._sse_search_start()
        t1 = _time.monotonic()
        chunks = await self._retrieve(rewritten, project_id, top_k, alpha)
        reranked = await self._rerank(query, chunks, rerank_top_n)
        yield self._sse_search_done(reranked)
        yield self._sse_think(
            step=1,
            label="Retrieval and reranking",
            text=f"Retrieved {len(chunks)} fragments → selected top {len(reranked)}.",
            duration_ms=int((_time.monotonic() - t1) * 1000),
        )

        async for chunk in self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        ):
            yield chunk
