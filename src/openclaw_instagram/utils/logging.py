"""Structured logging setup with file output to logs/ directory."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import structlog


def setup_logging(level: str = "INFO", log_dir: Path | None = None) -> None:
    """Configure structured logging with console + optional JSON file output."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    # Console always gets pretty output
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # File gets JSON lines for machine parsing
    if log_dir:
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        log_file = log_dir / f"agent-{today}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        json_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
        )
        file_handler.setFormatter(json_formatter)

        root = logging.getLogger()
        root.setLevel(log_level)
        root.addHandler(file_handler)
