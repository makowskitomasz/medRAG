from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import disconnect as amqp_disconnect
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.repositories.project_repository import ensure_indexes
from app.routers.document_router import router as document_router
from app.routers.eval_router import router as eval_router
from app.routers.project_router import router as project_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)
    await ensure_indexes()
    logger.info("admin service ready")
    yield
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Admin Service", lifespan=lifespan)
app.include_router(project_router)
app.include_router(document_router)
app.include_router(eval_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
