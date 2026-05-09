from fastapi import APIRouter, HTTPException, status
from medrag_shared.models.project import (
    ChunkingStrategy,
    EmbeddingProvider,
    Project,
    ProjectSettings,
    RagMode,
)
from medrag_shared.mongo import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/projects")


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    embedding_provider: EmbeddingProvider = EmbeddingProvider.LOCAL_BGE
    rag_mode: RagMode = RagMode.VANILLA
    hybrid_alpha: float = 0.5
    top_k: int = 20
    rerank_top_n: int = 5


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    settings: ProjectSettings


def _to_response(doc: dict) -> ProjectResponse:
    return ProjectResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description", ""),
        settings=ProjectSettings(**doc["settings"]),
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectRequest, user_id: str = "") -> ProjectResponse:
    db = get_db()
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
    await db.projects.insert_one(project.model_dump(by_alias=True))
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        settings=project.settings,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects() -> list[ProjectResponse]:
    db = get_db()
    docs = await db.projects.find().to_list(100)
    return [_to_response(d) for d in docs]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    db = get_db()
    doc = await db.projects.find_one({"_id": project_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return _to_response(doc)
