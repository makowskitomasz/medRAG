from medrag_shared.models.document import Document
from medrag_shared.mongo import get_db


async def find_duplicate(project_id: str, content_hash: str) -> dict | None:
    return await get_db().documents.find_one(
        {"project_id": project_id, "content_hash": content_hash}
    )


async def create(document: Document) -> None:
    await get_db().documents.insert_one(document.model_dump(by_alias=True))


async def find_by_id(document_id: str, project_id: str) -> dict | None:
    return await get_db().documents.find_one({"_id": document_id, "project_id": project_id})
