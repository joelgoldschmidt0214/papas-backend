"""
Integration tests for Pydantic models with FastAPI
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, UTC

from main import app
from models import UserResponse, PostResponse, ErrorResponse


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


class TestModelsIntegration:
    """Test Pydantic models integration with FastAPI"""

    def test_app_starts_successfully(self, client):
        """Test that the FastAPI app starts with new models"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "TOMOSU Backend API is running"
        assert data["status"] == "healthy"

    def test_error_response_serialization(self):
        """Test ErrorResponse model serialization"""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message",
            details={"field": "value"},
        )

        # Test JSON serialization
        json_data = error.model_dump()
        assert json_data["error_code"] == "TEST_ERROR"
        assert json_data["message"] == "Test error message"
        assert json_data["details"]["field"] == "value"
        assert "timestamp" in json_data

    def test_user_response_serialization(self):
        """Test UserResponse model serialization"""
        user = UserResponse(
            user_id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Test JSON serialization
        json_data = user.model_dump()
        assert json_data["user_id"] == 1
        assert json_data["username"] == "testuser"
        assert json_data["email"] == "test@example.com"
        assert json_data["display_name"] is None

    def test_post_response_with_nested_models(self):
        """Test PostResponse with nested UserResponse and TagResponse"""
        from models import TagResponse

        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        tags = [
            TagResponse(tag_id=1, tag_name="tag1"),
            TagResponse(tag_id=2, tag_name="tag2"),
        ]

        post = PostResponse(
            post_id=1,
            user_id=1,
            content="Test post content",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=author,
            tags=tags,
            likes_count=5,
            comments_count=3,
            is_liked=True,
            is_bookmarked=False,
        )

        # Test JSON serialization
        json_data = post.model_dump()
        assert json_data["post_id"] == 1
        assert json_data["content"] == "Test post content"
        assert json_data["author"]["username"] == "author"
        assert len(json_data["tags"]) == 2
        assert json_data["tags"][0]["tag_name"] == "tag1"
        assert json_data["likes_count"] == 5
        assert json_data["is_liked"] is True

    def test_validation_error_handling(self):
        """Test that validation errors are properly handled"""
        from pydantic import ValidationError

        # Test invalid user creation
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(
                user_id=0,  # Invalid: must be > 0
                username="testuser",
                email="invalid-email",  # Invalid: no @
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 2  # Should have errors for user_id and email

        # Check that error details are available
        error_fields = [error["loc"][0] for error in errors]
        assert "user_id" in error_fields
        assert "email" in error_fields

    def test_model_config_from_attributes(self):
        """Test that models can be created from SQLAlchemy objects"""

        # This would normally use a real SQLAlchemy object
        # For now, we test with a mock object that has attributes
        class MockUser:
            user_id = 1
            username = "testuser"
            email = "test@example.com"
            display_name = None
            profile_image_url = None
            bio = None
            area = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        mock_user = MockUser()

        # Test that UserResponse can be created from object attributes
        user = UserResponse.model_validate(mock_user)
        assert user.user_id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
