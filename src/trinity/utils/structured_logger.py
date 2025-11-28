"""
Structured Logger for Trinity

Provides structured JSON logging with context, correlation IDs, and performance tracking.
Designed for log aggregation systems (ELK, Datadog, CloudWatch, etc.).

Usage:
    from trinity.utils.structured_logger import get_logger

    logger = get_logger(__name__)

    # Simple logging
    logger.info("content_generated")

    # Structured context
    logger.info("llm_request", extra={
        "theme": "brutalist",
        "model": "gemini-2.0-flash-exp",
        "tokens": 1500,
        "duration_ms": 234
    })

    # With correlation ID
    with logger.correlation_context("req-123"):
        logger.info("processing_started")
        # ... work ...
        logger.info("processing_completed")

Phase 6, Task 6: Structured Logging
"""

import json
import logging
import logging.config
import os
import sys
import uuid
from contextvars import ContextVar, Token
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, cast

# Correlation ID context
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON objects with consistent schema for easy parsing.
    """

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        correlation_id = _correlation_id.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add structured extra fields
        if self.include_extra and hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add any other extra attributes (backward compatibility)
        reserved_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "extra_fields",
        }

        for key, value in record.__dict__.items():
            if key not in reserved_attrs and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.

    Colored output with structured context inline.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading."""
        # Color by level
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        # Base message
        message = (
            f"{color}{record.levelname:8}{reset} {timestamp} [{record.name}] {record.getMessage()}"
        )

        # Add correlation ID if present
        correlation_id = _correlation_id.get()
        if correlation_id:
            message += f" {color}[{correlation_id}]{reset}"

        # Add structured context
        if hasattr(record, "extra_fields") and record.extra_fields:
            context = " | ".join(f"{k}={v}" for k, v in record.extra_fields.items())
            message += f" {color}({context}){reset}"

        # Add exception if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


class StructuredLogger(logging.Logger):
    """
    Extended logger with structured context support.
    """

    def _log_with_context(
        self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any
    ) -> None:
        """Log with structured extra fields."""
        if extra:
            # Store extra fields in a dedicated attribute
            if "extra" not in kwargs:
                kwargs["extra"] = {}
            kwargs["extra"]["extra_fields"] = extra

        super()._log(level, msg, args, **kwargs)

    def debug(self, msg: str, extra: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Log debug message with optional structured context."""
        self._log_with_context(logging.DEBUG, msg, extra, *args, **kwargs)

    def info(self, msg: str, extra: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Log info message with optional structured context."""
        self._log_with_context(logging.INFO, msg, extra, *args, **kwargs)

    def warning(self, msg: str, extra: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Log warning message with optional structured context."""
        self._log_with_context(logging.WARNING, msg, extra, *args, **kwargs)

    def error(self, msg: str, extra: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Log error message with optional structured context."""
        self._log_with_context(logging.ERROR, msg, extra, *args, **kwargs)

    def critical(self, msg: str, extra: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Log critical message with optional structured context."""
        self._log_with_context(logging.CRITICAL, msg, extra, *args, **kwargs)

    def correlation_context(self, correlation_id: Optional[str] = None) -> "_CorrelationContext":
        """
        Context manager for correlation ID.

        Args:
            correlation_id: Optional correlation ID. Auto-generated if not provided.

        Usage:
            with logger.correlation_context("req-123"):
                logger.info("processing_started")
        """
        return _CorrelationContext(correlation_id)


class _CorrelationContext:
    """Context manager for correlation IDs."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        self.token: Optional[Token[Optional[str]]] = None

    def __enter__(self) -> str:
        self.token = _correlation_id.set(self.correlation_id)
        return self.correlation_id

    def __exit__(self, *args: Any) -> None:
        if self.token:
            _correlation_id.reset(self.token)


# Set custom logger class
logging.setLoggerClass(StructuredLogger)


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured StructuredLogger instance

    Example:
        logger = get_logger(__name__)
        logger.info("server_started", extra={"port": 8000})
    """
    return cast(StructuredLogger, logging.getLogger(name))


def configure_logging(
    level: str = "INFO",
    log_format: str = "human",  # "human" or "json"
    log_file: Optional[Path] = None,
    config_file: Optional[Path] = None,
) -> None:
    """
    Configure logging system.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("human" for development, "json" for production)
        log_file: Optional file path for file logging
        config_file: Optional YAML config file path

    Example:
        # Development (human-readable)
        configure_logging(level="DEBUG", log_format="human")

        # Production (JSON for log aggregation)
        configure_logging(level="INFO", log_format="json", log_file=Path("logs/app.log"))
    """
    # Use config file if provided
    if config_file and config_file.exists():
        import yaml

        with open(config_file) as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
        return

    # Manual configuration
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Choose formatter
    formatter: logging.Formatter
    if log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        # Always use JSON for file output
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def setup_default_logging() -> None:
    """
    Setup default logging based on environment.

    Uses LOG_LEVEL, LOG_FORMAT, and LOG_FILE environment variables if set.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = os.getenv("LOG_FORMAT", "human")  # "human" or "json"
    log_file = os.getenv("LOG_FILE")

    configure_logging(
        level=log_level, log_format=log_format, log_file=Path(log_file) if log_file else None
    )


# Auto-configure on import (can be overridden)
if not logging.getLogger().handlers:
    setup_default_logging()
