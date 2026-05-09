from typing import Any

from medrag_shared.logging import bind_trace_id

from app.connectors.providers.base import BaseEmbeddingProvider
from app.services import embedding_service

_provider: BaseEmbeddingProvider | None = None
_batch_size: int = 32


def configure(provider: BaseEmbeddingProvider, batch_size: int = 32) -> None:
    global _provider, _batch_size
    _provider = provider
    _batch_size = batch_size


async def handle_document_chunked(payload: dict[str, Any], trace_id: str | None) -> None:
    if trace_id:
        bind_trace_id(trace_id)
    assert _provider is not None, "Consumer not configured — call configure() first"
    await embedding_service.embed(
        document_id=payload["document_id"],
        project_id=payload["project_id"],
        chunk_ids=payload.get("chunk_ids", []),
        trace_id=trace_id,
        provider=_provider,
        batch_size=_batch_size,
    )
