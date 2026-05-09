import os

from medrag_shared import get_logger
from medrag_shared.amqp import publish

from app.connectors.file_extractor import extract_text
from app.repositories import document_repository

logger = get_logger(__name__)


async def parse(document_id: str, tmp_path: str, project_id: str, trace_id: str | None) -> None:
    logger.info("parsing document", document_id=document_id)

    try:
        text = extract_text(tmp_path)
    except Exception as exc:
        logger.error("extraction failed", document_id=document_id, error=str(exc))
        await document_repository.update_failed(document_id, trace_id, str(exc))
        raise
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    await document_repository.update_parsed(document_id, text, trace_id)

    await publish(
        exchange_name="documents",
        routing_key="document.parsed",
        payload={"document_id": document_id, "project_id": project_id},
        trace_id=trace_id,
    )
    logger.info("document parsed", document_id=document_id, chars=len(text))
