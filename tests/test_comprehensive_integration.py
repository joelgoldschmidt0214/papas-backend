"""
Comprehensive integration test suite covering all API endpoints
Tests complete API functionality with realistic scenarios
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC
from typing import List, Dict, Any

from main import app
from models.responses import (
    PostResponse,
    UserResponse,
    UserProfileResponse,
    TagResponse,
    CommentResponse,
    SurveyResponse,
    ErrorResponse,
)
from models.requests import PostRequest
from cache.manager import cache_manager


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing"""
    with patch("cache.manager.cache_manager") as mock:
        # Patch all the places where cache_manager is imported
        with (
            patch("api.posts.cache_manager", mock),
            patch("api.users.cache_manager", mock),
            patch("api.tags.cache_manager", mock),
            patch("api.surveys.cache_manager", mock),
            patch("api.likes_bookmarks.cache_manager", mock),
            patch("main.cache_manager", mock),
        ):
            yield mock


@pytest.fixture
def sample_users():
    """Sample users for testing"""
    return [
        UserResponse(
            user_id=1,
            username="tanaka_taro",
            display_name="田中太郎",
            email="tanaka@example.com",
            profile_image_url="https://example.com/avatar1.jpg",
            bio="地域イベント大好きです",
            area="東京都渋谷区",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        UserResponse(
            user_id=2,
            username="sato_hanako",
            display_name="佐藤花子",
            email="sato@example.com",
            profile_image_url="https://example.com/avatar2.jpg",
            bio="地域の安全を守りたい",
            area="東京都渋谷区",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]


@pytest.fixture
def sample_tags():
    """Sample tags for testing"""
    return [
        TagResponse(tag_id=1, tag_name="イベント", posts_count=25),
        TagResponse(tag_id=2, tag_name="お祭り", posts_count=12),
        TagResponse(tag_id=3, tag_name="安全", posts_count=8),
        TagResponse(tag_id=4, tag_name="地域", posts_count=30),
    ]


@pytest.fixture
def sample_posts(sample_users, sample_tags):
    """Sample posts for testing"""
    return [
        PostResponse(
            post_id=1,
            user_id=1,
            content="地域のお祭り情報です！今年も盛大に開催予定です。",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=sample_users[0],
            tags=[sample_tags[0], sample_tags[1]],
            likes_count=15,
            comments_count=3,
            is_liked=False,
            is_bookmarked=True,
        ),
        PostResponse(
            post_id=2,
            user_id=2,
            content="夜間の街灯が切れています。修理をお願いします。",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=sample_users[1],
            tags=[sample_tags[2], sample_tags[3]],
            likes_count=8,
            comments_count=5,
            is_liked=True,
            is_bookmarked=False,
        ),
    ]


@pytest.fixture
def sample_comments(sample_users):
    """Sample comments for testing"""
    return [
        CommentResponse(
            comment_id=1,
            post_id=1,
            user_id=2,
            content="楽しみにしています！",
            created_at=datetime.now(UTC),
            author=sample_users[1],
        ),
        CommentResponse(
            comment_id=2,
            post_id=1,
            user_id=1,
            content="ありがとうございます！",
            created_at=datetime.now(UTC),
            author=sample_users[0],
        ),
    ]


@pytest.fixture
def sample_surveys():
    """Sample surveys for testing"""
    return [
        SurveyResponse(
            survey_id=1,
            title="地域イベントについて",
            question_text="どのようなイベントに参加したいですか？",
            points=10,
            deadline=datetime.now(UTC),
            target_audience="全住民",
            created_at=datetime.now(UTC),
            response_count=25,
        )
    ]


class TestCompleteAPIWorkflow:
    """Test complete API workflow scenarios"""

    def test_complete_user_journey(
        self, client, mock_cache_manager, sample_users, sample_posts, sample_tags
    ):
        """Test complete user journey from login to post creation"""
        # Setup mock cache
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts
        mock_cache_manager.get_tags.return_value = sample_tags
        mock_cache_manager.add_post_to_cache.return_value = sample_posts[0]

        # 1. Check system health
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"

        # 2. Get available tags
        response = client.get("/api/v1/tags")
        assert response.status_code == 200
        tags_data = response.json()
        assert len(tags_data) == 4
        assert tags_data[0]["tag_name"] == "イベント"

        # 3. Browse posts without authentication
        response = client.get("/api/v1/posts")
        assert response.status_code == 200
        posts_data = response.json()
        assert len(posts_data) == 2

        # 4. Try to create post without authentication (should fail)
        post_data = {"content": "認証なしの投稿"}
        response = client.post("/api/v1/posts", json=post_data)
        assert response.status_code == 401

        # 5. Login and create post with authentication
        from main import app
        from auth.middleware import get_current_user_required

        def mock_get_current_user():
            return sample_users[0]

        app.dependency_overrides[get_current_user_required] = mock_get_current_user

        try:
            post_data = {
                "content": "新しい地域イベントの提案です！",
                "tags": ["イベント", "地域"],
            }
            response = client.post("/api/v1/posts", json=post_data)
            assert response.status_code == 201
            created_post = response.json()
            assert (
                created_post["content"]
                == "地域のお祭り情報です！今年も盛大に開催予定です。"
            )
        finally:
            app.dependency_overrides.clear()

    def test_posts_api_comprehensive(
        self, client, mock_cache_manager, sample_posts, sample_comments
    ):
        """Test all posts API endpoints comprehensively"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        mock_cache_manager.get_posts_by_tag.return_value = [sample_posts[0]]
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments

        # Test posts list with pagination
        response = client.get("/api/v1/posts?skip=0&limit=10")
        assert response.status_code == 200
        posts_data = response.json()
        assert len(posts_data) == 2

        # Test single post retrieval
        response = client.get("/api/v1/posts/1")
        assert response.status_code == 200
        post_data = response.json()
        assert post_data["post_id"] == 1
        assert post_data["author"]["username"] == "tanaka_taro"

        # Test posts by tag
        response = client.get("/api/v1/posts/tags/イベント")
        assert response.status_code == 200
        tagged_posts = response.json()
        assert len(tagged_posts) == 1

        # Test post comments
        response = client.get("/api/v1/posts/1/comments")
        assert response.status_code == 200
        comments_data = response.json()
        assert len(comments_data) == 2
        assert comments_data[0]["content"] == "楽しみにしています！"

    def test_users_api_comprehensive(self, client, mock_cache_manager, sample_users):
        """Test all users API endpoints comprehensively"""
        mock_cache_manager.is_initialized.return_value = True

        # Create user profile response
        user_profile = UserProfileResponse(
            user_id=1,
            username="tanaka_taro",
            display_name="田中太郎",
            email="tanaka@example.com",
            profile_image_url="https://example.com/avatar1.jpg",
            bio="地域イベント大好きです",
            area="東京都渋谷区",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            followers_count=10,
            following_count=15,
            posts_count=5,
        )

        mock_cache_manager.get_user_profile.return_value = user_profile
        mock_cache_manager.get_user_by_id.return_value = sample_users[0]
        mock_cache_manager.get_user_followers.return_value = [sample_users[1]]
        mock_cache_manager.get_user_following.return_value = [sample_users[1]]

        # Test user profile
        response = client.get("/api/v1/users/1")
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["user_id"] == 1
        assert profile_data["followers_count"] == 10
        assert profile_data["following_count"] == 15

        # Test user followers
        response = client.get("/api/v1/users/1/followers")
        assert response.status_code == 200
        followers_data = response.json()
        assert len(followers_data) == 1
        assert followers_data[0]["username"] == "sato_hanako"

        # Test user following
        response = client.get("/api/v1/users/1/following")
        assert response.status_code == 200
        following_data = response.json()
        assert len(following_data) == 1

    def test_tags_api_comprehensive(self, client, mock_cache_manager, sample_tags):
        """Test all tags API endpoints comprehensively"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        mock_cache_manager.get_tag_by_name.return_value = sample_tags[0]

        # Test tags list
        response = client.get("/api/v1/tags")
        assert response.status_code == 200
        tags_data = response.json()
        assert len(tags_data) == 4
        assert tags_data[0]["tag_name"] == "イベント"
        assert tags_data[0]["posts_count"] == 25

        # Test specific tag
        response = client.get("/api/v1/tags/イベント")
        assert response.status_code == 200
        tag_data = response.json()
        assert tag_data["tag_name"] == "イベント"
        assert tag_data["posts_count"] == 25

    def test_surveys_api_comprehensive(
        self, client, mock_cache_manager, sample_surveys
    ):
        """Test all surveys API endpoints comprehensively"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_surveys.return_value = sample_surveys
        mock_cache_manager.get_survey_by_id.return_value = sample_surveys[0]
        mock_cache_manager.get_survey_responses.return_value = {
            "total_responses": 25,
            "responses": [
                {"option": "お祭り", "count": 15},
                {"option": "スポーツイベント", "count": 10},
            ],
        }

        # Test surveys list
        response = client.get("/api/v1/surveys")
        assert response.status_code == 200
        surveys_data = response.json()
        assert len(surveys_data) == 1
        assert surveys_data[0]["title"] == "地域イベントについて"

        # Test specific survey
        response = client.get("/api/v1/surveys/1")
        assert response.status_code == 200
        survey_data = response.json()
        assert survey_data["survey_id"] == 1

        # Test survey responses
        response = client.get("/api/v1/surveys/1/responses")
        assert response.status_code == 200
        responses_data = response.json()
        assert responses_data["total_responses"] == 25

    def test_system_monitoring_comprehensive(self, client, mock_cache_manager):
        """Test all system monitoring endpoints comprehensively"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_cache_stats.return_value = {
            "initialized": True,
            "initialization_time": 2.5,
            "posts_count": 100,
            "users_count": 50,
            "comments_count": 200,
            "tags_count": 20,
            "surveys_count": 5,
            "likes_count": 500,
            "bookmarks_count": 150,
            "follows_count": 300,
        }
        mock_cache_manager.get_performance_stats.return_value = {
            "total_requests": 1000,
            "average_response_time_ms": 150.5,
            "min_response_time_ms": 50.0,
            "max_response_time_ms": 300.0,
            "total_response_time": 150.5,
            "requests_under_200ms": 950,
            "performance_percentage": 95.0,
        }
        mock_cache_manager.get_memory_stats.return_value = {
            "total_mb": 128.5,
            "total_bytes": 134742016,
        }

        # Test root health check
        response = client.get("/")
        assert response.status_code == 200
        root_data = response.json()
        assert root_data["status"] == "healthy"
        assert root_data["version"] == "1.0.0"

        # Test detailed health check
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["components"]["cache"]["status"] == "healthy"

        # Test system metrics
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200
        metrics_data = response.json()
        assert metrics_data["cache"]["data_counts"]["posts"] == 100
        assert metrics_data["performance"]["performance_target_percentage"] == 95.0
        assert metrics_data["performance"]["meets_200ms_target"] == True


class TestErrorHandlingComprehensive:
    """Test comprehensive error handling across all endpoints"""

    def test_cache_not_initialized_errors(self, client, mock_cache_manager):
        """Test all endpoints when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False

        endpoints_to_test = [
            "/api/v1/posts",
            "/api/v1/posts/1",
            "/api/v1/posts/tags/test",
            "/api/v1/posts/1/comments",
            "/api/v1/users/1",
            "/api/v1/users/1/followers",
            "/api/v1/users/1/following",
            "/api/v1/tags",
            "/api/v1/tags/test",
            "/api/v1/surveys",
            "/api/v1/surveys/1",
            "/api/v1/surveys/1/responses",
        ]

        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            assert response.status_code == 503, (
                f"Endpoint {endpoint} should return 503 when cache not initialized"
            )
            error_data = response.json()
            assert "cache" in error_data["message"].lower()
            assert "unavailable" in error_data["message"].lower()

    def test_resource_not_found_errors(self, client, mock_cache_manager):
        """Test 404 errors for non-existent resources"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = None
        mock_cache_manager.get_user_profile.return_value = None
        mock_cache_manager.get_user_by_id.return_value = None
        mock_cache_manager.get_tag_by_name.return_value = None
        mock_cache_manager.get_survey_by_id.return_value = None

        not_found_endpoints = [
            ("/api/v1/posts/999", "Post"),
            ("/api/v1/users/999", "User"),
            ("/api/v1/tags/nonexistent", "Tag"),
            ("/api/v1/surveys/999", "Survey"),
        ]

        for endpoint, resource_type in not_found_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 404, (
                f"Endpoint {endpoint} should return 404 for non-existent {resource_type}"
            )
            error_data = response.json()
            assert "not found" in error_data["message"].lower()

    def test_validation_errors(self, client, mock_cache_manager):
        """Test validation errors for invalid requests"""
        mock_cache_manager.is_initialized.return_value = True

        # Test invalid pagination parameters
        invalid_pagination_tests = [
            ("/api/v1/posts?skip=-1", "negative skip"),
            ("/api/v1/posts?limit=0", "zero limit"),
            ("/api/v1/posts?limit=200", "excessive limit"),
            ("/api/v1/users/1/followers?skip=-5", "negative skip for followers"),
            ("/api/v1/tags?limit=1000", "excessive limit for tags"),
        ]

        for endpoint, description in invalid_pagination_tests:
            response = client.get(endpoint)
            assert response.status_code == 422, (
                f"Should return 422 for {description}: {endpoint}"
            )

    def test_authentication_errors(self, client, mock_cache_manager, sample_users):
        """Test authentication-related errors"""
        mock_cache_manager.is_initialized.return_value = True

        # Test creating post without authentication
        post_data = {"content": "Test post"}
        response = client.post("/api/v1/posts", json=post_data)
        assert response.status_code == 401
        error_data = response.json()
        assert "authentication" in error_data["message"].lower()

        # Test creating post with invalid data (authenticated)
        from main import app
        from auth.middleware import get_current_user_required

        def mock_get_current_user():
            return sample_users[0]

        app.dependency_overrides[get_current_user_required] = mock_get_current_user

        try:
            # Test empty content
            invalid_post_data = {"content": ""}
            response = client.post("/api/v1/posts", json=invalid_post_data)
            assert response.status_code == 422

            # Test missing content
            invalid_post_data = {}
            response = client.post("/api/v1/posts", json=invalid_post_data)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestPerformanceValidation:
    """Test performance requirements validation"""

    def test_response_time_tracking(self, client, mock_cache_manager, sample_posts):
        """Test that response times are properly tracked"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts
        mock_cache_manager.record_request_time = Mock()

        # Make a request
        response = client.get("/api/v1/posts")
        assert response.status_code == 200

        # Check that response time header is present
        assert "X-Response-Time" in response.headers
        response_time_header = response.headers["X-Response-Time"]
        assert response_time_header.endswith("s")

        # Verify response time is reasonable (should be very fast with mocked cache)
        response_time = float(response_time_header[:-1])
        assert response_time < 1.0, (
            "Response time should be under 1 second with mocked cache"
        )

    def test_pagination_performance(self, client, mock_cache_manager, sample_posts):
        """Test pagination performance with various limits"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts

        # Test different pagination sizes
        pagination_tests = [(0, 1), (0, 10), (0, 50), (0, 100), (10, 20), (50, 50)]

        for skip, limit in pagination_tests:
            response = client.get(f"/api/v1/posts?skip={skip}&limit={limit}")
            assert response.status_code == 200

            # Verify response time header exists
            assert "X-Response-Time" in response.headers

            # Verify pagination parameters were passed correctly
            mock_cache_manager.get_posts.assert_called_with(
                skip=skip, limit=limit, current_user_id=None
            )


class TestAPIDocumentationValidation:
    """Test API documentation and OpenAPI schema"""

    def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is properly generated"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()

        # Verify basic schema structure
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
        assert "components" in openapi_schema

        # Verify API info
        info = openapi_schema["info"]
        assert info["title"] == "TOMOSU Backend API"
        assert info["version"] == "1.0.0"
        assert "地域SNS" in info["description"]

        # Verify key endpoints are documented
        paths = openapi_schema["paths"]
        expected_endpoints = [
            "/api/v1/posts",
            "/api/v1/posts/{post_id}",
            "/api/v1/users/{user_id}",
            "/api/v1/tags",
            "/api/v1/surveys",
            "/api/v1/system/health",
            "/api/v1/system/metrics",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in paths, (
                f"Endpoint {endpoint} should be documented in OpenAPI schema"
            )

    def test_docs_page_accessibility(self, client):
        """Test that documentation pages are accessible"""
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_endpoint_documentation_completeness(self, client):
        """Test that endpoints have proper documentation"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()

        # Check that key endpoints have proper documentation
        posts_endpoint = openapi_schema["paths"]["/api/v1/posts"]["get"]

        # Verify summary and description exist
        assert "summary" in posts_endpoint
        assert "description" in posts_endpoint
        assert "投稿一覧" in posts_endpoint["summary"]

        # Verify response documentation
        assert "responses" in posts_endpoint
        assert "200" in posts_endpoint["responses"]
        assert "503" in posts_endpoint["responses"]

        # Verify parameter documentation
        assert "parameters" in posts_endpoint
        parameters = posts_endpoint["parameters"]
        param_names = [p["name"] for p in parameters]
        assert "skip" in param_names
        assert "limit" in param_names
