from medrag_shared.models.user import User, UserRole
from medrag_shared.mongo import get_db

from app.connectors.jwt_connector import hash_password


async def find_by_email(email: str) -> dict | None:
    return await get_db().users.find_one({"email": email})


async def find_by_id(user_id: str) -> dict | None:
    return await get_db().users.find_one({"_id": user_id})


async def create_user(email: str, hashed_pw: str, role: UserRole = UserRole.USER) -> User:
    user = User(email=email, hashed_password=hashed_pw, role=role)
    await get_db().users.insert_one(user.model_dump(by_alias=True))
    return user


async def ensure_indexes() -> None:
    await get_db().users.create_index("email", unique=True)


async def seed_admin(email: str, password: str) -> None:
    if not await find_by_email(email):
        await create_user(email, hash_password(password), UserRole.ADMIN)
