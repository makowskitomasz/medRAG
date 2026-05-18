from fastapi import APIRouter, Query

from app.schemas.document_schemas import PaginatedDocumentsResponse
from app.services import document_service

router = APIRouter(prefix="/projects/{project_id}/documents")


@router.get("", response_model=PaginatedDocumentsResponse)
async def list_documents(
    project_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
) -> PaginatedDocumentsResponse:
    return await document_service.list_documents(project_id, page, limit, status)
