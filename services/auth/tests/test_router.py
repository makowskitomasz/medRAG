from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import hash_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_mongo():
    """Patch MongoDB so tests run without a real connection."""
    mock_db = MagicMock()
    with (
        patch("medrag_shared.mongo.connect", new_callable=AsyncMock),
        patch("medrag_shared.mongo.disconnect", new_callable=AsyncMock),
        patch("app.router._ensure_indexes", new_callable=AsyncMock),
        patch("app.router._seed_admin", new_callable=AsyncMock),
        patch("app.router.get_db", return_value=mock_db),
        patch("app.router.get_db", return_value=mock_db),
    ):
        yield mock_db


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_success(mock_mongo):
    mock_mongo.users.find_one = AsyncMock(return_value=None)
    mock_mongo.users.insert_one = AsyncMock()

    response = client.post("/auth/register", json={"email": "a@b.com", "password": "pass123"})
    assert response.status_code == 201
    assert response.json()["email"] == "a@b.com"


def test_register_duplicate(mock_mongo):
    mock_mongo.users.find_one = AsyncMock(return_value={"email": "a@b.com"})

    response = client.post("/auth/register", json={"email": "a@b.com", "password": "pass123"})
    assert response.status_code == 409


def test_login_success(mock_mongo):
    mock_mongo.users.find_one = AsyncMock(
        return_value={"_id": "uid1", "hashed_password": hash_password("pass123"), "role": "user"}
    )

    response = client.post("/auth/login", json={"email": "a@b.com", "password": "pass123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(mock_mongo):
    mock_mongo.users.find_one = AsyncMock(
        return_value={"_id": "uid1", "hashed_password": hash_password("correct"), "role": "user"}
    )

    response = client.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert response.status_code == 401


def test_login_not_found(mock_mongo):
    mock_mongo.users.find_one = AsyncMock(return_value=None)

    response = client.post("/auth/login", json={"email": "x@y.com", "password": "pass"})
    assert response.status_code == 401
