from datetime import datetime
from enum import StrEnum

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: EmailStr
    hashed_password: str
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
