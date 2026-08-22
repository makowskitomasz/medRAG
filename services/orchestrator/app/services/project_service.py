from fastapi import HTTPException, status
from medrag_shared.models.project import ProjectSettings
from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_project_settings(project_id: str, db: AsyncIOMotorDatabase) -> ProjectSettings:
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required",
        )
    doc = await db["projects"].find_one({"_id": project_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return ProjectSettings(**doc.get("settings", {}))
