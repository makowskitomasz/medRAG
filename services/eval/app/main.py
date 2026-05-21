import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from medrag_shared import get_logger
from medrag_shared.amqp import connect as amqp_connect
from medrag_shared.amqp import consume
from medrag_shared.amqp import disconnect as amqp_disconnect
from medrag_shared.mongo import connect, disconnect

from app.config.settings import settings
from app.consumers.query_consumer import configure as configure_consumer
from app.consumers.query_consumer import handle_query_completed, setup_topology
from app.repositories.eval_repository import ensure_indexes
from app.routers.eval_router import router

logger = get_logger(__name__)

_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _http_client
    await connect(settings.mongodb_uri)
    await amqp_connect(settings.rabbitmq_url)
    await ensure_indexes()

    _http_client = httpx.AsyncClient(timeout=60.0)
    configure_consumer(settings.generation_url, settings.embedding_url, _http_client)

    # Setup topology before starting consumer
    import aio_pika

    _tmp_conn = await aio_pika.connect_robust(settings.rabbitmq_url)
    _tmp_ch = await _tmp_conn.channel()
    await setup_topology(_tmp_ch)
    await _tmp_conn.close()

    asyncio.create_task(consume("eval.queue", handle_query_completed))
    logger.info("eval service ready")
    yield
    if _http_client:
        await _http_client.aclose()
    await amqp_disconnect()
    await disconnect()


app = FastAPI(title="Eval Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
