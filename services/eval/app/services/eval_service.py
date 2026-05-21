"""Orchestrates metric computation and persistence for a single query.completed event."""

import httpx
from medrag_shared import get_logger

from app.repositories import eval_repository
from app.services.metrics import citation_precision, cosine_similarity, exact_match, token_f1

logger = get_logger(__name__)


async def _faithfulness_score(
    query: str,
    answer: str,
    contexts: list[str],
    generation_url: str,
    client: httpx.AsyncClient,
) -> float:
    """LLM-as-judge: is the answer grounded in the provided contexts?"""
    chunks = [{"chunk_id": f"ctx_{i}", "content": c} for i, c in enumerate(contexts)]
    try:
        resp = await client.post(
            f"{generation_url}/evaluate",
            json={"query": query, "answer": answer, "chunks": chunks, "prompt_overrides": {}},
            timeout=30.0,
        )
        resp.raise_for_status()
        return float(resp.json().get("score", 0.0))
    except Exception as exc:
        logger.warning("faithfulness LLM call failed", error=str(exc))
        return 0.0


async def _answer_relevance_score(
    query: str,
    answer: str,
    embedding_url: str,
    client: httpx.AsyncClient,
) -> float:
    """BGE cosine similarity between query embedding and answer embedding."""
    try:
        resp = await client.post(
            f"{embedding_url}/embed",
            json={"texts": [query, answer]},
            timeout=30.0,
        )
        resp.raise_for_status()
        vectors = resp.json()["vectors"]
        return cosine_similarity(vectors[0], vectors[1])
    except Exception as exc:
        logger.warning("answer_relevance embedding call failed", error=str(exc))
        return 0.0


async def process_event(
    payload: dict,
    trace_id: str | None,
    generation_url: str,
    embedding_url: str,
    http_client: httpx.AsyncClient,
) -> None:
    query = payload.get("query", "")
    answer = payload.get("answer", "")
    rag_mode = payload.get("rag_mode", "unknown")
    project_id = payload.get("project_id", "")
    conversation_id = payload.get("conversation_id")
    citations: list[dict] = payload.get("citations", [])
    contexts: list[str] = payload.get("contexts", [])
    latency_ms: int = payload.get("latency_ms", 0)
    token_count: int = payload.get("token_count", 0)
    top_k: int = payload.get("top_k", 20)
    gold_answer: str | None = payload.get("gold_answer")

    if not query or not answer:
        logger.warning("skipping eval: missing query or answer")
        return

    # faithfulness always computed
    faith = await _faithfulness_score(query, answer, contexts, generation_url, http_client)

    metrics: dict = {
        "faithfulness": round(faith, 4),
        "latency_ms": latency_ms,
        "token_count": token_count,
        "citation_precision": round(citation_precision(len(citations), top_k), 4),
    }

    if gold_answer:
        eval_mode = "benchmark"
        metrics["token_f1"] = round(token_f1(answer, gold_answer), 4)
        metrics["em"] = round(exact_match(answer, gold_answer), 4)
        metrics["answer_relevance"] = round(
            await _answer_relevance_score(query, answer, embedding_url, http_client), 4
        )
    else:
        eval_mode = "production"
        # context_relevance: ratio of citation snippets to top_k (proxy without reranker scores)
        metrics["context_relevance"] = round(citation_precision(len(contexts), top_k), 4)

    await eval_repository.save(
        project_id=project_id,
        question=query,
        answer=answer,
        rag_mode=rag_mode,
        eval_mode=eval_mode,
        metrics=metrics,
        conversation_id=conversation_id,
        trace_id=trace_id,
    )
    logger.info(
        "eval result saved",
        rag_mode=rag_mode,
        eval_mode=eval_mode,
        faithfulness=metrics["faithfulness"],
    )
