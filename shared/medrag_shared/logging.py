import logging

import structlog


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(level=logging.INFO)
    return structlog.get_logger(name)


def bind_trace_id(trace_id: str) -> None:
    structlog.contextvars.bind_contextvars(trace_id=trace_id)


def clear_trace_id() -> None:
    structlog.contextvars.clear_contextvars()
