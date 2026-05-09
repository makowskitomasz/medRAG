import uuid

from fastapi import APIRouter, Request, UploadFile, status

from app.schemas.ingestion_schemas import DocumentStatusResponse, UploadResponse
from app.services import ingestion_service

router = APIRouter()


@router.post(
    "/projects/{project_id}/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(project_id: str, file: UploadFile, request: Request) -> UploadResponse:
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    content = await file.read()
    return await ingestion_service.upload(project_id, file.filename or "unknown", content, trace_id)


@router.get(
    "/projects/{project_id}/documents/{document_id}",
    response_model=DocumentStatusResponse,
)
async def get_document_status(project_id: str, document_id: str) -> DocumentStatusResponse:
    return await ingestion_service.get_status(project_id, document_id)
