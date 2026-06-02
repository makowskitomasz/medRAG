from fastapi import APIRouter, Header, HTTPException, status

from app.schemas.project_schemas import (
    CreateProjectRequest,
    DeleteProjectResponse,
    ProjectResponse,
    ReindexResponse,
    SettingsOptions,
    UpdateProjectRequest,
    UpdateSettingsRequest,
)
from app.services import project_service
from app.services.settings_options_service import get_settings_options

router = APIRouter(prefix="/projects")


@router.get("/settings/options", response_model=SettingsOptions)
async def settings_options() -> SettingsOptions:
    """Return available enum values, field constraints, and default prompt templates.
    Intended for frontend form construction."""
    return get_settings_options()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest, x_user_id: str = Header(default="")
) -> ProjectResponse:
    return await project_service.create_project(body, x_user_id)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    x_user_id: str = Header(default=""),
    x_user_role: str = Header(default=""),
) -> list[ProjectResponse]:
    return await project_service.list_projects_for_user(x_user_id, x_user_role)


@router.post("/{project_id}/members/{user_id}", response_model=ProjectResponse)
async def add_member(
    project_id: str,
    user_id: str,
    x_user_role: str = Header(default=""),
) -> ProjectResponse:
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return await project_service.add_member(project_id, user_id)


@router.delete("/{project_id}/members/{user_id}", response_model=ProjectResponse)
async def remove_member(
    project_id: str,
    user_id: str,
    x_user_role: str = Header(default=""),
) -> ProjectResponse:
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return await project_service.remove_member(project_id, user_id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    return await project_service.get_project(project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, body: UpdateProjectRequest) -> ProjectResponse:
    return await project_service.update_project(project_id, body)


@router.patch("/{project_id}/settings", response_model=ProjectResponse)
async def update_settings(project_id: str, body: UpdateSettingsRequest) -> ProjectResponse:
    """Granular settings patch — only supplied fields are updated.
    prompt_overrides are merged (not replaced) with existing overrides."""
    return await project_service.update_settings(project_id, body)


@router.delete("/{project_id}/settings/prompts/{slug}", response_model=ProjectResponse)
async def delete_prompt_override(project_id: str, slug: str) -> ProjectResponse:
    """Remove a single prompt override, reverting it to the file-based default."""
    return await project_service.delete_prompt_override(project_id, slug)


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project(project_id: str) -> DeleteProjectResponse:
    return await project_service.delete_project(project_id)


@router.post("/{project_id}/reindex", response_model=ReindexResponse)
async def reindex_project(project_id: str) -> ReindexResponse:
    """Re-publish document.uploaded events for all indexed documents of a project."""
    return await project_service.reindex_project(project_id)
