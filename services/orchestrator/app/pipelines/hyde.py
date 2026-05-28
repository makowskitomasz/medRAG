import time
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
        yield self._sse(
            "think", {"step": "Generating hypothetical document", "note": "HyDE expansion"}
        )

        hypothetical_doc = await self._hyde_query(query)
        retrieval_query = f"{query}\n\n{hypothetical_doc}"

        yield self._sse("search", {"status": "searching", "query": query})
        chunks = await self._retrieve(retrieval_query, project_id, top_k, alpha)
        yield self._sse("search", {"status": "reranking", "found": len(chunks)})

        reranked = await self._rerank(query, chunks, rerank_top_n)
        yield self._sse("search", {"status": "done", "kept": len(reranked)})

        async for event in self._timed_stream(
            query, reranked, conversation_history, conversation_id, rag_mode, t0
        ):
            yield event
