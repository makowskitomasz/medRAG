import hashlib

from fastapi import HTTPException, status
from medrag_shared.amqp import publish
from medrag_shared.models.document import Document, DocumentStatus, StatusHistoryEntry

from app.config import settings
from app.connectors.file_storage import file_ext, save
from app.repositories import document_repository, project_repository
from app.schemas.ingestion_schemas import DocumentStatusResponse, UploadResponse


async def upload(
    project_id: str,
    filename: str,
    content: bytes,
    trace_id: str,
) -> UploadResponse:
    if not await project_repository.find_by_id(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ext = file_ext(filename)
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type {ext!r} not allowed. Use: {settings.allowed_extensions}",
        )

    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_size_mb}MB limit",
        )

    content_hash = hashlib.sha256(content).hexdigest()
    if await document_repository.find_duplicate(project_id, content_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already exists in this project",
        )

    tmp_path = save(content, ext, settings.upload_dir)

    doc = Document(
        project_id=project_id,
        filename=filename,
        content_hash=content_hash,
        status=DocumentStatus.UPLOADED,
        status_history=[StatusHistoryEntry(status=DocumentStatus.UPLOADED, trace_id=trace_id)],
    )
    await document_repository.create(doc)

    await publish(
        exchange_name="documents",
        routing_key="document.uploaded",
        payload={"document_id": doc.id, "tmp_path": tmp_path, "project_id": project_id},
        trace_id=trace_id,
    )

    return UploadResponse(document_id=doc.id, status=doc.status)


async def get_status(project_id: str, document_id: str) -> DocumentStatusResponse:
    doc = await document_repository.find_by_id(document_id, project_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentStatusResponse(
        document_id=document_id,
        filename=doc["filename"],
        status=doc["status"],
        status_history=doc.get("status_history", []),
    )
