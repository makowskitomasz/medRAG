from medrag_shared.models.project import Project, ProjectSettings
from medrag_shared.mongo import get_db

from app.schemas.project_schemas import ProjectResponse


def _to_response(doc: dict) -> ProjectResponse:
    return ProjectResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description", ""),
        settings=ProjectSettings(**doc["settings"]),
        created_by=doc.get("created_by", ""),
        member_ids=doc.get("member_ids", []),
        created_at=doc["created_at"],
    )


async def create(project: Project) -> ProjectResponse:
    await get_db().projects.insert_one(project.model_dump(by_alias=True))
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        settings=project.settings,
        created_by=project.created_by,
        member_ids=project.member_ids,
        created_at=project.created_at,
    )


async def list_all() -> list[ProjectResponse]:
    docs = await get_db().projects.find().to_list(100)
    return [_to_response(d) for d in docs]


async def list_for_user(user_id: str) -> list[ProjectResponse]:
    docs = await get_db().projects.find({"member_ids": user_id}).to_list(100)
    return [_to_response(d) for d in docs]


async def find_by_name(name: str) -> dict | None:
    return await get_db().projects.find_one({"name": name})


async def get_by_id(project_id: str) -> dict | None:
    return await get_db().projects.find_one({"_id": project_id})


async def update_by_id(project_id: str, patch: dict) -> dict | None:
    await get_db().projects.update_one({"_id": project_id}, {"$set": patch})
    return await get_by_id(project_id)


async def delete_by_id(project_id: str) -> None:
    await get_db().projects.delete_one({"_id": project_id})


async def add_member(project_id: str, user_id: str) -> dict | None:
    await get_db().projects.update_one({"_id": project_id}, {"$addToSet": {"member_ids": user_id}})
    return await get_by_id(project_id)


async def remove_member(project_id: str, user_id: str) -> dict | None:
    await get_db().projects.update_one({"_id": project_id}, {"$pull": {"member_ids": user_id}})
    return await get_by_id(project_id)


async def ensure_indexes() -> None:
    await get_db().projects.create_index("name")
    await get_db().projects.create_index("member_ids")
