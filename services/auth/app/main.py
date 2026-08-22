from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.mongo import connect, disconnect

from app.config import settings
from app.repositories.user_repository import ensure_indexes, seed_admin
from app.routers.auth_router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await connect(settings.mongodb_uri)
    await ensure_indexes()
    await seed_admin(settings.admin_email, settings.admin_password)
    logger.info("auth service ready")
    yield
    await disconnect()


app = FastAPI(title="Auth Service", lifespan=lifespan)
app.include_router(router, prefix="/auth")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
