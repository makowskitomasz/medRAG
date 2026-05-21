from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "eval"
    generation_url: str = "http://generation:8000"
    embedding_url: str = "http://embedding:8000"
    faithfulness_threshold: float = 0.5


settings = Settings()
