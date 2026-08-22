import httpx
from medrag_shared.models.project import RagMode

from app.pipelines.base import RagPipeline
from app.pipelines.corrective_rag import CorrectiveRagPipeline
from app.pipelines.hyde import HydePipeline
from app.pipelines.iterative_multihop import IterativeMultiHopPipeline
from app.pipelines.madam_rag import MadamRagPipeline
from app.pipelines.multi_agent import MultiAgentPipeline
from app.pipelines.query_rewriting import QueryRewritingPipeline
from app.pipelines.rare_rag import RareRagPipeline
from app.pipelines.self_reflection import SelfReflectionPipeline
from app.pipelines.vanilla import VanillaPipeline

_PIPELINE_MAP = {
    RagMode.VANILLA: VanillaPipeline,
    RagMode.HYDE: HydePipeline,
    RagMode.QUERY_REWRITING: QueryRewritingPipeline,
    RagMode.SELF_REFLECTION: SelfReflectionPipeline,
    RagMode.MULTI_AGENT: MultiAgentPipeline,
    RagMode.CORRECTIVE_RAG: CorrectiveRagPipeline,
    RagMode.ITERATIVE_MULTIHOP: IterativeMultiHopPipeline,
    RagMode.MADAM_RAG: MadamRagPipeline,
    RagMode.RARE_RAG: RareRagPipeline,
}


def get_pipeline(
    rag_mode: RagMode,
    http_client: httpx.AsyncClient,
    settings,  # type: ignore[type-arg]
    prompt_overrides: dict[str, str] | None = None,
) -> RagPipeline:
    pipeline_cls = _PIPELINE_MAP.get(rag_mode, VanillaPipeline)
    return pipeline_cls(http_client, settings, prompt_overrides)
