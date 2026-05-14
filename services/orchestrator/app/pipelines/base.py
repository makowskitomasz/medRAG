from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx

from app.schemas.orchestrator_schemas import Citation, QueryResponse


class RagPipeline(ABC):
    def __init__(self, http_client: httpx.AsyncClient, settings) -> None:  # type: ignore[type-arg]
        self.http = http_client
        self.settings = settings

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
        payload = {"query": query, "chunks": chunks, "conversation_history": history}
        resp = await self.http.post(f"{self.settings.generation_url}/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        citations = [Citation(**c) for c in data.get("citations", [])]
        return data["answer"], citations

    async def _generate_stream_url(self) -> str:
        return f"{self.settings.generation_url}/generate/stream"
