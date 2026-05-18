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
