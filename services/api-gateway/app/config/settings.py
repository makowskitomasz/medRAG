from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "api-gateway"

    auth_url: str = "http://auth:8001"
    orchestrator_url: str = "http://orchestrator:8002"
    ingestion_url: str = "http://ingestion:8007"
    admin_url: str = "http://admin:8012"


settings = Settings()
