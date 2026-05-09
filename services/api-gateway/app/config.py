from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "api-gateway"

    auth_url: str = "http://auth:8000"
    orchestrator_url: str = "http://orchestrator:8000"
    ingestion_url: str = "http://ingestion:8000"
    admin_url: str = "http://admin:8000"


settings = Settings()
