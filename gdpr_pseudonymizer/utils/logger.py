"""Structured logging framework using structlog.

This module configures and provides structured logging with JSON output,
context preservation, and strict rules against logging sensitive data.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Configure structlog processors
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(module_name: str) -> Any:
    """Create module-specific structured logger.

    CRITICAL SECURITY RULE: NEVER log sensitive data
    - Entity text (names, locations, organizations)
    - User input containing PII
    - Unencrypted mapping data

    GOOD logging examples:
        logger.info("entity_detected", entity_type="PERSON", confidence=0.92, count=5)
        logger.error("model_load_failed", model_name="fr_core_news_lg")

    BAD logging examples (NEVER DO THIS):
        logger.info("detected_name", text="Marie Dubois")  # LOGS SENSITIVE DATA!
        logger.debug("entity", full_name=entity.full_name)  # LOGS SENSITIVE DATA!

    Args:
        module_name: Name of module requesting logger (use __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(module_name)


def log_with_context(
    logger: structlog.stdlib.BoundLogger,
    level: str,
    message: str,
    **context: Any,
) -> None:
    """Log message with structured context.

    Helper function for logging with key-value context preservation.

    Args:
        logger: Structlog logger instance
        level: Log level (debug, info, warning, error)
        message: Log message (no sensitive data!)
        **context: Additional context key-value pairs (no sensitive data!)
    """
    log_method = getattr(logger, level.lower())
    log_method(message, **context)


def sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive fields from logging context.

    This function removes known sensitive fields to prevent accidental
    logging of PII or other sensitive information.

    Args:
        context: Context dictionary to sanitize

    Returns:
        Sanitized context dictionary
    """
    sensitive_fields = {
        "text",
        "full_name",
        "first_name",
        "last_name",
        "entity_text",
        "name",
        "user_input",
        "passphrase",
        "password",
        "key",
    }

    return {k: v for k, v in context.items() if k not in sensitive_fields}
