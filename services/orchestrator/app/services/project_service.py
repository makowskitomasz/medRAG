from medrag_shared.models.project import ProjectSettings
from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_project_settings(project_id: str, db: AsyncIOMotorDatabase) -> ProjectSettings:
    doc = await db["projects"].find_one({"_id": project_id})
    if not doc:
        raise ValueError(f"Project {project_id} not found")
    return ProjectSettings(**doc.get("settings", {}))
