from medrag_shared.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "orchestrator"

    retrieval_url: str = "http://retrieval:8000"
    reranker_url: str = "http://reranker:8000"
    generation_url: str = "http://generation:8000"
    query_processor_url: str = "http://query-processor:8000"

    # Env aliases from .env.example (docker service names)
    retrieval_service_url: str | None = None
    reranker_service_url: str | None = None
    generation_service_url: str | None = None
    query_processor_service_url: str | None = None

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if self.retrieval_service_url:
            object.__setattr__(self, "retrieval_url", self.retrieval_service_url)
        if self.reranker_service_url:
            object.__setattr__(self, "reranker_url", self.reranker_service_url)
        if self.generation_service_url:
            object.__setattr__(self, "generation_url", self.generation_service_url)
        if self.query_processor_service_url:
            object.__setattr__(self, "query_processor_url", self.query_processor_service_url)


settings = Settings()
