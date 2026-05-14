import httpx
from medrag_shared.models.project import RagMode

from app.pipelines.base import RagPipeline
from app.pipelines.corrective_rag import CorrectiveRagPipeline
from app.pipelines.hyde import HydePipeline
from app.pipelines.multi_agent import MultiAgentPipeline
from app.pipelines.query_rewriting import QueryRewritingPipeline
from app.pipelines.self_reflection import SelfReflectionPipeline
from app.pipelines.vanilla import VanillaPipeline

_PIPELINE_MAP = {
    RagMode.VANILLA: VanillaPipeline,
    RagMode.HYDE: HydePipeline,
    RagMode.QUERY_REWRITING: QueryRewritingPipeline,
    RagMode.SELF_REFLECTION: SelfReflectionPipeline,
    RagMode.MULTI_AGENT: MultiAgentPipeline,
    RagMode.CORRECTIVE_RAG: CorrectiveRagPipeline,
}


def get_pipeline(rag_mode: RagMode, http_client: httpx.AsyncClient, settings) -> RagPipeline:  # type: ignore[type-arg]
    pipeline_cls = _PIPELINE_MAP.get(rag_mode, VanillaPipeline)
    return pipeline_cls(http_client, settings)
