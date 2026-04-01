"""Tests for the logging setup utility."""

from __future__ import annotations

import logging

from openclaw_instagram.utils.logging import setup_logging


def test_setup_logging_console_only(tmp_path):
    """setup_logging without log_dir configures console handler only."""
    setup_logging(level="INFO", log_dir=None)
    # Should not raise and logging should be configured
    import structlog
    logger = structlog.get_logger()
    # Just verify it doesn't crash
    assert logger is not None


def test_setup_logging_with_log_dir(tmp_path):
    """setup_logging with log_dir creates log file and handler."""
    setup_logging(level="DEBUG", log_dir=tmp_path)

    # Log directory should exist
    assert tmp_path.exists()

    # A log file should have been created
    log_files = list(tmp_path.glob("agent-*.log"))
    assert len(log_files) == 1


def test_setup_logging_creates_log_dir_if_missing(tmp_path):
    """setup_logging creates log dir if it doesn't exist."""
    new_dir = tmp_path / "nested" / "logs"
    assert not new_dir.exists()

    setup_logging(level="INFO", log_dir=new_dir)

    assert new_dir.exists()


def test_setup_logging_different_levels(tmp_path):
    """setup_logging accepts various log level strings."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        # Should not raise
        setup_logging(level=level, log_dir=None)


def test_setup_logging_invalid_level_defaults_to_info(tmp_path):
    """setup_logging with invalid level string falls back to INFO."""
    # getattr(logging, "INVALID", logging.INFO) returns logging.INFO
    setup_logging(level="INVALID_LEVEL", log_dir=None)
    # Should not raise


def test_setup_logging_file_handler_added(tmp_path):
    """setup_logging with log_dir adds a FileHandler to root logger."""
    # Clear any existing handlers first
    root = logging.getLogger()
    initial_handlers = list(root.handlers)

    setup_logging(level="INFO", log_dir=tmp_path)

    root = logging.getLogger()
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) >= 1

    # Cleanup: remove added handlers
    for h in root.handlers:
        if h not in initial_handlers:
            h.close()
            root.removeHandler(h)
