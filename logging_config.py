"""
Logging configuration for TOMOSU Backend API.

Provides environment-specific logging setup with proper formatting,
rotation, and structured logging for production environments.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from config import Settings, Environment


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs for production
    and human-readable logs for development.
    """

    def __init__(self, environment: Environment):
        self.environment = environment
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record based on environment"""
        if self.environment == Environment.PRODUCTION:
            return self._format_json(record)
        else:
            return self._format_human_readable(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for production"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
                if record.exc_info
                else None,
            }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add request context if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "response_time"):
            log_data["response_time"] = record.response_time

        return json.dumps(log_data, ensure_ascii=False)

    def _format_human_readable(self, record: logging.LogRecord) -> str:
        """Format log record for human readability in development"""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Base format
        message = f"{timestamp} | {record.levelname:8} | {record.name:20} | {record.getMessage()}"

        # Add request context if available
        context_parts = []
        if hasattr(record, "request_id"):
            context_parts.append(f"req_id={record.request_id}")
        if hasattr(record, "user_id"):
            context_parts.append(f"user_id={record.user_id}")
        if hasattr(record, "endpoint"):
            context_parts.append(f"endpoint={record.endpoint}")
        if hasattr(record, "method"):
            context_parts.append(f"method={record.method}")
        if hasattr(record, "status_code"):
            context_parts.append(f"status={record.status_code}")
        if hasattr(record, "response_time") and record.response_time is not None:
            context_parts.append(f"time={record.response_time:.3f}s")

        if context_parts:
            message += f" | {' '.join(context_parts)}"

        # Add location info for debug level
        if record.levelno == logging.DEBUG:
            message += f" | {record.module}:{record.funcName}:{record.lineno}"

        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


class RequestContextFilter(logging.Filter):
    """
    Filter to add request context to log records.
    This would typically be populated by middleware.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record if available"""
        # In a real application, this would extract context from
        # request-local storage or context variables
        # For now, we'll just ensure the attributes exist

        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "user_id"):
            record.user_id = None
        if not hasattr(record, "endpoint"):
            record.endpoint = None
        if not hasattr(record, "method"):
            record.method = None
        if not hasattr(record, "status_code"):
            record.status_code = None
        if not hasattr(record, "response_time"):
            record.response_time = None

        return True


def setup_logging(settings: Settings) -> None:
    """
    Set up logging configuration based on settings.

    Args:
        settings: Application settings instance
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(getattr(logging, settings.log_level.value))

    # Create formatter
    formatter = StructuredFormatter(settings.environment)

    # Create request context filter
    context_filter = RequestContextFilter()

    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    root_logger.addHandler(console_handler)

    # Set up file handler if log file is specified
    if settings.log_file:
        log_file_path = Path(settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler to prevent log files from growing too large
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=settings.log_max_size,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    configure_logger_levels(settings)

    # Log configuration info
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Level: {settings.log_level.value}, "
        f"Environment: {settings.environment.value}, "
        f"File: {settings.log_file or 'stdout only'}"
    )


def configure_logger_levels(settings: Settings) -> None:
    """Configure specific logger levels based on environment"""

    # Application loggers
    app_loggers = [
        "main",
        "cache.manager",
        "auth.manager",
        "api",
        "db_control",
    ]

    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        if settings.is_development:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    # Third-party library loggers
    third_party_configs = {
        "uvicorn": logging.INFO,
        "uvicorn.access": logging.INFO if settings.is_production else logging.DEBUG,
        "fastapi": logging.INFO,
        "sqlalchemy.engine": logging.WARNING if not settings.db_echo else logging.INFO,
        "sqlalchemy.pool": logging.WARNING,
        "sqlalchemy.dialects": logging.WARNING,
        "httpx": logging.WARNING,
        "urllib3": logging.WARNING,
    }

    for logger_name, level in third_party_configs.items():
        logging.getLogger(logger_name).setLevel(level)

    # In production, be more restrictive with third-party logs
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds request context to log records.
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message and add extra context"""
        # Add extra fields to the log record
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Merge adapter extra with call-specific extra
        kwargs["extra"].update(self.extra)

        return msg, kwargs

    def with_context(self, **context) -> "LoggerAdapter":
        """Create a new adapter with additional context"""
        new_extra = self.extra.copy()
        new_extra.update(context)
        return LoggerAdapter(self.logger, new_extra)


def get_logger_with_context(name: str, **context) -> LoggerAdapter:
    """
    Get a logger adapter with request context.

    Args:
        name: Logger name
        **context: Additional context to include in logs

    Returns:
        Logger adapter with context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)


# Utility functions for common logging patterns


def log_api_request(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    user_id: Optional[int] = None,
    request_id: Optional[str] = None,
):
    """Log API request start"""
    extra = {
        "method": method,
        "endpoint": endpoint,
        "user_id": user_id,
        "request_id": request_id,
        "event_type": "api_request_start",
    }
    logger.info(f"API Request: {method} {endpoint}", extra=extra)


def log_api_response(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: int,
    response_time: float,
    user_id: Optional[int] = None,
    request_id: Optional[str] = None,
):
    """Log API response"""
    extra = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time": response_time,
        "user_id": user_id,
        "request_id": request_id,
        "event_type": "api_response",
    }
    logger.info(
        f"API Response: {method} {endpoint} - {status_code} ({response_time:.3f}s)",
        extra=extra,
    )


def log_cache_operation(
    logger: logging.Logger, operation: str, cache_type: str, key: str, hit: bool = None
):
    """Log cache operation"""
    extra = {
        "operation": operation,
        "cache_type": cache_type,
        "cache_key": key,
        "cache_hit": hit,
        "event_type": "cache_operation",
    }

    if hit is not None:
        result = "HIT" if hit else "MISS"
        logger.debug(f"Cache {operation}: {cache_type}[{key}] - {result}", extra=extra)
    else:
        logger.debug(f"Cache {operation}: {cache_type}[{key}]", extra=extra)


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    duration: float,
    rows_affected: int = None,
):
    """Log database operation"""
    extra = {
        "operation": operation,
        "table": table,
        "duration": duration,
        "rows_affected": rows_affected,
        "event_type": "database_operation",
    }

    message = f"DB {operation}: {table} ({duration:.3f}s)"
    if rows_affected is not None:
        message += f" - {rows_affected} rows"

    logger.debug(message, extra=extra)


def log_error(
    logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None
):
    """Log error with context"""
    extra = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "event_type": "error",
    }

    if context:
        extra.update(context)

    logger.error(
        f"Error: {type(error).__name__}: {str(error)}", extra=extra, exc_info=True
    )
