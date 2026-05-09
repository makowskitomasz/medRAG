import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import consume
from medrag_shared.amqp import disconnect as amqp_disconnect
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.consumer import handle_document_chunked
from app.providers.local_bge import LocalBGEProvider

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)

    provider = LocalBGEProvider(model_name=settings.bge_model_name)
    handler = partial(
        handle_document_chunked, provider=provider, batch_size=settings.embedding_batch_size
    )

    async def _handler(payload: dict[str, Any], trace_id: str | None) -> None:
        await handler(payload, trace_id)

    asyncio.create_task(consume("embedding.queue", _handler))
    logger.info("embedding service ready", model=settings.bge_model_name)
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Embedding Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
