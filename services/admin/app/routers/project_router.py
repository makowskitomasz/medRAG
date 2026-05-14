from fastapi import APIRouter, status

from app.schemas.project_schemas import CreateProjectRequest, ProjectResponse, UpdateProjectRequest
from app.services import project_service

router = APIRouter(prefix="/projects")


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectRequest) -> ProjectResponse:
    return await project_service.create_project(body)


@router.get("", response_model=list[ProjectResponse])
async def list_projects() -> list[ProjectResponse]:
    return await project_service.list_projects()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    return await project_service.get_project(project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, body: UpdateProjectRequest) -> ProjectResponse:
    return await project_service.update_project(project_id, body)
