import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.connectors.http_connector import get_http
from app.services.auth_validator import validate_token

bearer = HTTPBearer()


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    http: httpx.AsyncClient = Depends(get_http),
) -> dict:
    return await validate_token(credentials.credentials, http)
