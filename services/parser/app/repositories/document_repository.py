from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db


async def update_parsed(document_id: str, text: str, trace_id: str | None) -> None:
    entry = StatusHistoryEntry(status=DocumentStatus.PARSED, trace_id=trace_id)
    await get_db().documents.update_one(
        {"_id": document_id},
        {
            "$set": {"extracted_text": text, "status": DocumentStatus.PARSED},
            "$push": {"status_history": entry.model_dump()},
        },
    )


async def update_failed(document_id: str, trace_id: str | None, error: str) -> None:
    entry = StatusHistoryEntry(status=DocumentStatus.FAILED, trace_id=trace_id, error=error)
    await get_db().documents.update_one(
        {"_id": document_id},
        {
            "$push": {"status_history": entry.model_dump()},
            "$set": {"status": DocumentStatus.FAILED},
        },
    )
