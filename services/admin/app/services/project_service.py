from fastapi import HTTPException, status
from medrag_shared.models.project import Project, ProjectSettings

from app.repositories import project_repository
from app.schemas.project_schemas import (
    CreateProjectRequest,
    ProjectResponse,
    UpdateProjectRequest,
    UpdateSettingsRequest,
)


async def create_project(body: CreateProjectRequest, user_id: str = "") -> ProjectResponse:
    proj_settings = ProjectSettings(
        chunking_strategy=body.chunking_strategy,
        embedding_provider=body.embedding_provider,
        rag_mode=body.rag_mode,
        hybrid_alpha=body.hybrid_alpha,
        top_k=body.top_k,
        rerank_top_n=body.rerank_top_n,
    )
    project = Project(
        name=body.name,
        description=body.description,
        settings=proj_settings,
        created_by=user_id,
    )
    return await project_repository.create(project)


async def update_project(project_id: str, body: UpdateProjectRequest) -> ProjectResponse:
    doc = await project_repository.get_by_id(project_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    patch: dict = {}
    if body.name is not None:
        patch["name"] = body.name
    if body.description is not None:
        patch["description"] = body.description
    if body.settings is not None:
        patch["settings"] = body.settings.model_dump()
    updated = await project_repository.update_by_id(project_id, patch)
    return project_repository._to_response(updated)


async def update_settings(project_id: str, body: UpdateSettingsRequest) -> ProjectResponse:
    """Merge only the provided settings fields into the existing settings."""
    doc = await project_repository.get_by_id(project_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    current = ProjectSettings(**doc["settings"])
    merged = current.model_dump()

    updates = body.model_dump(exclude_unset=True)
    if "prompt_overrides" in updates and updates["prompt_overrides"] is not None:
        # Merge override keys — don't wipe keys not mentioned in the request.
        existing = merged.get("prompt_overrides", {})
        merged["prompt_overrides"] = {**existing, **updates.pop("prompt_overrides")}
    merged.update({k: v for k, v in updates.items() if v is not None})

    updated = await project_repository.update_by_id(project_id, {"settings": merged})
    return project_repository._to_response(updated)


async def delete_prompt_override(project_id: str, slug: str) -> ProjectResponse:
    """Remove a single prompt override — reverts to the file-based default."""
    doc = await project_repository.get_by_id(project_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    current = ProjectSettings(**doc["settings"])
    overrides = dict(current.prompt_overrides)
    overrides.pop(slug, None)
    current_dump = current.model_dump()
    current_dump["prompt_overrides"] = overrides

    updated = await project_repository.update_by_id(project_id, {"settings": current_dump})
    return project_repository._to_response(updated)


async def list_projects() -> list[ProjectResponse]:
    return await project_repository.list_all()


async def get_project(project_id: str) -> ProjectResponse:
    doc = await project_repository.get_by_id(project_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project_repository._to_response(doc)
