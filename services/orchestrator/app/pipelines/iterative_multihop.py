import time
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import Citation, QueryResponse

logger = get_logger(__name__)

_SYNTHESIS_INSTRUCTIONS = (
    "The retrieval chain below ran one hop per sub-question. The intermediate findings "
    "summarise what each hop established; the passages are the evidence they came from. "
    "Chain the findings into a single answer to the question, citing [SOURCE_N] passages. "
    "If a finding says no evidence was found, do not fill the gap from prior knowledge."
)


class IterativeMultiHopPipeline(RagPipeline):
    """Chain-of-retrieval: each hop retrieves using what the previous hops established."""

    async def _decompose(self, query: str) -> list[str]:
        data = await self._tracked_post(
            f"{self.settings.query_processor_url}/decompose",
            {"query": query},
        )
        sub_questions = data.get("sub_questions") or [query]
        return sub_questions[: self.max_hops]

    async def _retrieve_hop(
        self, sub_q: str, project_id: str, top_k: int, alpha: float, rerank_top_n: int
    ) -> list[dict]:
        try:
            chunks = await self._retrieve(sub_q, project_id, top_k, alpha)
        except Exception as exc:
            logger.warning("multihop hop retrieval failed", sub_q=sub_q, error=str(exc))
            return []
        return await self._rerank(sub_q, chunks, rerank_top_n) if chunks else []

    async def _run_chain(
        self, query: str, project_id: str, top_k: int, alpha: float, rerank_top_n: int
    ) -> tuple[list[dict], list[str]]:
        """Sequential hops. Returns (evidence chunks for synthesis, findings)."""
        sub_questions = await self._decompose(query)
        logger.info("iterative_multihop decomposed", n_hops=len(sub_questions))

        per_hop_top_k = max(top_k // len(sub_questions), 5)
        findings: list[str] = []
        collected: dict[str, dict] = {}
        current_q = sub_questions[0]

        for hop, _ in enumerate(sub_questions):
            hop_chunks = await self._retrieve_hop(
                current_q, project_id, per_hop_top_k, alpha, rerank_top_n
            )
            for chunk in hop_chunks:
                collected.setdefault(chunk.get("chunk_id", ""), chunk)

            draft = sub_questions[hop + 1] if hop + 1 < len(sub_questions) else None
            finding, next_q = await self._extract(
                query=query,
                sub_question=current_q,
                chunks=hop_chunks,
                prior_findings=findings,
                next_question_draft=draft,
            )
            findings.append(finding)
            logger.info("iterative_multihop hop done", hop=hop + 1, sub_question=current_q)

            if draft is None:
                break
            current_q = next_q or draft

        evidence = await self._rerank(query, list(collected.values()), rerank_top_n)
        return evidence, findings

    async def _synthesise(
        self, query: str, evidence: list[dict], findings: list[str], history: list[dict]
    ) -> tuple[str, list[Citation]]:
        return await self._generate(
            query,
            evidence,
            history,
            evidence_notes=findings,
            task_instructions=_SYNTHESIS_INSTRUCTIONS,
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
        evidence, findings = await self._run_chain(query, project_id, top_k, alpha, rerank_top_n)
        answer, citations = await self._synthesise(query, evidence, findings, conversation_history)
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
        # Decomposition is a full LLM call — announce it so the panel is not blank.
        yield self._sse_think(
            step=0,
            label="Decomposing the question",
            text="Splitting the question into sub-questions to chain retrieval over…",
            duration_ms=0,
        )
        sub_questions = await self._decompose(query)
        per_hop_top_k = max(top_k // len(sub_questions), 5)
        findings: list[str] = []
        collected: dict[str, dict] = {}
        current_q = sub_questions[0]

        for hop, _ in enumerate(sub_questions):
            yield self._sse_search_start()
            t0 = time.monotonic()
            hop_chunks = await self._retrieve_hop(
                current_q, project_id, per_hop_top_k, alpha, rerank_top_n
            )
            for chunk in hop_chunks:
                collected.setdefault(chunk.get("chunk_id", ""), chunk)
            yield self._sse_search_done(hop_chunks)

            draft = sub_questions[hop + 1] if hop + 1 < len(sub_questions) else None
            finding, next_q = await self._extract(
                query=query,
                sub_question=current_q,
                chunks=hop_chunks,
                prior_findings=findings,
                next_question_draft=draft,
            )
            findings.append(finding)
            yield self._sse_think(
                step=hop,
                label=f"Hop {hop + 1}: {current_q}",
                text=finding,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

            if draft is None:
                break
            current_q = next_q or draft

        evidence = await self._rerank(query, list(collected.values()), rerank_top_n)
        async for event in self._stream_generation(
            query,
            evidence,
            conversation_history,
            conversation_id,
            rag_mode,
            evidence_notes=findings,
            task_instructions=_SYNTHESIS_INSTRUCTIONS,
        ):
            yield event
