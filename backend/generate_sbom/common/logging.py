"""Structured logging configuration (NFR-5.3).

All logging uses ``structlog`` with a JSON renderer in production (and a console
renderer in local dev). Callers bind ``org_id``, ``task_id`` (where applicable),
and ``user_id`` as structured fields. ``print()`` and the stdlib ``logging``
module are never used for application output.
"""

from __future__ import annotations

import structlog

# structlog level threshold; 20 == INFO (avoids importing the stdlib logging module).
_INFO_LEVEL = 20


def configure_structlog(*, json_logs: bool) -> None:
    """Configure structlog process-wide.

    Args:
        json_logs: When ``True`` render each entry as a single JSON line
            (production); when ``False`` use the human-friendly console renderer
            (local dev).
    """
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_INFO_LEVEL),
        cache_logger_on_first_use=False,
    )
