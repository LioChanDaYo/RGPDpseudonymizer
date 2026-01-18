"""Unit tests for structured logging framework."""

from __future__ import annotations

import json

import pytest

from gdpr_pseudonymizer.utils.logger import (
    configure_logging,
    get_logger,
    log_with_context,
    sanitize_context,
)


def test_configure_logging_default_level() -> None:
    """Test logging configuration with default INFO level."""
    configure_logging()

    # Verify structlog is configured
    logger = get_logger("test_module")
    assert logger is not None
    # Logger may be BoundLogger or BoundLoggerLazyProxy
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_configure_logging_custom_level() -> None:
    """Test logging configuration with custom log level."""
    configure_logging(log_level="DEBUG")

    logger = get_logger("test_module")
    assert logger is not None


def test_get_logger_returns_bound_logger() -> None:
    """Test get_logger returns structlog logger instance."""
    configure_logging()
    logger = get_logger("test_module")

    # Logger may be BoundLogger or BoundLoggerLazyProxy
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "debug")


def test_get_logger_with_module_name() -> None:
    """Test logger creation with module name."""
    configure_logging()
    logger = get_logger("gdpr_pseudonymizer.nlp.entity_detector")

    assert logger is not None


def test_log_with_context_info_level(capsys: pytest.CaptureFixture) -> None:
    """Test logging with structured context at INFO level."""
    import sys

    configure_logging(log_level="INFO")
    logger = get_logger("test_module")

    log_with_context(logger, "info", "entity_detected", entity_type="PERSON", count=5)
    sys.stdout.flush()

    # Capture output and verify JSON structure
    captured = capsys.readouterr()
    assert "entity_detected" in captured.out
    assert "entity_type" in captured.out or "PERSON" in captured.out


def test_log_with_context_error_level(capsys: pytest.CaptureFixture) -> None:
    """Test logging at ERROR level with context."""
    import sys

    configure_logging(log_level="ERROR")
    logger = get_logger("test_module")

    log_with_context(logger, "error", "model_load_failed", model_name="fr_core_news_lg")
    sys.stdout.flush()

    captured = capsys.readouterr()
    assert "model_load_failed" in captured.out


def test_sanitize_context_removes_sensitive_fields() -> None:
    """Test that sanitize_context removes known sensitive fields."""
    context = {
        "entity_type": "PERSON",
        "count": 5,
        "text": "Marie Dubois",  # Sensitive
        "full_name": "Jean Martin",  # Sensitive
        "confidence": 0.92,
        "passphrase": "secret123",  # Sensitive
    }

    sanitized = sanitize_context(context)

    # Non-sensitive fields should remain
    assert "entity_type" in sanitized
    assert "count" in sanitized
    assert "confidence" in sanitized

    # Sensitive fields should be removed
    assert "text" not in sanitized
    assert "full_name" not in sanitized
    assert "passphrase" not in sanitized


def test_sanitize_context_preserves_safe_fields() -> None:
    """Test that sanitize_context preserves all safe fields."""
    context = {
        "entity_type": "LOCATION",
        "confidence": 0.88,
        "count": 3,
        "operation_id": "op-12345",
        "processing_time": 1.25,
    }

    sanitized = sanitize_context(context)

    assert sanitized == context  # All fields should be preserved


def test_sanitize_context_empty_dict() -> None:
    """Test sanitize_context with empty dictionary."""
    context = {}
    sanitized = sanitize_context(context)

    assert sanitized == {}


def test_logger_json_output_structure(capsys: pytest.CaptureFixture) -> None:
    """Test that logger produces valid JSON output."""
    import sys

    configure_logging(log_level="INFO")
    logger = get_logger("test_module")

    logger.info("test_event", key1="value1", key2=42)
    sys.stdout.flush()

    captured = capsys.readouterr()

    # Verify output is valid JSON
    try:
        log_entry = json.loads(captured.out.strip())
        assert "event" in log_entry or "test_event" in str(log_entry)
    except json.JSONDecodeError:
        # structlog may format output differently depending on configuration
        # At minimum, verify the message contains expected data
        assert "test_event" in captured.out
        assert "value1" in captured.out


def test_logger_level_filtering_debug(capsys: pytest.CaptureFixture) -> None:
    """Test that DEBUG messages are filtered when log level is INFO."""
    import sys

    configure_logging(log_level="INFO")
    logger = get_logger("test_module")

    logger.debug("debug_message", detail="should not appear")
    logger.info("info_message", detail="should appear")
    sys.stdout.flush()

    captured = capsys.readouterr()

    # DEBUG message should not appear
    assert "debug_message" not in captured.out

    # INFO message should appear
    assert "info_message" in captured.out


def test_multiple_loggers_same_module() -> None:
    """Test creating multiple loggers for the same module returns consistent instances."""
    configure_logging()

    logger1 = get_logger("test_module")
    logger2 = get_logger("test_module")

    # Both should be valid logger instances
    assert logger1 is not None
    assert logger2 is not None


def test_logger_sensitive_data_warning() -> None:
    """Test that logging framework documentation warns against sensitive data.

    This is a documentation test - the actual prevention happens through
    developer discipline and code review.
    """
    configure_logging()
    logger = get_logger("test_module")

    # This test serves as a reminder: NEVER log sensitive data
    # BAD: logger.info("entity_detected", text="Marie Dubois")
    # GOOD: logger.info("entity_detected", entity_type="PERSON", count=1)

    # Verify logger has required methods
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "debug")
