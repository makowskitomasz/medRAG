import json
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

    async def _stream_generation(
        self,
        query: str,
        chunks: list[dict],
        conversation_history: list[dict],
        conversation_id: str,
        rag_mode: str,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "query": query,
            "chunks": chunks,
            "conversation_history": conversation_history,
            "prompt_overrides": self.prompt_overrides,
        }
        url = f"{self.settings.generation_url}/generate/stream"

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
                    yield f"data: {json.dumps(event)}\n\n"

        yield "data: [DONE]\n\n"
