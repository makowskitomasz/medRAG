from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.retrieval_schemas import RetrievalRequest
from app.services.retrieval_service import hybrid_search


def _make_weaviate_obj(uuid: str, content: str, project_id: str, score: float):
    obj = MagicMock()
    obj.uuid = uuid
    obj.properties = {"content": content, "project_id": project_id, "chunk_index": 0}
    obj.metadata = MagicMock()
    obj.metadata.score = score
    return obj


@pytest.mark.asyncio
async def test_hybrid_search_returns_enriched_chunks():
    weaviate_client = MagicMock()
    collection_mock = AsyncMock()
    weaviate_client.collections.get.return_value = collection_mock

    obj1 = _make_weaviate_obj("uuid-1", "Drug A interacts with Drug B", "proj-1", 0.9)
    obj2 = _make_weaviate_obj("uuid-2", "Ibuprofen and warfarin interaction", "proj-1", 0.7)
    collection_mock.query.hybrid = AsyncMock(return_value=MagicMock(objects=[obj1, obj2]))

    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=MagicMock())
    mongo_docs = [
        {
            "weaviate_id": "uuid-1",
            "document_id": "doc-1",
            "project_id": "proj-1",
            "chunk_index": 0,
            "page": 1,
            "filename": "drug_interactions.pdf",
        },
    ]

    async def fake_aggregate(pipeline):
        for doc in mongo_docs:
            yield doc

    db.__getitem__.return_value.aggregate = fake_aggregate

    request = RetrievalRequest(query="drug interaction", project_id="proj-1", top_k=10, alpha=0.5)
    result = await hybrid_search(request, weaviate_client, db)

    assert result.total == 2
    chunk1 = next(c for c in result.chunks if c.chunk_id == "uuid-1")
    assert chunk1.filename == "drug_interactions.pdf"
    assert chunk1.page == 1
    assert chunk1.score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_hybrid_search_empty_results():
    weaviate_client = MagicMock()
    collection_mock = AsyncMock()
    weaviate_client.collections.get.return_value = collection_mock
    collection_mock.query.hybrid = AsyncMock(return_value=MagicMock(objects=[]))

    db = MagicMock()

    async def fake_aggregate(pipeline):
        return
        yield

    db.__getitem__ = MagicMock(return_value=MagicMock(aggregate=fake_aggregate))

    request = RetrievalRequest(query="unknown query", project_id="proj-1")
    result = await hybrid_search(request, weaviate_client, db)

    assert result.total == 0
    assert result.chunks == []
