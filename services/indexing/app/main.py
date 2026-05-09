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
from app.consumer import handle_chunks_embedded
from app.weaviate_client import connect as weaviate_connect
from app.weaviate_client import disconnect as weaviate_disconnect

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)
    await weaviate_connect(settings.weaviate_url, settings.weaviate_collection)
    asyncio.create_task(consume("indexing.queue", handle_chunks_embedded))
    logger.info("indexing service ready")
    yield
    weaviate_disconnect()
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Indexing Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
