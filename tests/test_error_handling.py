"""
Unit tests for error handling system
Tests custom exceptions and global exception handlers
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, HTTPException
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC
import json

from main import app
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
from error_handlers import (
    tomosu_exception_handler,
    authentication_exception_handler,
    authorization_exception_handler,
    resource_not_found_exception_handler,
    validation_exception_handler,
    rate_limit_exception_handler,
    service_unavailable_exception_handler,
    database_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from models.responses import ErrorResponse


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Mock request fixture"""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.__str__ = Mock(return_value="http://test.com/api/test")
    request.method = "GET"
    request.headers = {"user-agent": "test-agent"}
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


class TestCustomExceptions:
    """Test custom exception classes"""

    def test_tomosu_exception_base(self):
        """Test base TOMOSException"""
        exc = TOMOSException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"key": "value"},
        )

        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 400
        assert exc.details == {"key": "value"}
        assert str(exc) == "Test error"

    def test_authentication_error(self):
        """Test AuthenticationError"""
        exc = AuthenticationError("Invalid credentials")

        assert exc.message == "Invalid credentials"
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.status_code == 401

    def test_authorization_error(self):
        """Test AuthorizationError"""
        exc = AuthorizationError("Access denied")

        assert exc.message == "Access denied"
        assert exc.error_code == "AUTHORIZATION_ERROR"
        assert exc.status_code == 403

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError"""
        exc = ResourceNotFoundError("Post", "123")

        assert exc.message == "Post with ID '123' not found"
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == 404

    def test_resource_not_found_error_without_id(self):
        """Test ResourceNotFoundError without resource ID"""
        exc = ResourceNotFoundError("User")

        assert exc.message == "User not found"
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == 404

    def test_validation_error(self):
        """Test ValidationError"""
        field_errors = {"email": "Invalid format", "name": "Required"}
        exc = ValidationError("Validation failed", field_errors=field_errors)

        assert exc.message == "Validation failed"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 422
        assert exc.details["field_errors"] == field_errors

    def test_cache_error(self):
        """Test CacheError"""
        exc = CacheError("Cache failed", operation="initialization")

        assert exc.message == "Cache initialization operation failed"
        assert exc.error_code == "CACHE_ERROR"
        assert exc.status_code == 503

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError"""
        exc = ServiceUnavailableError("Service down", service="Database")

        assert exc.message == "Database service temporarily unavailable"
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.status_code == 503

    def test_database_error(self):
        """Test DatabaseError"""
        exc = DatabaseError("DB failed", operation="query")

        assert exc.message == "Database query operation failed"
        assert exc.error_code == "DATABASE_ERROR"
        assert exc.status_code == 500

    def test_rate_limit_error(self):
        """Test RateLimitError"""
        exc = RateLimitError("Too many requests", retry_after=60)

        assert exc.message == "Too many requests"
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60


