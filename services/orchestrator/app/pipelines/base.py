import json
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx

from app.schemas.orchestrator_schemas import Citation, QueryResponse


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

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # ------------------------------------------------------------------ backend calls

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
        payload = {
            "query": query,
            "chunks": chunks,
            "conversation_history": history,
            "prompt_overrides": self.prompt_overrides,
        }
        resp = await self.http.post(f"{self.settings.generation_url}/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        citations = [Citation(**c) for c in data.get("citations", [])]
        return data["answer"], citations

    async def _evaluate_answer(self, query: str, answer: str, chunks: list[dict]) -> float:
        """Ask generation service to score answer sufficiency (0.0–1.0)."""
        payload = {
            "query": query,
            "answer": answer,
            "chunks": chunks,
            "prompt_overrides": self.prompt_overrides,
        }
        resp = await self.http.post(f"{self.settings.generation_url}/evaluate", json=payload)
        resp.raise_for_status()
        return float(resp.json().get("score", 1.0))

    # ------------------------------------------------------------------ streaming

    async def _stream_tokens_and_citations(
        self,
        query: str,
        chunks: list[dict],
        conversation_history: list[dict],
    ) -> AsyncGenerator[str, None]:
        """Call generation service and map its events to rich SSE format."""
        payload = {
            "query": query,
            "chunks": chunks,
            "conversation_history": conversation_history,
            "prompt_overrides": self.prompt_overrides,
        }
        url = f"{self.settings.generation_url}/generate/stream"

        async with self.http.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            citation_index = 1
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")
                if event_type == "token":
                    yield self._sse("token", {"text": event.get("content", "")})
                elif event_type == "citations":
                    for c in event.get("citations", []):
                        yield self._sse(
                            "citation",
                            {
                                "n": citation_index,
                                "documentId": c.get("chunk_id", ""),
                                "filename": c.get("filename"),
                                "page": c.get("page"),
                                "snippet": c.get("snippet", ""),
                            },
                        )
                        citation_index += 1

    async def _timed_stream(
        self,
        query: str,
        chunks: list[dict],
        conversation_history: list[dict],
        conversation_id: str,
        rag_mode: str,
        t0: float,
    ) -> AsyncGenerator[str, None]:
        """Emit token/citation events then a final done event."""
        async for event in self._stream_tokens_and_citations(query, chunks, conversation_history):
            yield event
        latency_ms = int((time.monotonic() - t0) * 1000)
        yield self._sse(
            "done",
            {"conversationId": conversation_id, "latencyMs": latency_ms, "ragMode": rag_mode},
        )
