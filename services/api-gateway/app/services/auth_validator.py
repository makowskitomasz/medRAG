import httpx
from fastapi import HTTPException, status

from app.config import settings


async def validate_token(token: str, http: httpx.AsyncClient) -> dict:
    try:
        resp = await http.post(
            f"{settings.auth_url}/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {**resp.json(), "token": token}
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )
