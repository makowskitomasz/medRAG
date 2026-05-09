from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: str
    status: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    status_history: list[dict]
