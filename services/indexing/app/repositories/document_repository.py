from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db


async def update_indexed(document_id: str, trace_id: str | None) -> None:
    entry = StatusHistoryEntry(status=DocumentStatus.INDEXED, trace_id=trace_id)
    await get_db().documents.update_one(
        {"_id": document_id},
        {
            "$set": {"status": DocumentStatus.INDEXED},
            "$push": {"status_history": entry.model_dump()},
        },
    )
