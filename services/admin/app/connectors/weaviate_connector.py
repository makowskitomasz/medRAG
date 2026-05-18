import weaviate
import weaviate.classes as wvc

_client: weaviate.WeaviateClient | None = None


def get_client() -> weaviate.WeaviateClient:
    if _client is None:
        raise RuntimeError("Weaviate client not initialized")
    return _client


def connect(url: str) -> None:
    global _client
    host = url.replace("http://", "").replace("https://", "").split(":")[0]
    port = int(url.split(":")[-1]) if ":" in url else 8080
    _client = weaviate.connect_to_local(host=host, port=port)


def disconnect() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def delete_by_project(collection_name: str, project_id: str) -> int:
    client = get_client()
    collection = client.collections.get(collection_name)
    result = collection.data.delete_many(
        where=wvc.query.Filter.by_property("project_id").equal(project_id)
    )
    return result.successful
