"""HTTP endpoint tests for Admin Service — project CRUD."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)

_PROJECT_DOC = {
    "_id": "proj-abc",
    "name": "Test Project",
    "description": "desc",
    "settings": {
        "chunking_strategy": "recursive",
        "embedding_provider": "local_bge",
        "rag_mode": "vanilla",
        "hybrid_alpha": 0.5,
        "top_k": 20,
        "rerank_top_n": 5,
        "prompt_overrides": {},
    },
    "created_by": "user-1",
    "created_at": _NOW,
}


@pytest.fixture(autouse=True)
def mock_deps():
    mock_db = MagicMock()
    with (
        patch("medrag_shared.mongo.connect", new_callable=AsyncMock),
        patch("medrag_shared.mongo.disconnect", new_callable=AsyncMock),
        patch("medrag_shared.amqp.connect", new_callable=AsyncMock),
        patch("medrag_shared.amqp.disconnect", new_callable=AsyncMock),
        patch("app.connectors.weaviate_connector.connect"),
        patch("app.connectors.weaviate_connector.disconnect"),
        patch("app.repositories.project_repository.get_db", return_value=mock_db),
        patch("app.repositories.document_repository.get_db", return_value=mock_db),
        patch("app.repositories.chunk_repository.get_db", return_value=mock_db),
        patch("app.repositories.conversation_repository.get_db", return_value=mock_db),
        patch("app.services.eval_service.get_db", return_value=mock_db),
        patch("app.repositories.project_repository.ensure_indexes", new_callable=AsyncMock),
    ):
        yield mock_db


# ── Health ────────────────────────────────────────────────────────────────────


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "admin"


# ── Settings options ──────────────────────────────────────────────────────────


def test_settings_options_returns_all_rag_modes():
    resp = client.get("/projects/settings/options")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rag_modes"]) == 9
    modes = [m["value"] for m in data["rag_modes"]]
    assert "vanilla" in modes
    assert "rare_rag" in modes


def test_settings_options_returns_field_constraints():
    resp = client.get("/projects/settings/options")
    data = resp.json()
    assert data["hybrid_alpha"]["min"] == 0.0
    assert data["hybrid_alpha"]["max"] == 1.0
    assert data["top_k"]["type"] == "int"


# ── Create project ────────────────────────────────────────────────────────────


def test_create_project_returns_201(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)
    mock_deps.projects.insert_one = AsyncMock()

    resp = client.post(
        "/projects",
        json={"name": "Drug Interactions", "description": "Test", "rag_mode": "vanilla"},
        headers={"x-user-id": "user-1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Drug Interactions"
    assert data["settings"]["rag_mode"] == "vanilla"
    assert "id" in data


def test_create_project_defaults(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)
    mock_deps.projects.insert_one = AsyncMock()

    resp = client.post("/projects", json={"name": "Minimal"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["settings"]["chunking_strategy"] == "recursive"
    assert data["settings"]["hybrid_alpha"] == 0.5
    assert data["settings"]["top_k"] == 20


# ── List / Get projects ───────────────────────────────────────────────────────


def test_list_projects(mock_deps):
    mock_deps.projects.find.return_value.to_list = AsyncMock(return_value=[_PROJECT_DOC])

    resp = client.get("/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Test Project"


def test_get_project_found(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=_PROJECT_DOC)

    resp = client.get("/projects/proj-abc")
    assert resp.status_code == 200
    assert resp.json()["id"] == "proj-abc"


def test_get_project_not_found(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)

    resp = client.get("/projects/missing")
    assert resp.status_code == 404


# ── Update settings ───────────────────────────────────────────────────────────


def test_patch_settings_merges_fields(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=_PROJECT_DOC)
    mock_deps.projects.update_one = AsyncMock()

    updated_doc = {**_PROJECT_DOC, "settings": {**_PROJECT_DOC["settings"], "rag_mode": "hyde"}}
    mock_deps.projects.find_one = AsyncMock(side_effect=[_PROJECT_DOC, updated_doc])

    resp = client.patch("/projects/proj-abc/settings", json={"rag_mode": "hyde"})
    assert resp.status_code == 200
    assert resp.json()["settings"]["rag_mode"] == "hyde"
    # other fields should be preserved
    assert resp.json()["settings"]["chunking_strategy"] == "recursive"


def test_patch_settings_project_not_found(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)

    resp = client.patch("/projects/missing/settings", json={"rag_mode": "hyde"})
    assert resp.status_code == 404


def test_patch_settings_rejects_invalid_rag_mode(mock_deps):
    resp = client.patch("/projects/proj-abc/settings", json={"rag_mode": "nonexistent_mode"})
    assert resp.status_code == 422


# ── Delete project ────────────────────────────────────────────────────────────


def test_delete_project_returns_cascade_counts(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=_PROJECT_DOC)
    mock_deps.documents.delete_many = AsyncMock(return_value=MagicMock(deleted_count=3))
    mock_deps.chunks.delete_many = AsyncMock(return_value=MagicMock(deleted_count=42))
    mock_deps.conversations.delete_many = AsyncMock(return_value=MagicMock(deleted_count=2))
    mock_deps.projects.delete_one = AsyncMock()

    with patch("app.connectors.weaviate_connector.delete_by_project", return_value=42):
        resp = client.delete("/projects/proj-abc")

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "proj-abc"
    assert data["documents_deleted"] == 3
    assert data["chunks_deleted"] == 42
    assert data["conversations_deleted"] == 2
    assert data["vectors_deleted"] == 42


def test_delete_project_not_found(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)

    resp = client.delete("/projects/missing")
    assert resp.status_code == 404


def test_delete_project_weaviate_failure_does_not_abort(mock_deps):
    """Weaviate error is logged but deletion of Mongo data still completes."""
    mock_deps.projects.find_one = AsyncMock(return_value=_PROJECT_DOC)
    mock_deps.documents.delete_many = AsyncMock(return_value=MagicMock(deleted_count=1))
    mock_deps.chunks.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))
    mock_deps.conversations.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))
    mock_deps.projects.delete_one = AsyncMock()

    with patch(
        "app.connectors.weaviate_connector.delete_by_project",
        side_effect=RuntimeError("Weaviate down"),
    ):
        resp = client.delete("/projects/proj-abc")

    assert resp.status_code == 200
    assert resp.json()["vectors_deleted"] == 0
    assert resp.json()["chunks_deleted"] == 5


# ── Reindex ───────────────────────────────────────────────────────────────────


def test_reindex_publishes_events_for_indexed_docs(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=_PROJECT_DOC)
    indexed_docs = [
        {"_id": "doc-1", "filename": "a.pdf", "content_hash": "h1"},
        {"_id": "doc-2", "filename": "b.pdf", "content_hash": "h2"},
    ]
    mock_deps.documents.find.return_value.to_list = AsyncMock(return_value=indexed_docs)

    with patch("app.services.project_service.publish", new_callable=AsyncMock) as mock_pub:
        resp = client.post("/projects/proj-abc/reindex")

    assert resp.status_code == 200
    assert resp.json()["documents_queued"] == 2
    assert mock_pub.call_count == 2


def test_reindex_project_not_found(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=None)

    resp = client.post("/projects/missing/reindex")
    assert resp.status_code == 404


def test_reindex_no_indexed_docs_queues_zero(mock_deps):
    mock_deps.projects.find_one = AsyncMock(return_value=_PROJECT_DOC)
    mock_deps.documents.find.return_value.to_list = AsyncMock(return_value=[])

    with patch("app.services.project_service.publish", new_callable=AsyncMock):
        resp = client.post("/projects/proj-abc/reindex")

    assert resp.status_code == 200
    assert resp.json()["documents_queued"] == 0
