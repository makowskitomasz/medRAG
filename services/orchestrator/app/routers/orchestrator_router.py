import httpx
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.settings import settings
from app.dependencies import get_db, get_http_client
from app.schemas.orchestrator_schemas import QueryRequest, QueryResponse
from app.services.orchestrator_service import handle_query, handle_query_stream

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_trace_id: str | None = Header(default=None),
) -> QueryResponse:
    return await handle_query(request, db, http_client, settings, x_trace_id)


@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_trace_id: str | None = Header(default=None),
) -> StreamingResponse:
    gen = await handle_query_stream(request, db, http_client, settings, x_trace_id)
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
