from fastapi import APIRouter, Depends, HTTPException, status
from medrag_shared.models.user import User, UserRole
from medrag_shared.mongo import get_db
from pydantic import BaseModel, EmailStr

from app.dependencies import require_auth
from app.security import create_token, hash_password, verify_password

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> UserResponse:
    db = get_db()
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password))
    await db.users.insert_one(user.model_dump(by_alias=True))
    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    db = get_db()
    doc = await db.users.find_one({"email": body.email})
    if not doc or not verify_password(body.password, doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(str(doc["_id"]), doc["role"]))


@router.get("/me", response_model=UserResponse)
async def me(payload: dict = Depends(require_auth)) -> UserResponse:
    db = get_db()
    doc = await db.users.find_one({"_id": payload["sub"]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=str(doc["_id"]), email=doc["email"], role=doc["role"])


@router.post("/validate")
async def validate(payload: dict = Depends(require_auth)) -> dict:
    """Internal endpoint used by API Gateway to validate JWT and return claims."""
    return {"user_id": payload["sub"], "role": payload["role"]}


async def _ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)


async def _seed_admin(email: str, password: str) -> None:
    db = get_db()
    if not await db.users.find_one({"email": email}):
        user = User(email=email, hashed_password=hash_password(password), role=UserRole.ADMIN)
        await db.users.insert_one(user.model_dump(by_alias=True))
