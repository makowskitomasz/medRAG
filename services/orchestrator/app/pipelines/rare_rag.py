from collections.abc import AsyncGenerator

from medrag_shared import get_logger

from app.pipelines.base import RagPipeline
from app.schemas.orchestrator_schemas import QueryResponse

logger = get_logger(__name__)

# Claim-level grounding threshold τ (thesis §3.6). Kept at 0.3: on the DDI faithfulness
# distribution τ=0.5 would abstain on ~21% of questions versus ~10% here.
_GROUNDING_THRESHOLD = 0.3
_ABSTENTION_RETRY_SCORE = 0.3

_ROUTE_TO_MODE = {
    "vanilla": "vanilla",
    "hyde": "hyde",
    "query_rewriting": "query_rewriting",
    "self_reflection": "self_reflection",
    "multi_agent": "multi_agent",
    "corrective_rag": "corrective_rag",
    "iterative_multihop": "iterative_multihop",
    "madam_rag": "madam_rag",
}


class RareRagPipeline(RagPipeline):
    async def _triage(self, query: str) -> str:
        """Returns the routed rag_mode string."""
        try:
            data = await self._tracked_post(
                f"{self.settings.query_processor_url}/triage",
                {"query": query},
            )
            route = data.get("route", "vanilla")
            return _ROUTE_TO_MODE.get(route, "vanilla")
        except Exception as exc:
            logger.warning("rare_rag triage failed, defaulting to vanilla", error=str(exc))
            return "vanilla"

    def _get_sub_pipeline(self, mode: str) -> RagPipeline:
        # Import here to avoid circular imports.
        from medrag_shared.models.project import RagMode

        from app.pipelines.factory import get_pipeline

        try:
            rag_mode_enum = RagMode(mode)
        except ValueError:
            rag_mode_enum = RagMode.VANILLA
        sub = get_pipeline(rag_mode_enum, self.http, self.settings, self.prompt_overrides)
        sub.llm_model = self.llm_model
        sub.max_hops = self.max_hops
        # RARE's contribution over the routed mode: set-wise evidence selection after rerank.
        sub.setwise_selection = True
        return sub

    async def _run_with_grounding(
        self,
        query: str,
        project_id: str,
        conversation_id: str,
        conversation_history: list[dict],
        routed_mode: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> tuple[QueryResponse, float]:
        """Run sub-pipeline, verify claim-level grounding. Returns (response, score)."""
        pipeline = self._get_sub_pipeline(routed_mode)
        response = await pipeline.run(
            query=query,
            project_id=project_id,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            rag_mode=routed_mode,
            top_k=top_k,
            alpha=alpha,
            rerank_top_n=rerank_top_n,
        )
        # Propagate chunks and token usage from sub-pipeline
        self._last_chunks = pipeline._last_chunks
        self._last_input_tokens += pipeline._last_input_tokens
        self._last_output_tokens += pipeline._last_output_tokens

        try:
            score = await self._verify_claims(response.answer, self._last_chunks or [])
        except Exception as exc:
            # A verifier outage must not turn every answer into an abstention.
            logger.warning("rare_rag claim verification failed, accepting answer", error=str(exc))
            score = 1.0
        return response, score

    async def run(
        self,
        query: str,
        project_id: str,
        conversation_id: str,
        conversation_history: list[dict],
        rag_mode: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> QueryResponse:
        routed_mode = await self._triage(query)
        logger.info("rare_rag triage result", route=routed_mode)

        response, score = await self._run_with_grounding(
            query,
            project_id,
            conversation_id,
            conversation_history,
            routed_mode,
            top_k,
            alpha,
            rerank_top_n,
        )

        if score >= _GROUNDING_THRESHOLD:
            response.rag_mode = rag_mode
            return response

        # Retry with self_reflection for better grounding.
        logger.info("rare_rag low grounding score, retrying with self_reflection", score=score)
        response, score = await self._run_with_grounding(
            query,
            project_id,
            conversation_id,
            conversation_history,
            "self_reflection",
            top_k,
            alpha,
            rerank_top_n,
        )

        if score >= _ABSTENTION_RETRY_SCORE:
            response.rag_mode = rag_mode
            return response

        # Abstain.
        logger.info("rare_rag abstaining", final_score=score)
        return QueryResponse(
            conversation_id=conversation_id,
            answer=(
                "I cannot provide a reliable answer to this question "
                "based on the available sources. "
                "Please consult a qualified healthcare professional."
            ),
            citations=[],
            rag_mode=rag_mode,
            abstained=True,
        )

    async def run_stream(  # type: ignore[override]
        self,
        query: str,
        project_id: str,
        conversation_id: str,
        conversation_history: list[dict],
        rag_mode: str,
        top_k: int,
        alpha: float,
        rerank_top_n: int,
    ) -> AsyncGenerator[str, None]:
        import time as _time

        yield self._sse_think(
            step=0,
            label="Triage",
            text="Analysing the question to pick the best RAG strategy…",
            duration_ms=0,
        )
        t0 = _time.monotonic()
        routed_mode = await self._triage(query)
        logger.info("rare_rag triage result", route=routed_mode)
        yield self._sse_think(
            step=0,
            label="Triage",
            text=f"Routed to the '{routed_mode}' pipeline.",
            duration_ms=int((_time.monotonic() - t0) * 1000),
        )

        # Grounding check requires a full answer — run the routed pipeline non-streaming
        # first, then stream the pipeline that passed the check.
        yield self._sse_think(
            step=1,
            label="Grounding check",
            text=f"Running the '{routed_mode}' pipeline and scoring how well it is grounded…",
            duration_ms=0,
        )
        t1 = _time.monotonic()
        response, score = await self._run_with_grounding(
            query,
            project_id,
            conversation_id,
            conversation_history,
            routed_mode,
            top_k,
            alpha,
            rerank_top_n,
        )
        grounded = score >= _GROUNDING_THRESHOLD
        yield self._sse_think(
            step=1,
            label="Grounding check",
            text=(
                f"'{routed_mode}' answer scored {score:.2f} "
                f"(threshold {_GROUNDING_THRESHOLD}). "
                + ("Accepted." if grounded else "Too weak — retrying with self-reflection.")
            ),
            duration_ms=int((_time.monotonic() - t1) * 1000),
        )

        final_mode = routed_mode
        if not grounded:
            yield self._sse_think(
                step=2,
                label="Grounding recheck",
                text="Re-running the question through the self-reflection pipeline…",
                duration_ms=0,
            )
            t2 = _time.monotonic()
            response, score = await self._run_with_grounding(
                query,
                project_id,
                conversation_id,
                conversation_history,
                "self_reflection",
                top_k,
                alpha,
                rerank_top_n,
            )
            final_mode = "self_reflection"
            yield self._sse_think(
                step=2,
                label="Grounding recheck",
                text=(
                    f"Self-reflection answer scored {score:.2f} "
                    f"(abstention threshold {_ABSTENTION_RETRY_SCORE})."
                ),
                duration_ms=int((_time.monotonic() - t2) * 1000),
            )

        if score < _ABSTENTION_RETRY_SCORE:
            logger.info("rare_rag abstaining", final_score=score)
            yield self._sse_think(
                step=3,
                label="Abstention",
                text="No sufficiently grounded answer could be produced — abstaining.",
                duration_ms=0,
            )
            async for chunk in self._stream_text(
                "I cannot provide a reliable answer to this question "
                "based on the available sources. "
                "Please consult a qualified healthcare professional.",
                [],
                conversation_id,
                rag_mode,
            ):
                yield chunk
            return

        # The answer is already generated and grounded; replay it rather than
        # re-generating, which is what made this mode cost two full pipeline runs.
        yield self._sse_think(
            step=3,
            label="Answer accepted",
            text=f"Replaying the grounded '{final_mode}' answer.",
            duration_ms=0,
        )
        async for chunk in self._stream_text(
            response.answer, response.citations, conversation_id, rag_mode
        ):
            yield chunk
