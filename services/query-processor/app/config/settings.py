from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "query-processor"

    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    openrouter_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"

    @property
    def resolved_api_key(self) -> str:
        return self.llm_api_key or self.openrouter_api_key


settings = Settings()
