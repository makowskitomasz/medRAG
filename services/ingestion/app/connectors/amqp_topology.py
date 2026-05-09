"""RabbitMQ topology: exchanges, queues, bindings, DLX."""

import aio_pika

EXCHANGE = "documents"
DLX_EXCHANGE = "documents.dlx"

QUEUES = {
    "parser.queue": "document.uploaded",
    "chunking.queue": "document.parsed",
    "embedding.queue": "document.chunked",
    "indexing.queue": "chunks.embedded",
    "eval.queue": "query.completed",
}


async def setup_topology(channel: aio_pika.abc.AbstractChannel) -> None:
    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    dlx = await channel.declare_exchange(DLX_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    for queue_name, routing_key in QUEUES.items():
        failed_queue_name = f"{queue_name}.failed"

        await channel.declare_queue(failed_queue_name, durable=True)
        failed_q = await channel.declare_queue(failed_queue_name, durable=True)
        await failed_q.bind(dlx, routing_key=routing_key)

        q = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": DLX_EXCHANGE,
                "x-dead-letter-routing-key": routing_key,
            },
        )
        await q.bind(exchange, routing_key=routing_key)