class TestExceptionHandlers:
    """Test exception handler functions"""

    @pytest.mark.asyncio
    async def test_tomosu_exception_handler(self, mock_request):
        """Test TOMOSException handler"""
        exc = TOMOSException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"key": "value"},
        )

        response = await tomosu_exception_handler(mock_request, exc)

        assert response.status_code == 400
        content = json.loads(response.body)
        assert content["error_code"] == "TEST_ERROR"
        assert content["message"] == "Test error"
        assert content["details"] == {"key": "value"}
        assert "timestamp" in content

    @pytest.mark.asyncio
    async def test_authentication_exception_handler(self, mock_request):
        """Test AuthenticationError handler"""
        exc = AuthenticationError("Invalid token")

        response = await authentication_exception_handler(mock_request, exc)

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        content = json.loads(response.body)
        assert content["error_code"] == "AUTHENTICATION_ERROR"
        assert content["message"] == "Invalid token"

    @pytest.mark.asyncio
    async def test_authorization_exception_handler(self, mock_request):
        """Test AuthorizationError handler"""
        exc = AuthorizationError("Access denied")

        response = await authorization_exception_handler(mock_request, exc)

        assert response.status_code == 403
        content = json.loads(response.body)
        assert content["error_code"] == "AUTHORIZATION_ERROR"
        assert content["message"] == "Access denied"

    @pytest.mark.asyncio
    async def test_resource_not_found_exception_handler(self, mock_request):
        """Test ResourceNotFoundError handler"""
        exc = ResourceNotFoundError("Post", "123")

        response = await resource_not_found_exception_handler(mock_request, exc)

        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["error_code"] == "RESOURCE_NOT_FOUND"
        assert content["message"] == "Post with ID '123' not found"

    @pytest.mark.asyncio
    async def test_rate_limit_exception_handler(self, mock_request):
        """Test RateLimitError handler"""
        exc = RateLimitError("Too many requests", retry_after=60)

        response = await rate_limit_exception_handler(mock_request, exc)

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
        content = json.loads(response.body)
        assert content["error_code"] == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_service_unavailable_exception_handler(self, mock_request):
        """Test ServiceUnavailableError handler"""
        exc = ServiceUnavailableError("Service down")

        response = await service_unavailable_exception_handler(mock_request, exc)

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "60"
        content = json.loads(response.body)
        assert content["error_code"] == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTPException handler"""
        exc = HTTPException(status_code=404, detail="Not found")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["error_code"] == "RESOURCE_NOT_FOUND"
        assert content["message"] == "Not found"

    @pytest.mark.asyncio
    async def test_general_exception_handler(self, mock_request):
        """Test general Exception handler"""
        exc = Exception("Unexpected error")

        with patch("error_handlers.logger") as mock_logger:
            response = await general_exception_handler(mock_request, exc)

        assert response.status_code == 500
        content = json.loads(response.body)
        assert content["error_code"] == "INTERNAL_SERVER_ERROR"
        assert content["message"] == "An unexpected error occurred"
        mock_logger.error.assert_called_once()


class TestErrorHandlingIntegration:
    """Test error handling integration with API endpoints"""

    def test_authentication_error_integration(self, client):
        """Test authentication error in protected endpoint"""
        # Try to create a post without authentication
        response = client.post(
            "/api/v1/posts", json={"content": "Test post", "tags": []}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "AUTHENTICATION_ERROR"
        assert "Authentication required" in data["message"]
        assert "timestamp" in data

    @patch("cache.manager.cache_manager.is_initialized")
    @patch("cache.manager.cache_manager.get_post_by_id")
    def test_resource_not_found_integration(
        self, mock_get_post, mock_is_initialized, client
    ):
        """Test resource not found error"""
        mock_is_initialized.return_value = True
        mock_get_post.return_value = None

        # Try to get a non-existent post
        response = client.get("/api/v1/posts/99999")

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
        assert "Post with ID '99999' not found" in data["message"]

    def test_validation_error_integration(self, client):
        """Test validation error with invalid data"""
        # Try to get posts with invalid pagination parameters
        response = client.get("/api/v1/posts?skip=-1&limit=0")

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "validation" in data["message"].lower()

    @patch("cache.manager.cache_manager.is_initialized")
    def test_service_unavailable_integration(self, mock_is_initialized, client):
        """Test service unavailable error when cache is not initialized"""
        mock_is_initialized.return_value = False

        response = client.get("/api/v1/posts")

        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert (
            "cache" in data["message"].lower()
            and "unavailable" in data["message"].lower()
        )

    def test_health_check_error_handling(self, client):
        """Test health check endpoint error handling"""
        with patch("cache.manager.cache_manager.is_initialized") as mock_is_initialized:
            mock_is_initialized.return_value = False

            response = client.get("/")

            assert response.status_code == 503
            data = response.json()
            assert data["error_code"] == "SERVICE_UNAVAILABLE"

    def test_detailed_health_check_success(self, client):
        """Test detailed health check success"""
        with (
            patch("cache.manager.cache_manager.is_initialized") as mock_is_initialized,
            patch("main.SessionLocal") as mock_session_local,
        ):
            mock_is_initialized.return_value = True

            # Mock database session
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.execute.return_value = None
            mock_db.close.return_value = None

            response = client.get("/api/v1/system/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "components" in data
            assert "cache" in data["components"]
            assert "database" in data["components"]

    def test_system_metrics_endpoint(self, client):
        """Test system metrics endpoint"""
        with (
            patch("cache.manager.cache_manager.is_initialized") as mock_is_initialized,
            patch("cache.manager.cache_manager.get_cache_stats") as mock_get_stats,
        ):
            mock_is_initialized.return_value = True
            mock_get_stats.return_value = {
                "posts_count": 100,
                "users_count": 50,
                "memory_usage": "10MB",
            }

            response = client.get("/api/v1/system/metrics")

            assert response.status_code == 200
            data = response.json()
            assert "cache" in data
            assert "system" in data
            assert data["cache"]["posts_count"] == 100


class TestErrorResponseModel:
    """Test ErrorResponse model"""

    def test_error_response_creation(self):
        """Test ErrorResponse model creation"""
        error = ErrorResponse(
            error_code="TEST_ERROR", message="Test message", details={"key": "value"}
        )

        assert error.error_code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details == {"key": "value"}
        assert isinstance(error.timestamp, datetime)

    def test_error_response_serialization(self):
        """Test ErrorResponse model serialization"""
        error = ErrorResponse(error_code="TEST_ERROR", message="Test message")

        data = error.model_dump()

        assert data["error_code"] == "TEST_ERROR"
        assert data["message"] == "Test message"
        assert data["details"] is None
        assert isinstance(data["timestamp"], str)  # Should be serialized as ISO string


class TestLoggingIntegration:
    """Test logging integration with error handling"""

    @pytest.mark.asyncio
    async def test_error_logging(self, mock_request):
        """Test that errors are properly logged"""
        exc = TOMOSException(
            message="Test error", error_code="TEST_ERROR", status_code=500
        )

        with patch("error_handlers.logger") as mock_logger:
            await tomosu_exception_handler(mock_request, exc)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "TEST_ERROR" in call_args[0][0]
            assert "Test error" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_general_exception_logging(self, mock_request):
        """Test that general exceptions are logged with stack trace"""
        exc = Exception("Unexpected error")

        with patch("error_handlers.logger") as mock_logger:
            await general_exception_handler(mock_request, exc)

            mock_logger.error.assert_called_once()
            # Check that exc_info=True was passed for stack trace
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs.get("exc_info") is True
