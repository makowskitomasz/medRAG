from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.repositories import chunk_repository
from app.schemas.document_schemas import PaginatedDocumentsResponse
from app.services import document_service

router = APIRouter(prefix="/projects/{project_id}/documents")


class ProjectStats(BaseModel):
    total_chunks: int


@router.get("/stats", response_model=ProjectStats)
async def project_stats(project_id: str) -> ProjectStats:
    total_chunks = await chunk_repository.count_by_project(project_id)
    return ProjectStats(total_chunks=total_chunks)


@router.get("", response_model=PaginatedDocumentsResponse)
async def list_documents(
    project_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
) -> PaginatedDocumentsResponse:
    return await document_service.list_documents(project_id, page, limit, status)
