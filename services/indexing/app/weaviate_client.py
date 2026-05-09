import weaviate
import weaviate.classes as wvc

_client: weaviate.WeaviateClient | None = None


def get_client() -> weaviate.WeaviateClient:
    if _client is None:
        raise RuntimeError("Weaviate client not initialized")
    return _client


async def connect(url: str, collection_name: str) -> None:
    global _client
    _client = weaviate.connect_to_local(
        host=url.replace("http://", "").split(":")[0],
        port=int(url.split(":")[-1]),
    )
    _ensure_collection(_client, collection_name)


def _ensure_collection(client: weaviate.WeaviateClient, name: str) -> None:
    if client.collections.exists(name):
        return
    client.collections.create(
        name=name,
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[
            wvc.config.Property(name="chunk_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="document_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="project_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="chunk_index", data_type=wvc.config.DataType.INT),
        ],
    )


def disconnect() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
