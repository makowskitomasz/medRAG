import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx
from medrag_shared import get_logger

from app.schemas.orchestrator_schemas import Citation, QueryResponse

logger = get_logger(__name__)


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
        payload = {"query": query, "chunks": chunks, "top_n": top_n}
        resp = await self.http.post(f"{self.settings.reranker_url}/rerank", json=payload)
        resp.raise_for_status()
        return resp.json()["chunks"]

    async def _generate(
        self, query: str, chunks: list[dict], history: list[dict]
    ) -> tuple[str, list[Citation]]:
        self._last_chunks = chunks  # capture for eval contexts
        payload: dict = {
            "query": query,
            "chunks": chunks,
            "conversation_history": history,
            "prompt_overrides": self.prompt_overrides,
        }
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
            logger.warning("answer evaluation failed, assuming sufficient", error=str(exc))
            return 1.0
        return float(data.get("score", 1.0))

    async def _stream_generation(
        self,
        query: str,
        chunks: list[dict],
        conversation_history: list[dict],
        conversation_id: str,
        rag_mode: str,
    ) -> AsyncGenerator[str, None]:
        payload: dict = {
            "query": query,
            "chunks": chunks,
            "conversation_history": conversation_history,
            "prompt_overrides": self.prompt_overrides,
        }
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
                    elif event.get("type") == "think":
                        event["step"] = generation_step
                    yield f"data: {json.dumps(event)}\n\n"

        yield "data: [DONE]\n\n"
