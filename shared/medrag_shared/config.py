from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "medrag-service"
    log_level: str = "INFO"

    mongodb_uri: str = "mongodb://mongo:27017/medrag"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
