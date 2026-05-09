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
from app.consumer import handle_document_uploaded

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)
    asyncio.create_task(consume("parser.queue", handle_document_uploaded))
    logger.info("parser service ready")
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Parser Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
