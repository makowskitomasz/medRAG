from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "ingestion"
    upload_dir: str = "/tmp/uploads"
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt"]
    max_file_size_mb: int = 50


settings = Settings()
