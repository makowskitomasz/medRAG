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
from app.connectors.providers.local_bge import LocalBGEProvider
from app.consumers import document_consumer

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)

    provider = LocalBGEProvider(model_name=settings.bge_model_name)
    document_consumer.configure(provider, settings.embedding_batch_size)

    asyncio.create_task(consume("embedding.queue", document_consumer.handle_document_chunked))
    logger.info("embedding service ready", model=settings.bge_model_name)
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Embedding Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
