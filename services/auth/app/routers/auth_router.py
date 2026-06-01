from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.dependencies import require_auth
from app.schemas.auth_schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> UserResponse:
    return await auth_service.register(body.email, body.password, body.first_name, body.last_name)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    return await auth_service.login(body.email, body.password)


@router.get("/me", response_model=UserResponse)
async def me(payload: dict = Depends(require_auth)) -> UserResponse:
    return await auth_service.get_me(payload["sub"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    return await auth_service.refresh(body.refresh_token)


@router.post("/validate")
async def validate(payload: dict = Depends(require_auth)) -> dict:
    """Internal endpoint used by API Gateway to validate JWT and return claims."""
    return {"user_id": payload["sub"], "role": payload["role"]}


@router.get("/users", response_model=list[UserResponse])
async def list_users(x_user_role: str = Header(default="")) -> list[UserResponse]:
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return await auth_service.list_users()
