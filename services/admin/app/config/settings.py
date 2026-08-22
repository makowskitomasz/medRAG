from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "admin"
    weaviate_url: str = "http://weaviate:8080"
    weaviate_collection: str = "Chunk"


settings = Settings()
