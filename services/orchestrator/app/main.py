from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import disconnect as amqp_disconnect

from app.config.settings import settings
from app.connectors import (
    close_http_client,
    connect_mongo,
    create_http_client,
    disconnect_mongo,
)
from app.routers.conversations_router import router as conversations_router
from app.routers.orchestrator_router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect_mongo(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)
    await create_http_client()
    logger.info("orchestrator service ready")
    yield
    await close_http_client()
    await amqp_disconnect()
    await disconnect_mongo()


app = FastAPI(title="Orchestrator Service", lifespan=lifespan)
app.include_router(router)
app.include_router(conversations_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
