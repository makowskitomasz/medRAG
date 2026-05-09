from fastapi import HTTPException, status
from medrag_shared.models.project import Project, ProjectSettings

from app.repositories import project_repository
from app.schemas.project_schemas import CreateProjectRequest, ProjectResponse


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


async def list_projects() -> list[ProjectResponse]:
    return await project_repository.list_all()


async def get_project(project_id: str) -> ProjectResponse:
    doc = await project_repository.get_by_id(project_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    from medrag_shared.models.project import ProjectSettings

    return ProjectResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description", ""),
        settings=ProjectSettings(**doc["settings"]),
    )
