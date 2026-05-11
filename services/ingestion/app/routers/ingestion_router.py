import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from app.schemas.ingestion_schemas import DocumentStatusResponse, UploadResponse
from app.services import ingestion_service

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post(
    "/projects/{project_id}/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(project_id: str, file: UploadFile, request: Request) -> UploadResponse:
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if file.content_type not in ALLOWED_CONTENT_TYPES and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: PDF, DOCX.",
        )
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    content = await file.read()
    return await ingestion_service.upload(project_id, filename, content, trace_id)


@router.get(
    "/projects/{project_id}/documents",
    response_model=list[DocumentStatusResponse],
)
async def list_documents(project_id: str) -> list[DocumentStatusResponse]:
    return await ingestion_service.list_documents(project_id)


@router.get(
    "/projects/{project_id}/documents/{document_id}",
    response_model=DocumentStatusResponse,
)
async def get_document_status(project_id: str, document_id: str) -> DocumentStatusResponse:
    return await ingestion_service.get_status(project_id, document_id)


@router.delete(
    "/projects/{project_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(project_id: str, document_id: str) -> None:
    await ingestion_service.delete_document(project_id, document_id)
