"""
Custom exception classes for TOMOSU Backend API
Provides specific exception types for different error scenarios
"""

from typing import Optional, Dict, Any


class TOMOSException(Exception):
    """Base exception class for TOMOSU application"""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(TOMOSException):
    """Raised when authentication fails"""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details,
        )


class AuthorizationError(TOMOSException):
    """Raised when user lacks permission for requested action"""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details,
        )


class ResourceNotFoundError(TOMOSException):
    """Raised when requested resource is not found"""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if resource_id:
            message = f"{resource_type} with ID '{resource_id}' not found"
        else:
            message = f"{resource_type} not found"

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details,
        )


class ValidationError(TOMOSException):
    """Raised when request data validation fails"""

    def __init__(
        self,
        message: str = "Request validation failed",
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if field_errors:
            details = details or {}
            details["field_errors"] = field_errors

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class CacheError(TOMOSException):
    """Raised when cache operations fail"""

    def __init__(
        self,
        message: str = "Cache operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if operation:
            message = f"Cache {operation} operation failed"

        super().__init__(
            message=message, error_code="CACHE_ERROR", status_code=503, details=details
        )


class ServiceUnavailableError(TOMOSException):
    """Raised when service is temporarily unavailable"""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if service:
            message = f"{service} service temporarily unavailable"

        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            details=details,
        )


class DatabaseError(TOMOSException):
    """Raised when database operations fail"""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if operation:
            message = f"Database {operation} operation failed"

        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )


class RateLimitError(TOMOSException):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if retry_after:
            details = details or {}
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
        )
