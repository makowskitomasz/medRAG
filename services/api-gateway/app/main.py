from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger

from app.config import settings
from app.connectors.http_connector import connect, disconnect
from app.routers.proxy_router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect()
    logger.info("api-gateway ready")
    yield
    await disconnect()


app = FastAPI(title="API Gateway", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
