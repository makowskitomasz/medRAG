from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db


async def find_by_id(document_id: str) -> dict | None:
    return await get_db().documents.find_one({"_id": document_id})


async def update_chunked(document_id: str, chunk_count: int, trace_id: str | None) -> None:
    entry = StatusHistoryEntry(status=DocumentStatus.CHUNKED, trace_id=trace_id)
    await get_db().documents.update_one(
        {"_id": document_id},
        {
            "$set": {"status": DocumentStatus.CHUNKED, "stats.chunk_count": chunk_count},
            "$push": {"status_history": entry.model_dump()},
        },
    )
