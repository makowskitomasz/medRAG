import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import consume
from medrag_shared.amqp import disconnect as amqp_disconnect
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.connectors.providers.base import BaseEmbeddingProvider
from app.consumers import document_consumer

logger = get_logger(__name__)


def _build_provider() -> BaseEmbeddingProvider:
    if settings.embedding_provider == "openai":
        from app.connectors.providers.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key or None,
        )
    if settings.embedding_provider == "local_bge":
        from app.connectors.providers.local_bge import LocalBGEProvider

        return LocalBGEProvider(model_name=settings.bge_model_name)
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider!r}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)

    provider = _build_provider()
    document_consumer.configure(provider, settings.embedding_batch_size)

    asyncio.create_task(consume("embedding.queue", document_consumer.handle_document_chunked))
    logger.info("embedding service ready", provider=settings.embedding_provider)
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Embedding Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
