import asyncio

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.repositories import chunk_repository, document_repository
from app.schemas.document_schemas import PaginatedDocumentsResponse
from app.services import document_service

router = APIRouter(prefix="/projects/{project_id}/documents")


class ProjectStats(BaseModel):
    total_chunks: int
    total_documents: int
    indexed_count: int
    failed_count: int


@router.get("/stats", response_model=ProjectStats)
async def project_stats(project_id: str) -> ProjectStats:
    total_chunks, total_documents, indexed_count, failed_count = await asyncio.gather(
        chunk_repository.count_by_project(project_id),
        document_repository.count_by_project(project_id),
        document_repository.count_by_project(project_id, status="indexed"),
        document_repository.count_by_project(project_id, status="failed"),
    )
    return ProjectStats(
        total_chunks=total_chunks,
        total_documents=total_documents,
        indexed_count=indexed_count,
        failed_count=failed_count,
    )


@router.get("", response_model=PaginatedDocumentsResponse)
async def list_documents(
    project_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
) -> PaginatedDocumentsResponse:
    return await document_service.list_documents(project_id, page, limit, status)
