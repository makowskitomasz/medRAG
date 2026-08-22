from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger

from app.config.settings import settings
from app.connectors import connect_mongo, connect_weaviate, disconnect_mongo, disconnect_weaviate
from app.routers.retrieval_router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect_mongo(settings.mongodb_uri)
    await connect_weaviate(settings.weaviate_url)
    logger.info("retrieval service ready")
    yield
    await disconnect_weaviate()
    await disconnect_mongo()


app = FastAPI(title="Retrieval Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
