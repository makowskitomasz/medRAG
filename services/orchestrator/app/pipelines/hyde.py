from collections.abc import AsyncGenerator

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse


class HydePipeline(RagPipeline):
    async def _hyde_query(self, query: str) -> str:
        resp = await self.http.post(
            f"{self.settings.query_processor_url}/hyde",
            json={"query": query},
        )
        resp.raise_for_status()
        return resp.json()["hypothetical_document"]

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
        hypothetical_doc = await self._hyde_query(query)
        retrieval_query = f"{query}\n\n{hypothetical_doc}"
        chunks = await self._retrieve(retrieval_query, project_id, top_k, alpha)
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

        # think: generate hypothetical document
        yield self._sse_think(
            step=0,
            label="Generowanie dokumentu hipotetycznego",
            text="Tworzę hipotetyczną odpowiedź do wzbogacenia wyszukiwania…",
            duration_ms=0,
        )
        t0 = _time.monotonic()
        hypothetical_doc = await self._hyde_query(query)
        yield self._sse_think(
            step=0,
            label="Generowanie dokumentu hipotetycznego",
            text=hypothetical_doc[:300] + ("…" if len(hypothetical_doc) > 300 else ""),
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )

        # search with enriched query
        yield self._sse_search_start()
        retrieval_query = f"{query}\n\n{hypothetical_doc}"
        chunks = await self._retrieve(retrieval_query, project_id, top_k, alpha)
        reranked = await self._rerank(query, chunks, rerank_top_n)
        yield self._sse_search_done(reranked)

        async for chunk in self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        ):
            yield chunk
