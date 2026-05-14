import json
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
        hypothetical_doc = await self._hyde_query(query)
        retrieval_query = f"{query}\n\n{hypothetical_doc}"
        chunks = await self._retrieve(retrieval_query, project_id, top_k, alpha)
        reranked = await self._rerank(query, chunks, rerank_top_n)

        payload = {"query": query, "chunks": reranked, "conversation_history": conversation_history}
        url = await self._generate_stream_url()

        async with self.http.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    event = json.loads(raw)
                    if event.get("type") == "citations":
                        event["conversation_id"] = conversation_id
                        event["rag_mode"] = rag_mode
                    yield f"data: {json.dumps(event)}\n\n"

        yield "data: [DONE]\n\n"
