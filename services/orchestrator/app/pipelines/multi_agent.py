import asyncio
import time
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import Citation, QueryResponse

logger = get_logger(__name__)

_MAX_STEPS = 3

_SYNTHESIS_INSTRUCTIONS = (
    "A planner split the question into sub-tasks and an executor agent resolved each one "
    "against its own retrieved passages. The findings below are those executors' reports; "
    "the passages are the evidence behind them. Compose one coherent answer from the "
    "findings, citing [SOURCE_N] passages. Where a finding reports no evidence, say so "
    "instead of relying on prior knowledge."
)


class MultiAgentPipeline(RagPipeline):
    """MA-RAG: planner decomposes, executor agents resolve sub-tasks, QA agent synthesises."""

    async def _execute_step(
        self,
        query: str,
        step: dict,
        project_id: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> tuple[str, list[dict]]:
        """One executor agent: retrieve for its sub-task and report a focused finding."""
        sub_task = step.get("sub_task", query)
        focus = step.get("focus") or ""
        retrieval_query = f"{sub_task} {focus}".strip()
        try:
            chunks = await self._retrieve(retrieval_query, project_id, top_k, alpha)
        except Exception as exc:
            logger.warning("executor retrieval failed", sub_task=sub_task, error=str(exc))
            return "No supporting evidence found.", []

        chunks = await self._rerank(retrieval_query, chunks, rerank_top_n) if chunks else []
        finding, _ = await self._extract(query=query, sub_question=sub_task, chunks=chunks)
        return finding, chunks

    async def _run_agents(
        self, query: str, project_id: str, top_k: int, alpha: float, rerank_top_n: int
    ) -> tuple[list[dict], list[str], list[dict]]:
        """Returns (plan steps, executor findings, evidence chunks for synthesis)."""
        steps = await self._plan(query, max_steps=_MAX_STEPS)
        logger.info("multi_agent plan", n_steps=len(steps))

        per_agent_top_k = max(top_k // len(steps), 3)
        per_agent_top_n = max(rerank_top_n // len(steps), 2)

        results = await asyncio.gather(
            *[
                self._execute_step(query, s, project_id, per_agent_top_k, alpha, per_agent_top_n)
                for s in steps
            ]
        )

        findings = [finding for finding, _ in results]
        collected: dict[str, dict] = {}
        for _, chunks in results:
            for chunk in chunks:
                collected.setdefault(chunk.get("chunk_id", ""), chunk)

        evidence = await self._rerank(query, list(collected.values()), rerank_top_n)
        return steps, findings, evidence

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
        _, findings, evidence = await self._run_agents(
            query, project_id, top_k, alpha, rerank_top_n
        )
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
        yield self._sse_think(
            step=0,
            label="Planner",
            text="Breaking the question into sub-tasks…",
            duration_ms=0,
            agent="planner",
        )
        t0 = time.monotonic()
        steps = await self._plan(query, max_steps=_MAX_STEPS)
        yield self._sse_think(
            step=0,
            label="Planner",
            text="Sub-tasks: " + "; ".join(s.get("sub_task", "") for s in steps),
            duration_ms=int((time.monotonic() - t0) * 1000),
            agent="planner",
        )

        per_agent_top_k = max(top_k // len(steps), 3)
        per_agent_top_n = max(rerank_top_n // len(steps), 2)
        findings: list[str] = []
        collected: dict[str, dict] = {}

        for i, step in enumerate(steps):
            yield self._sse_search_start()
            t_step = time.monotonic()
            finding, chunks = await self._execute_step(
                query, step, project_id, per_agent_top_k, alpha, per_agent_top_n
            )
            for chunk in chunks:
                collected.setdefault(chunk.get("chunk_id", ""), chunk)
            findings.append(finding)
            yield self._sse_search_done(chunks)
            yield self._sse_think(
                step=i + 1,
                label=f"Executor {i + 1}: {step.get('sub_task', '')}",
                text=finding,
                duration_ms=int((time.monotonic() - t_step) * 1000),
                agent="executor",
            )

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
