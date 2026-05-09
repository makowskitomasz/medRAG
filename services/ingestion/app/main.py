from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import disconnect as amqp_disconnect
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.router import router
from app.topology import setup_topology

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)

    # set up RabbitMQ topology (exchanges, queues, DLX)
    conn = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await conn.channel()
    await setup_topology(channel)
    await conn.close()

    logger.info("ingestion service ready")
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Ingestion Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
