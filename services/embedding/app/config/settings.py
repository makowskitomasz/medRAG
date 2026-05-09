from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "embedding"

    embedding_provider: str = "local_bge"
    bge_model_name: str = "BAAI/bge-m3"
    embedding_batch_size: int = 32


settings = Settings()
