from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "embedding"

    embedding_provider: str = "openai"
    bge_model_name: str = "BAAI/bge-m3"
    embedding_batch_size: int = 32

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"


settings = Settings()
