import os
from typing import Any

from medrag_shared import get_logger
from medrag_shared.amqp import publish
from medrag_shared.logging import bind_trace_id
from medrag_shared.models.document import DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db

from app.extractor import extract_text

logger = get_logger(__name__)


async def handle_document_uploaded(payload: dict[str, Any], trace_id: str | None) -> None:
    document_id: str = payload["document_id"]
    tmp_path: str = payload["tmp_path"]
    project_id: str = payload["project_id"]

    if trace_id:
        bind_trace_id(trace_id)

    logger.info("parsing document", document_id=document_id)
    db = get_db()

    try:
        text = extract_text(tmp_path)
    except Exception as exc:
        logger.error("extraction failed", document_id=document_id, error=str(exc))
        await _update_status(db, document_id, DocumentStatus.FAILED, trace_id, error=str(exc))
        raise

    finally:
        # always clean up tmp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    await db.documents.update_one(
        {"_id": document_id},
        {"$set": {"extracted_text": text, "status": DocumentStatus.PARSED}},
    )
    await _update_status(db, document_id, DocumentStatus.PARSED, trace_id)

    await publish(
        exchange_name="documents",
        routing_key="document.parsed",
        payload={"document_id": document_id, "project_id": project_id},
        trace_id=trace_id,
    )
    logger.info("document parsed", document_id=document_id, chars=len(text))


async def _update_status(
    db: Any,
    document_id: str,
    status: DocumentStatus,
    trace_id: str | None,
    error: str | None = None,
) -> None:
    entry = StatusHistoryEntry(status=status, trace_id=trace_id, error=error)
    await db.documents.update_one(
        {"_id": document_id},
        {"$push": {"status_history": entry.model_dump()}},
    )
