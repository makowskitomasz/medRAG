import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_deps():
    mock_db = MagicMock()
    with (
        patch("medrag_shared.mongo.connect", new_callable=AsyncMock),
        patch("medrag_shared.mongo.disconnect", new_callable=AsyncMock),
        patch("medrag_shared.amqp.connect", new_callable=AsyncMock),
        patch("medrag_shared.amqp.disconnect", new_callable=AsyncMock),
        patch("app.services.ingestion_service.publish", new_callable=AsyncMock),
        patch("app.services.ingestion_service.save", return_value="/tmp/test.pdf"),
        patch("app.main.setup_topology", new_callable=AsyncMock),
        patch("medrag_shared.amqp._channel", new_callable=MagicMock),
        patch("app.repositories.project_repository.get_db", return_value=mock_db),
        patch("app.repositories.document_repository.get_db", return_value=mock_db),
    ):
        yield mock_db


def test_health():
    assert client.get("/health").status_code == 200


def test_upload_success(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value={"_id": "proj1"})
    mock_deps.documents.find_one = AsyncMock(return_value=None)
    mock_deps.documents.insert_one = AsyncMock()

    response = client.post(
        "/projects/proj1/documents",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")},
    )
    assert response.status_code == 202
    assert "document_id" in response.json()


def test_upload_project_not_found(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)

    response = client.post(
        "/projects/missing/documents",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert response.status_code == 404


def test_upload_invalid_extension(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value={"_id": "proj1"})

    response = client.post(
        "/projects/proj1/documents",
        files={"file": ("test.exe", io.BytesIO(b"binary"), "application/octet-stream")},
    )
    assert response.status_code == 415


def test_upload_duplicate(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value={"_id": "proj1"})
    mock_deps.documents.find_one = AsyncMock(return_value={"_id": "existing"})

    response = client.post(
        "/projects/proj1/documents",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")},
    )
    assert response.status_code == 409
