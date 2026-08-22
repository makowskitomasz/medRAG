"""Consumer for query.completed events from the `queries` exchange."""

import aio_pika
import httpx
from medrag_shared import get_logger

from app.services import eval_service

logger = get_logger(__name__)

_generation_url: str = ""
_embedding_url: str = ""
_http_client: httpx.AsyncClient | None = None


def configure(generation_url: str, embedding_url: str, client: httpx.AsyncClient) -> None:
    global _generation_url, _embedding_url, _http_client
    _generation_url = generation_url
    _embedding_url = embedding_url
    _http_client = client


async def handle_query_completed(payload: dict, trace_id: str | None) -> None:
    assert _http_client is not None, "consumer not configured"
    await eval_service.process_event(
        payload=payload,
        trace_id=trace_id,
        generation_url=_generation_url,
        embedding_url=_embedding_url,
        http_client=_http_client,
    )


async def setup_topology(channel: aio_pika.abc.AbstractChannel) -> None:
    """Declare queries exchange + eval.queue with DLX."""
    exchange = await channel.declare_exchange("queries", aio_pika.ExchangeType.TOPIC, durable=True)
    dlx = await channel.declare_exchange("queries.dlx", aio_pika.ExchangeType.TOPIC, durable=True)

    failed_q = await channel.declare_queue("eval.queue.failed", durable=True)
    await failed_q.bind(dlx, routing_key="query.completed")

    q = await channel.declare_queue(
        "eval.queue",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "queries.dlx",
            "x-dead-letter-routing-key": "query.completed",
        },
    )
    await q.bind(exchange, routing_key="query.completed")
