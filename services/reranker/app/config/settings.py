from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "reranker"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"


settings = Settings()
