import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import ExchangeType, Message

_connection: aio_pika.abc.AbstractConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None


async def connect(url: str) -> None:
    global _connection, _channel
    _connection = await aio_pika.connect_robust(url)
    _channel = await _connection.channel()
    await _channel.set_qos(prefetch_count=1)


async def disconnect() -> None:
    global _connection, _channel
    if _connection:
        await _connection.close()
        _connection = None
        _channel = None


async def publish(
    exchange_name: str,
    routing_key: str,
    payload: dict[str, Any],
    trace_id: str | None = None,
) -> None:
    if _channel is None:
        raise RuntimeError("AMQP channel not initialized — call connect() first")
    exchange = await _channel.declare_exchange(exchange_name, ExchangeType.TOPIC, durable=True)
    headers = {"x-trace-id": trace_id} if trace_id else {}
    message = Message(
        body=json.dumps(payload).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        headers=headers,
    )
    await exchange.publish(message, routing_key=routing_key)


async def consume(
    queue_name: str,
    handler: Callable[[dict[str, Any], str | None], Awaitable[None]],
) -> None:
    if _channel is None:
        raise RuntimeError("AMQP channel not initialized — call connect() first")
    queue = await _channel.declare_queue(queue_name, durable=True, passive=True)
    async with queue.iterator() as it:
        async for message in it:
            async with message.process():
                payload = json.loads(message.body)
                trace_id = (message.headers or {}).get("x-trace-id")
                await handler(payload, trace_id)
