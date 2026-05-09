from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    db = __import__("medrag_shared.mongo", fromlist=["get_db"]).get_db()
    await db.projects.create_index("name")
    logger.info("admin service ready")
    yield
    await disconnect()


app = FastAPI(title="Admin Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
