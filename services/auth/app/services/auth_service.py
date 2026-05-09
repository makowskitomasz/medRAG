from fastapi import HTTPException, status

from app.connectors.jwt_connector import create_token, hash_password, verify_password
from app.repositories import user_repository
from app.schemas.auth_schemas import TokenResponse, UserResponse


async def register(email: str, password: str) -> UserResponse:
    if await user_repository.find_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await user_repository.create_user(email, hash_password(password))
    return UserResponse(id=user.id, email=user.email, role=user.role)


async def login(email: str, password: str) -> TokenResponse:
    doc = await user_repository.find_by_email(email)
    if not doc or not verify_password(password, doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(str(doc["_id"]), doc["role"]))


async def get_me(user_id: str) -> UserResponse:
    doc = await user_repository.find_by_id(user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=str(doc["_id"]), email=doc["email"], role=doc["role"])
