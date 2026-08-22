from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db


async def get_extracted_text(document_id: str) -> str | None:
    doc = await get_db().documents.find_one({"_id": document_id}, {"extracted_text": 1})
    return doc.get("extracted_text") if doc else None


async def update_parsed(
    document_id: str, text: str, trace_id: str | None, page_count: int = 0
) -> None:
    entry = StatusHistoryEntry(status=DocumentStatus.PARSED, trace_id=trace_id)
    update: dict = {
        "$set": {"extracted_text": text, "status": DocumentStatus.PARSED},
        "$push": {"status_history": entry.model_dump()},
    }
    if page_count > 0:
        update["$set"]["stats.page_count"] = page_count
    await get_db().documents.update_one({"_id": document_id}, update)


async def update_failed(document_id: str, trace_id: str | None, error: str) -> None:
    entry = StatusHistoryEntry(status=DocumentStatus.FAILED, trace_id=trace_id, error=error)
    await get_db().documents.update_one(
        {"_id": document_id},
        {
            "$push": {"status_history": entry.model_dump()},
            "$set": {"status": DocumentStatus.FAILED},
        },
    )
