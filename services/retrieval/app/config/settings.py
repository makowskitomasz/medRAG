from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "retrieval"
    weaviate_url: str = "http://weaviate:8080"
    weaviate_collection: str = "Chunk"
    embedding_service_url: str = "http://embedding:8000"


settings = Settings()
