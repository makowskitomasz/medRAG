import asyncio
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

_CONFLICT_THRESHOLD = 0.6

_PRO_PERSPECTIVE = "supporting evidence and benefits: {query}"
_COUNTER_PERSPECTIVE = "risks, contraindications, and opposing evidence: {query}"
_CONFLICT_PERSPECTIVE = "conflicting or uncertain evidence: {query}"

_PERSPECTIVES = [_PRO_PERSPECTIVE, _COUNTER_PERSPECTIVE, _CONFLICT_PERSPECTIVE]


class MadamRagPipeline(RagPipeline):
    async def _detect_conflict(self, chunks: list[dict]) -> tuple[bool, float]:
        """Returns (has_conflict, confidence)."""
        try:
            data = await self._tracked_post(
                f"{self.settings.generation_url}/detect_conflict",
                {"chunks": chunks, "prompt_overrides": self.prompt_overrides},
            )
            return bool(data.get("has_conflict", False)), float(data.get("confidence", 0.5))
        except Exception as exc:
            logger.warning("conflict detection failed", error=str(exc))
            return False, 0.0

    async def _perspective_retrieve(
        self, perspective: str, query: str, project_id: str, top_k: int, alpha: float
    ) -> list[dict]:
        formatted = perspective.format(query=query)
        try:
            return await self._retrieve(formatted, project_id, top_k, alpha)
        except Exception as exc:
            logger.warning("madam perspective retrieval failed", error=str(exc))
            return []

    async def _get_chunks(
        self, query: str, project_id: str, top_k: int, alpha: float, rerank_top_n: int
    ) -> tuple[list[dict], bool]:
        per_perspective_top_k = max(top_k // len(_PERSPECTIVES), 3)

        results = await asyncio.gather(
            *[
                self._perspective_retrieve(p, query, project_id, per_perspective_top_k, alpha)
                for p in _PERSPECTIVES
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

        has_conflict, confidence = await self._detect_conflict(merged[:10])
        conflict_detected = has_conflict and confidence >= _CONFLICT_THRESHOLD
        logger.info(
            "madam_rag conflict detection",
            has_conflict=has_conflict,
            confidence=confidence,
            conflict_detected=conflict_detected,
        )

        reranked = await self._rerank(query, merged, rerank_top_n)
        return reranked, conflict_detected

    def _build_cautious_query(self, query: str) -> str:
        return (
            f"{query}\n\n"
            "NOTE: Sources contain conflicting information. "
            "Present all perspectives, highlight uncertainties, "
            "and recommend consulting a specialist."
        )

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
        reranked, conflict_detected = await self._get_chunks(
            query, project_id, top_k, alpha, rerank_top_n
        )
        effective_query = self._build_cautious_query(query) if conflict_detected else query
        answer, citations = await self._generate(effective_query, reranked, conversation_history)
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
        reranked, conflict_detected = await self._get_chunks(
            query, project_id, top_k, alpha, rerank_top_n
        )
        effective_query = self._build_cautious_query(query) if conflict_detected else query
        return self._stream_generation(
            effective_query, reranked, conversation_history, conversation_id, rag_mode
        )
