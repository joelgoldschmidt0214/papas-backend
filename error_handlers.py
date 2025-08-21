"""
Global exception handlers for TOMOSU Backend API
Provides consistent error response formatting and logging
"""

import logging
from typing import Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, UTC

from models.responses import ErrorResponse
from exceptions import (
    TOMOSException,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
    CacheError,
    ServiceUnavailableError,
    DatabaseError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


async def tomosu_exception_handler(
    request: Request, exc: TOMOSException
) -> JSONResponse:
    """
    Handle custom TOMOSU exceptions
    """
    logger.warning(
        f"TOMOSU Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": str(request.url),
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
    )


async def authentication_exception_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """
    Handle authentication errors (401)
    """
    logger.warning(
        f"Authentication error: {exc.message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
        },
    )

    return JSONResponse(
        status_code=401,
        content=ErrorResponse(
            error_code="AUTHENTICATION_ERROR",
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authorization_exception_handler(
    request: Request, exc: AuthorizationError
) -> JSONResponse:
    """
    Handle authorization errors (403)
    """
    logger.warning(
        f"Authorization error: {exc.message}",
        extra={"path": str(request.url), "method": request.method},
    )

    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            error_code="AUTHORIZATION_ERROR",
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
    )


async def resource_not_found_exception_handler(
    request: Request, exc: ResourceNotFoundError
) -> JSONResponse:
    """
    Handle resource not found errors (404)
    """
    logger.info(
        f"Resource not found: {exc.message}",
        extra={"path": str(request.url), "method": request.method},
    )

    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error_code="RESOURCE_NOT_FOUND",
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[ValidationError, RequestValidationError, PydanticValidationError],
) -> JSONResponse:
    """
    Handle validation errors (422)
    """
    if isinstance(exc, ValidationError):
        # Custom validation error
        error_details = exc.details
        message = exc.message
    elif isinstance(exc, RequestValidationError):
        # FastAPI request validation error
        error_details = {"validation_errors": exc.errors()}
        message = "Request validation failed"
    else:
        # Pydantic validation error
        error_details = {"validation_errors": exc.errors()}
        message = "Data validation failed"

    logger.warning(
        f"Validation error: {message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "validation_errors": error_details,
        },
    )

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=message,
            details=error_details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
    )


async def rate_limit_exception_handler(
    request: Request, exc: RateLimitError
) -> JSONResponse:
    """
    Handle rate limit errors (429)
    """
    logger.warning(
        f"Rate limit exceeded: {exc.message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown",
        },
    )

    headers = {}
    if exc.details and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])

    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error_code="RATE_LIMIT_EXCEEDED",
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
        headers=headers,
    )


async def service_unavailable_exception_handler(
    request: Request, exc: Union[ServiceUnavailableError, CacheError]
) -> JSONResponse:
    """
    Handle service unavailable errors (503)
    """
    logger.error(
        f"Service unavailable: {exc.message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "error_details": exc.details,
        },
    )

    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
        headers={"Retry-After": "60"},  # Suggest retry after 60 seconds
    )


async def database_exception_handler(
    request: Request, exc: Union[DatabaseError, SQLAlchemyError]
) -> JSONResponse:
    """
    Handle database errors (500)
    """
    if isinstance(exc, DatabaseError):
        error_code = exc.error_code
        message = exc.message
        details = exc.details
    else:
        # SQLAlchemy error
        error_code = "DATABASE_ERROR"
        message = "Database operation failed"
        details = {"database_error": str(exc)}

    logger.error(
        f"Database error: {message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "error_details": details,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=error_code,
            message=message,
            details=details,
            timestamp=datetime.now(UTC),
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTP exceptions
    """
    # Map common HTTP status codes to appropriate error codes
    error_code_mapping = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_ERROR",
        403: "AUTHORIZATION_ERROR",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_mapping.get(exc.status_code, f"HTTP_{exc.status_code}")

    # Log based on severity
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "path": str(request.url),
                "method": request.method,
                "status_code": exc.status_code,
            },
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "path": str(request.url),
                "method": request.method,
                "status_code": exc.status_code,
            },
        )

    headers = getattr(exc, "headers", None)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=error_code, message=exc.detail, timestamp=datetime.now(UTC)
        ).model_dump(),
        headers=headers,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions (500)
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            timestamp=datetime.now(UTC),
        ).model_dump(),
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app
    """
    # Custom TOMOSU exceptions
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(AuthorizationError, authorization_exception_handler)
    app.add_exception_handler(
        ResourceNotFoundError, resource_not_found_exception_handler
    )
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitError, rate_limit_exception_handler)
    app.add_exception_handler(
        ServiceUnavailableError, service_unavailable_exception_handler
    )
    app.add_exception_handler(CacheError, service_unavailable_exception_handler)
    app.add_exception_handler(DatabaseError, database_exception_handler)
    app.add_exception_handler(TOMOSException, tomosu_exception_handler)

    # Standard exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
