"""Structured logging setup."""

from __future__ import annotations

import logging
from pathlib import Path

import structlog


def setup_logging(level: str = "INFO", log_dir: Path | None = None) -> None:
    """Configure structured logging with optional file output."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if log_dir is None else structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
