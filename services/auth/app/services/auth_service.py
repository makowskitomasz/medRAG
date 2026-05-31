from fastapi import HTTPException, status

from app.connectors.jwt_connector import (
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
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
    user_id = str(doc["_id"])
    role = doc["role"]
    return TokenResponse(
        access_token=create_token(user_id, role),
        refresh_token=create_refresh_token(user_id, role),
    )


async def refresh(refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")
    user_id: str = payload["sub"]
    role: str = payload["role"]
    doc = await user_repository.find_by_id(user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenResponse(
        access_token=create_token(user_id, role),
        refresh_token=create_refresh_token(user_id, role),
    )


async def get_me(user_id: str) -> UserResponse:
    doc = await user_repository.find_by_id(user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=str(doc["_id"]), email=doc["email"], role=doc["role"])
