import httpx
from medrag_shared.models.project import RagMode

from app.pipelines.base import RagPipeline
from app.pipelines.hyde import HydePipeline
from app.pipelines.vanilla import VanillaPipeline


def get_pipeline(rag_mode: RagMode, http_client: httpx.AsyncClient, settings) -> RagPipeline:  # type: ignore[type-arg]
    if rag_mode == RagMode.HYDE:
        return HydePipeline(http_client, settings)
    return VanillaPipeline(http_client, settings)
