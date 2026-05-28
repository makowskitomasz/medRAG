import time
from collections.abc import AsyncGenerator

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse


class QueryRewritingPipeline(RagPipeline):
    async def _rewrite_query(self, query: str, history: list[dict]) -> str:
        context = " ".join(m["content"] for m in history[-4:]) if history else ""
        resp = await self.http.post(
            f"{self.settings.query_processor_url}/rewrite",
            json={"query": query, "context": context},
        )
        resp.raise_for_status()
        return resp.json()["rewritten_query"]

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
        yield self._sse("think", {"step": "Rewriting query", "note": "contextual reformulation"})

        rewritten = await self._rewrite_query(query, conversation_history)
        yield self._sse("search", {"status": "searching", "query": rewritten})

        chunks = await self._retrieve(rewritten, project_id, top_k, alpha)
        yield self._sse("search", {"status": "reranking", "found": len(chunks)})

        reranked = await self._rerank(query, chunks, rerank_top_n)
        yield self._sse("search", {"status": "done", "kept": len(reranked)})

        async for event in self._timed_stream(
            query, reranked, conversation_history, conversation_id, rag_mode, t0
        ):
            yield event
