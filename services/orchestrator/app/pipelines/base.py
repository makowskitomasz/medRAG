import json
import math
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx
from medrag_shared import get_logger

from app.schemas.orchestrator_schemas import Citation, QueryResponse

_logger = get_logger(__name__)

# Set-wise evidence selection (RARE-RAG, thesis §3.5): relevance/diversity trade-off
# and size of the final evidence set.
_MMR_LAMBDA = 0.5
_MMR_M = 3


class RagPipeline(ABC):
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        settings,  # type: ignore[type-arg]
        prompt_overrides: dict[str, str] | None = None,
    ) -> None:
        self.http = http_client
        self.settings = settings
        self.prompt_overrides: dict[str, str] = prompt_overrides or {}
        self.llm_model: str | None = None
        # Retrieval hops for iterative_multihop; overridden from project settings.
        self.max_hops: int = 3
        # When enabled, _rerank() prunes the shortlist with greedy set-wise selection.
        self.setwise_selection: bool = False
        self._last_chunks: list[dict] = []  # all reranked chunks passed to LLM
        self._last_input_tokens: int = 0
        self._last_output_tokens: int = 0
        # Highest `think` step index emitted so far — the generation service always
        # labels its chain-of-thought as step 0, which would overwrite the pipeline's
        # own steps in the UI, so it gets remapped past this watermark.
        self._max_step: int = -1
        # Shifts this pipeline's step numbering — set by a parent pipeline (RARE)
        # that delegates to a sub-pipeline after already emitting its own steps.
        self._step_base: int = 0

    @abstractmethod
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
    ) -> QueryResponse: ...

    @abstractmethod
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
    ) -> AsyncGenerator[str, None]: ...

    # ---- helpers ----

    @staticmethod
    def _sse(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    @staticmethod
    def _sse_search_start() -> str:
        return RagPipeline._sse({"type": "search", "status": "start"})

    @staticmethod
    def _sse_search_done(chunks: list[dict]) -> str:
        # Count how many selected chunks each document contributed, preserving rank order.
        hits: dict[str, int] = {}
        for c in chunks:
            name = c.get("filename") or c.get("metadata", {}).get("filename") or ""
            if name:
                hits[name] = hits.get(name, 0) + 1
        return RagPipeline._sse(
            {
                "type": "search",
                "status": "done",
                "count": len(chunks),
                "filenames": list(hits),
                "files": [{"name": name, "hits": n} for name, n in hits.items()],
            }
        )

    def _sse_think(
        self,
        step: int,
        label: str,
        text: str,
        duration_ms: int,
        agent: str | None = None,
    ) -> str:
        step += self._step_base
        self._max_step = max(self._max_step, step)
        event: dict = {
            "type": "think",
            "step": step,
            "label": label,
            "text": text,
            "durationMs": duration_ms,
        }
        if agent:
            event["agent"] = agent
        return self._sse(event)

    async def _retrieve(
        self,
        query: str,
        project_id: str,
        top_k: int,
        alpha: float,
        query_vector: list[float] | None = None,
    ) -> list[dict]:
        payload: dict = {"query": query, "project_id": project_id, "top_k": top_k, "alpha": alpha}
        if query_vector:
            payload["query_vector"] = query_vector
        resp = await self.http.post(f"{self.settings.retrieval_url}/retrieve", json=payload)
        resp.raise_for_status()
        return resp.json()["chunks"]

    async def _rerank(self, query: str, chunks: list[dict], top_n: int) -> list[dict]:
        if not chunks:
            return []
        payload = {"query": query, "chunks": chunks, "top_n": top_n}
        resp = await self.http.post(f"{self.settings.reranker_url}/rerank", json=payload)
        resp.raise_for_status()
        reranked: list[dict] = resp.json()["chunks"]
        if self.setwise_selection:
            return await self._setwise_select(reranked)
        return reranked

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self.http.post(f"{self.settings.embedding_url}/embed", json={"texts": texts})
        resp.raise_for_status()
        vectors: list[list[float]] = resp.json()["vectors"]
        return vectors

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
        return dot / norm if norm else 0.0

    async def _setwise_select(
        self, chunks: list[dict], m: int = _MMR_M, lam: float = _MMR_LAMBDA
    ) -> list[dict]:
        """Greedy complementarity-aware selection (thesis eq. 3.2–3.3).

        Picks m passages maximising `lam * relevance + (1 - lam) * complementarity`,
        where complementarity is 1 minus the maximum cosine similarity to the
        already-selected set. No LLM call.
        """
        if len(chunks) <= m:
            return chunks
        try:
            vectors = await self._embed([c["content"] for c in chunks])
        except Exception as exc:
            _logger.warning("set-wise selection fell back to top-m", error=str(exc))
            return chunks[:m]

        # Cross-encoder scores are unbounded logits; min-max normalise to [0, 1].
        raw = [float(c.get("score", 0.0)) for c in chunks]
        lo, hi = min(raw), max(raw)
        span = hi - lo
        relevance = [(s - lo) / span if span else 1.0 for s in raw]

        selected: list[int] = []
        while len(selected) < m:
            best_i, best_score = -1, -math.inf
            for i in range(len(chunks)):
                if i in selected:
                    continue
                comp = (
                    1.0 - max(self._cosine(vectors[i], vectors[j]) for j in selected)
                    if selected
                    else 1.0
                )
                score = lam * relevance[i] + (1.0 - lam) * comp
                if score > best_score:
                    best_i, best_score = i, score
            selected.append(best_i)

        _logger.info("set-wise selection", candidates=len(chunks), selected=m)
        return [chunks[i] for i in selected]

    async def _generate(
        self,
        query: str,
        chunks: list[dict],
        history: list[dict],
        evidence_notes: list[str] | None = None,
        task_instructions: str | None = None,
    ) -> tuple[str, list[Citation]]:
        self._last_chunks = chunks  # capture for eval contexts
        payload: dict = {
            "query": query,
            "chunks": chunks,
            "conversation_history": history,
            "prompt_overrides": self.prompt_overrides,
        }
        if evidence_notes:
            payload["evidence_notes"] = evidence_notes
        if task_instructions:
            payload["task_instructions"] = task_instructions
        if self.llm_model:
            payload["llm_model"] = self.llm_model
        resp = await self.http.post(f"{self.settings.generation_url}/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        citations = [Citation(**c) for c in data.get("citations", [])]
        self._last_input_tokens += data.get("input_tokens", 0)
        self._last_output_tokens += data.get("output_tokens", 0)
        return data["answer"], citations

    async def _tracked_post(self, url: str, payload: dict) -> dict:
        """HTTP POST that automatically accumulates LLM token usage from the response."""
        extra: dict = {}
        if self.llm_model:
            extra["llm_model"] = self.llm_model
        if self.prompt_overrides:
            extra["prompt_overrides"] = self.prompt_overrides
        if extra:
            payload = {**payload, **extra}
        resp = await self.http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        self._last_input_tokens += data.get("input_tokens", 0)
        self._last_output_tokens += data.get("output_tokens", 0)
        return data

    async def _extract(
        self,
        query: str,
        sub_question: str,
        chunks: list[dict],
        prior_findings: list[str] | None = None,
        next_question_draft: str | None = None,
    ) -> tuple[str, str]:
        """Summarise passages for one sub-question. Returns (finding, next_question)."""
        payload: dict = {
            "query": query,
            "sub_question": sub_question,
            "chunks": chunks,
            "prior_findings": prior_findings or [],
        }
        if next_question_draft:
            payload["next_question_draft"] = next_question_draft
        try:
            data = await self._tracked_post(f"{self.settings.generation_url}/extract", payload)
        except Exception as exc:
            _logger.warning("extraction failed", sub_question=sub_question, error=str(exc))
            return "No supporting evidence found.", next_question_draft or ""
        return data.get("finding", ""), data.get("next_question", "")

    async def _plan(self, query: str, max_steps: int = 4) -> list[dict]:
        """Planner agent: decompose the query into independent sub-tasks."""
        try:
            data = await self._tracked_post(
                f"{self.settings.query_processor_url}/plan",
                {"query": query, "max_steps": max_steps},
            )
        except Exception as exc:
            _logger.warning("planning failed, falling back to single step", error=str(exc))
            return [{"sub_task": query, "focus": ""}]
        steps: list[dict] = data.get("steps") or []
        return steps or [{"sub_task": query, "focus": ""}]

    async def _verify_claims(self, answer: str, chunks: list[dict]) -> float:
        """Claim-level grounding score in [0, 1] (thesis §3.6)."""
        payload: dict = {"answer": answer, "chunks": chunks}
        data = await self._tracked_post(f"{self.settings.generation_url}/verify_claims", payload)
        score = float(data.get("grounding_score", 1.0))
        _logger.info("grounding verification", n_claims=len(data.get("claims", [])), score=score)
        return score

    async def _evaluate_answer(self, query: str, answer: str, chunks: list[dict]) -> float:
        """Ask generation service to score answer sufficiency (0.0–1.0).

        Structured-output scoring is model-dependent and can fail (some providers
        return a bare number or an empty completion). A failed self-assessment must
        not fail the whole query, so it degrades to "sufficient".
        """
        payload: dict = {
            "query": query,
            "answer": answer,
            "chunks": chunks,
            "prompt_overrides": self.prompt_overrides,
        }
        if self.llm_model:
            payload["llm_model"] = self.llm_model
        try:
            data = await self._tracked_post(f"{self.settings.generation_url}/evaluate", payload)
        except Exception as exc:
            _logger.warning("answer evaluation failed, assuming sufficient", error=str(exc))
            return 1.0
        return float(data.get("score", 1.0))

    async def _stream_text(
        self,
        answer: str,
        citations: list[Citation],
        conversation_id: str,
        rag_mode: str,
    ) -> AsyncGenerator[str, None]:
        """Replay an already-generated answer as an SSE token stream."""
        for word in answer.split(" "):
            yield self._sse({"type": "token", "content": word + " "})
        yield self._sse(
            {
                "type": "citations",
                "citations": [c.model_dump() for c in citations],
                "conversation_id": conversation_id,
                "rag_mode": rag_mode,
            }
        )
        yield "data: [DONE]\n\n"

    async def _stream_generation(
        self,
        query: str,
        chunks: list[dict],
        conversation_history: list[dict],
        conversation_id: str,
        rag_mode: str,
        evidence_notes: list[str] | None = None,
        task_instructions: str | None = None,
    ) -> AsyncGenerator[str, None]:
        self._last_chunks = chunks
        payload: dict = {
            "query": query,
            "chunks": chunks,
            "conversation_history": conversation_history,
            "prompt_overrides": self.prompt_overrides,
        }
        if evidence_notes:
            payload["evidence_notes"] = evidence_notes
        if task_instructions:
            payload["task_instructions"] = task_instructions
        if self.llm_model:
            payload["llm_model"] = self.llm_model
        url = f"{self.settings.generation_url}/generate/stream"
        # Reserve one step index for the model's chain-of-thought so it appends
        # after the pipeline steps instead of replacing step 0.
        generation_step = self._max_step + 1

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
                        # Usage rides along on the final event; without recording
                        # it here every streamed answer was billed as zero tokens.
                        self._last_input_tokens += event.pop("input_tokens", 0)
                        self._last_output_tokens += event.pop("output_tokens", 0)
                    elif event.get("type") == "think":
                        event["step"] = generation_step
                    yield f"data: {json.dumps(event)}\n\n"

        yield "data: [DONE]\n\n"
