from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from weaviate import WeaviateAsyncClient

from app.dependencies import get_db, get_weaviate
from app.schemas.retrieval_schemas import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import hybrid_search

router = APIRouter()


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(
    request: RetrievalRequest,
    weaviate_client: WeaviateAsyncClient = Depends(get_weaviate),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> RetrievalResponse:
    return await hybrid_search(request, weaviate_client, db)
