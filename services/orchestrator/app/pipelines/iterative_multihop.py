import asyncio
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

_MAX_SUB_QUESTIONS = 4


class IterativeMultiHopPipeline(RagPipeline):
    async def _decompose(self, query: str) -> list[str]:
        resp = await self.http.post(
            f"{self.settings.query_processor_url}/decompose",
            json={"query": query},
        )
        resp.raise_for_status()
        sub_questions = resp.json().get("sub_questions", [query])
        return sub_questions[:_MAX_SUB_QUESTIONS]

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
        reranked = await self._get_chunks(query, project_id, top_k, alpha, rerank_top_n)
        return self._stream_generation(
            query, reranked, conversation_history, conversation_id, rag_mode
        )
