import hashlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from medrag_shared.amqp import publish
from medrag_shared.models.document import Document, DocumentStatus, StatusHistoryEntry
from medrag_shared.mongo import get_db
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class UploadResponse(BaseModel):
    document_id: str
    status: str


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@router.post(
    "/projects/{project_id}/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(project_id: str, file: UploadFile, request: Request) -> UploadResponse:
    db = get_db()
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))

    # validate project exists
    if not await db.projects.find_one({"_id": project_id}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # validate file type
    ext = _ext(file.filename or "")
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type {ext!r} not allowed. Use: {settings.allowed_extensions}",
        )

    content = await file.read()

    # validate file size
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_size_mb}MB limit",
        )

    content_hash = _hash(content)

    # deduplication check
    if await db.documents.find_one({"project_id": project_id, "content_hash": content_hash}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already exists in this project",
        )

    # save to tmp
    os.makedirs(settings.upload_dir, exist_ok=True)
    tmp_path = f"{settings.upload_dir}/{uuid.uuid4()}{ext}"
    with open(tmp_path, "wb") as f:
        f.write(content)

    # persist document
    doc = Document(
        project_id=project_id,
        filename=file.filename or "unknown",
        content_hash=content_hash,
        status=DocumentStatus.UPLOADED,
        status_history=[StatusHistoryEntry(status=DocumentStatus.UPLOADED, trace_id=trace_id)],
    )
    await db.documents.insert_one(doc.model_dump(by_alias=True))

    # publish event
    await publish(
        exchange_name="documents",
        routing_key="document.uploaded",
        payload={"document_id": doc.id, "tmp_path": tmp_path, "project_id": project_id},
        trace_id=trace_id,
    )

    return UploadResponse(document_id=doc.id, status=doc.status)


@router.get("/projects/{project_id}/documents/{document_id}")
async def get_document_status(project_id: str, document_id: str) -> dict:
    db = get_db()
    doc = await db.documents.find_one({"_id": document_id, "project_id": project_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {
        "document_id": document_id,
        "filename": doc["filename"],
        "status": doc["status"],
        "status_history": doc.get("status_history", []),
    }
