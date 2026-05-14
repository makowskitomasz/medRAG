from unittest.mock import MagicMock

from medrag_shared.models.project import RagMode

from app.pipelines.factory import get_pipeline
from app.pipelines.hyde import HydePipeline
from app.pipelines.vanilla import VanillaPipeline


def _mock_deps():
    return MagicMock(), MagicMock()


def test_vanilla_mode_returns_vanilla_pipeline():
    http, settings = _mock_deps()
    pipeline = get_pipeline(RagMode.VANILLA, http, settings)
    assert isinstance(pipeline, VanillaPipeline)


def test_hyde_mode_returns_hyde_pipeline():
    http, settings = _mock_deps()
    pipeline = get_pipeline(RagMode.HYDE, http, settings)
    assert isinstance(pipeline, HydePipeline)


def test_self_reflection_falls_back_to_vanilla():
    http, settings = _mock_deps()
    pipeline = get_pipeline(RagMode.SELF_REFLECTION, http, settings)
    assert isinstance(pipeline, VanillaPipeline)


def test_multi_agent_falls_back_to_vanilla():
    http, settings = _mock_deps()
    pipeline = get_pipeline(RagMode.MULTI_AGENT, http, settings)
    assert isinstance(pipeline, VanillaPipeline)
