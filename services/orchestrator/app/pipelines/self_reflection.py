import time
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

_SUFFICIENCY_THRESHOLD = 0.7
_MAX_ITERATIONS = 2


class SelfReflectionPipeline(RagPipeline):
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
        current_query = query

        for iteration in range(_MAX_ITERATIONS):
            chunks = await self._retrieve(current_query, project_id, top_k, alpha)
            reranked = await self._rerank(query, chunks, rerank_top_n)
            answer, citations = await self._generate(query, reranked, conversation_history)

            score = await self._evaluate_answer(query, answer, reranked)
            logger.info(
                "self_reflection iteration",
                iteration=iteration + 1,
                score=score,
                sufficient=score >= _SUFFICIENCY_THRESHOLD,
            )

            if score >= _SUFFICIENCY_THRESHOLD:
                break

            if iteration < _MAX_ITERATIONS - 1:
                current_query = f"{query} (provide more detail and specific information)"

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

        current_query = query
        best_chunks: list[dict] = []

        for iteration in range(_MAX_ITERATIONS):
            iter_label = f"{iteration + 1}/{_MAX_ITERATIONS}"
            yield self._sse(
                "think",
                {
                    "step": f"Retrieval iteration {iter_label}",
                    "note": "evaluating answer sufficiency",
                },
            )
            yield self._sse("search", {"status": "searching", "query": current_query})

            chunks = await self._retrieve(current_query, project_id, top_k, alpha)
            yield self._sse("search", {"status": "reranking", "found": len(chunks)})

            reranked = await self._rerank(query, chunks, rerank_top_n)
            yield self._sse("search", {"status": "done", "kept": len(reranked)})
            best_chunks = reranked

            answer, _ = await self._generate(query, reranked, conversation_history)
            score = await self._evaluate_answer(query, answer, reranked)

            logger.info(
                "self_reflection iteration",
                iteration=iteration + 1,
                score=score,
                sufficient=score >= _SUFFICIENCY_THRESHOLD,
            )

            if score >= _SUFFICIENCY_THRESHOLD:
                yield self._sse(
                    "think",
                    {
                        "step": f"Iteration {iter_label} sufficient",
                        "note": f"score {score:.2f} ≥ {_SUFFICIENCY_THRESHOLD}",
                    },
                )
                break

            yield self._sse(
                "think",
                {
                    "step": f"Iteration {iter_label} insufficient",
                    "note": f"score {score:.2f} — retrying with expanded query",
                },
            )
            current_query = f"{query} (provide more detail and specific information)"

        async for event in self._timed_stream(
            query, best_chunks, conversation_history, conversation_id, rag_mode, t0
        ):
            yield event
