from motor.motor_asyncio import AsyncIOMotorDatabase
from weaviate import WeaviateAsyncClient
from weaviate.classes.query import HybridFusion, MetadataQuery

from app.schemas.retrieval_schemas import RetrievalRequest, RetrievalResponse, RetrievedChunk


async def hybrid_search(
    request: RetrievalRequest,
    weaviate_client: WeaviateAsyncClient,
    db: AsyncIOMotorDatabase,
) -> RetrievalResponse:
    collection = weaviate_client.collections.get("Chunk")

    hybrid_kwargs: dict = {
        "query": request.query,
        "alpha": request.alpha,
        "limit": request.top_k,
        "fusion_type": HybridFusion.RELATIVE_SCORE,
        "return_metadata": MetadataQuery(score=True),
        "filters": _project_filter(request.project_id),
    }
    if request.query_vector:
        hybrid_kwargs["vector"] = request.query_vector

    result = await collection.query.hybrid(**hybrid_kwargs)

    chunk_ids = [str(obj.uuid) for obj in result.objects]
    mongo_chunks = await _fetch_chunk_metadata(chunk_ids, db)

    chunks: list[RetrievedChunk] = []
    for obj in result.objects:
        weaviate_id = str(obj.uuid)
        meta = mongo_chunks.get(weaviate_id, {})
        chunks.append(
            RetrievedChunk(
                chunk_id=weaviate_id,
                document_id=meta.get("document_id", obj.properties.get("document_id", "")),
                project_id=meta.get("project_id", request.project_id),
                content=obj.properties.get("content", ""),
                score=obj.metadata.score if obj.metadata else 0.0,
                chunk_index=meta.get("chunk_index", obj.properties.get("chunk_index", 0)),
                page=meta.get("page"),
                document_title=meta.get("document_title"),
                filename=meta.get("filename"),
            )
        )

    return RetrievalResponse(chunks=chunks, total=len(chunks))


def _project_filter(project_id: str):
    from weaviate.classes.query import Filter

    return Filter.by_property("project_id").equal(project_id)


async def _fetch_chunk_metadata(
    weaviate_ids: list[str],
    db: AsyncIOMotorDatabase,
) -> dict[str, dict]:
    if not weaviate_ids:
        return {}

    pipeline = [
        {"$match": {"weaviate_id": {"$in": weaviate_ids}}},
        {
            "$lookup": {
                "from": "documents",
                "localField": "document_id",
                "foreignField": "_id",
                "as": "doc",
            }
        },
        {"$unwind": {"path": "$doc", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "weaviate_id": 1,
                "document_id": 1,
                "project_id": 1,
                "chunk_index": 1,
                "page": 1,
                "filename": "$doc.filename",
            }
        },
    ]

    result: dict[str, dict] = {}
    async for doc in db["chunks"].aggregate(pipeline):
        wid = doc.get("weaviate_id")
        if wid:
            result[wid] = {
                "document_id": doc.get("document_id", ""),
                "project_id": doc.get("project_id", ""),
                "chunk_index": doc.get("chunk_index", 0),
                "page": doc.get("page"),
                "filename": doc.get("filename"),
            }
    return result
