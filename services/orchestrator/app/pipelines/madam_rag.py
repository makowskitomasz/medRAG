import asyncio
import time
from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import Citation, QueryResponse

logger = get_logger(__name__)

# Two agents argue the question from opposing angles, then a judge reconciles them.
_AGENTS = [
    {
        "name": "Advocate",
        "perspective": "supporting evidence, established benefits and mechanisms: {query}",
        "stance": (
            "You argue from the evidence that supports an interaction being well-characterised "
            "and clinically manageable."
        ),
    },
    {
        "name": "Skeptic",
        "perspective": "risks, contraindications, and opposing or conflicting evidence: {query}",
        "stance": (
            "You argue from the evidence that emphasises risk, contraindication, uncertainty "
            "and conflicting findings."
        ),
    },
]

_CANDIDATE_INSTRUCTIONS = (
    "{stance}\n"
    "Answer the question strictly from the passages below, citing [SOURCE_N]. State the "
    "claims your passages actually support. If your passages do not settle the question, "
    "say so rather than filling the gap from prior knowledge."
)

_REVISION_INSTRUCTIONS = (
    "{stance}\n"
    "The notes below contain your own draft answer and the opposing agent's answer. "
    "Revise your answer: concede points the other agent grounds in evidence, keep the claims "
    "your own passages support, and name explicitly any point where the two of you disagree. "
    "Answer from the passages below, citing [SOURCE_N]."
)

_JUDGE_INSTRUCTIONS = (
    "Two agents debated this question from opposing angles; the notes below are their revised "
    "answers. Act as judge: produce the consensus answer. Where the agents agree and the "
    "passages support them, state the conclusion directly. Where they disagree, present both "
    "positions, flag the uncertainty explicitly, and recommend consulting a specialist. "
    "Cite [SOURCE_N] passages; do not introduce claims absent from the passages."
)


class MadamRagPipeline(RagPipeline):
    """Multi-agent debate: candidate answers, one revision round, then a judge synthesises."""

    async def _agent_retrieve(
        self, agent: dict, query: str, project_id: str, top_k: int, alpha: float, top_n: int
    ) -> list[dict]:
        formatted = agent["perspective"].format(query=query)
        try:
            chunks = await self._retrieve(formatted, project_id, top_k, alpha)
        except Exception as exc:
            logger.warning("madam agent retrieval failed", agent=agent["name"], error=str(exc))
            return []
        return await self._rerank(formatted, chunks, top_n) if chunks else []

    async def _candidate(
        self, agent: dict, query: str, chunks: list[dict]
    ) -> tuple[str, list[Citation]]:
        answer, citations = await self._generate(
            query,
            chunks,
            [],
            task_instructions=_CANDIDATE_INSTRUCTIONS.format(stance=agent["stance"]),
        )
        return answer, citations

    async def _revise(
        self, agent: dict, query: str, chunks: list[dict], own: str, other: str, other_name: str
    ) -> str:
        answer, _ = await self._generate(
            query,
            chunks,
            [],
            evidence_notes=[f"Your draft answer: {own}", f"{other_name}'s answer: {other}"],
            task_instructions=_REVISION_INSTRUCTIONS.format(stance=agent["stance"]),
        )
        return answer

    async def _debate(
        self, query: str, project_id: str, top_k: int, alpha: float, rerank_top_n: int
    ) -> tuple[list[str], list[dict]]:
        """Returns (revised agent answers, merged evidence for the judge)."""
        per_agent_top_k = max(top_k // len(_AGENTS), 3)
        per_agent_top_n = max(rerank_top_n // len(_AGENTS), 2)

        agent_chunks = await asyncio.gather(
            *[
                self._agent_retrieve(a, query, project_id, per_agent_top_k, alpha, per_agent_top_n)
                for a in _AGENTS
            ]
        )
        candidates = await asyncio.gather(
            *[self._candidate(a, query, c) for a, c in zip(_AGENTS, agent_chunks, strict=True)]
        )
        drafts = [answer for answer, _ in candidates]

        revised = await asyncio.gather(
            *[
                self._revise(
                    agent,
                    query,
                    agent_chunks[i],
                    drafts[i],
                    drafts[1 - i],
                    _AGENTS[1 - i]["name"],
                )
                for i, agent in enumerate(_AGENTS)
            ]
        )
        logger.info("madam_rag debate round complete", n_agents=len(_AGENTS))

        collected: dict[str, dict] = {}
        for chunks in agent_chunks:
            for chunk in chunks:
                collected.setdefault(chunk.get("chunk_id", ""), chunk)
        evidence = await self._rerank(query, list(collected.values()), rerank_top_n)
        return list(revised), evidence

    @staticmethod
    def _judge_notes(revised: list[str]) -> list[str]:
        return [f"{a['name']}'s revised answer: {r}" for a, r in zip(_AGENTS, revised, strict=True)]

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
        revised, evidence = await self._debate(query, project_id, top_k, alpha, rerank_top_n)
        answer, citations = await self._generate(
            query,
            evidence,
            conversation_history,
            evidence_notes=self._judge_notes(revised),
            task_instructions=_JUDGE_INSTRUCTIONS,
        )
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
        t0 = time.monotonic()
        yield self._sse_search_start()
        revised, evidence = await self._debate(query, project_id, top_k, alpha, rerank_top_n)
        yield self._sse_search_done(evidence)

        for i, (agent, answer) in enumerate(zip(_AGENTS, revised, strict=True)):
            yield self._sse_think(
                step=i,
                label=f"Agent: {agent['name']}",
                text=answer,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        async for event in self._stream_generation(
            query,
            evidence,
            conversation_history,
            conversation_id,
            rag_mode,
            evidence_notes=self._judge_notes(revised),
            task_instructions=_JUDGE_INSTRUCTIONS,
        ):
            yield event
