from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import disconnect as amqp_disconnect
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.connectors.amqp_topology import setup_topology
from app.routers.ingestion_router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)

    from medrag_shared.amqp import _channel as shared_channel

    if shared_channel is not None:
        await setup_topology(shared_channel)

    logger.info("ingestion service ready")
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Ingestion Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
