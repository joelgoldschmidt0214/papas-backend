"""
Integration tests for posts API endpoints
Tests all posts endpoints with cache integration
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from main import app
from models.responses import PostResponse, UserResponse, TagResponse
from cache.manager import cache_manager


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing"""
    with patch('api.posts.cache_manager') as mock:
        yield mock


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return UserResponse(
        user_id=1,
        username="testuser",
        display_name="Test User",
        email="test@example.com",
        profile_image_url=None,
        bio="Test bio",
        area="Test Area",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def sample_posts(sample_user):
    """Sample posts for testing"""
    tag1 = TagResponse(tag_id=1, tag_name="テスト", posts_count=2)
    tag2 = TagResponse(tag_id=2, tag_name="地域", posts_count=1)
    
    return [
        PostResponse(
            post_id=1,
            user_id=1,
            content="テスト投稿1です",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=sample_user,
            tags=[tag1],
            likes_count=5,
            comments_count=2,
            is_liked=False,
            is_bookmarked=False
        ),
        PostResponse(
            post_id=2,
            user_id=1,
            content="テスト投稿2です",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=sample_user,
            tags=[tag1, tag2],
            likes_count=3,
            comments_count=1,
            is_liked=True,
            is_bookmarked=True
        )
    ]


class TestGetPosts:
    """Test GET /api/v1/posts endpoint"""
    
    def test_get_posts_success(self, client, mock_cache_manager, sample_posts):
        """Test successful posts retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts
        
        response = client.get("/api/v1/posts")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["post_id"] == 1
        assert data[0]["content"] == "テスト投稿1です"
        assert data[1]["post_id"] == 2
        
        mock_cache_manager.get_posts.assert_called_once_with(
            skip=0, limit=20, current_user_id=None
        )
    
    def test_get_posts_with_pagination(self, client, mock_cache_manager, sample_posts):
        """Test posts retrieval with pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts[1:]
        
        response = client.get("/api/v1/posts?skip=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        mock_cache_manager.get_posts.assert_called_once_with(
            skip=1, limit=10, current_user_id=None
        )
    
    def test_get_posts_cache_not_initialized(self, client, mock_cache_manager):
        """Test posts retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/posts")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "cache" in data["message"].lower() and "unavailable" in data["message"].lower()
    
    def test_get_posts_invalid_pagination(self, client, mock_cache_manager):
        """Test posts retrieval with invalid pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        
        # Test negative skip
        response = client.get("/api/v1/posts?skip=-1")
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get("/api/v1/posts?limit=200")
        assert response.status_code == 422
        
        # Test limit too small
        response = client.get("/api/v1/posts?limit=0")
        assert response.status_code == 422


class TestGetPostById:
    """Test GET /api/v1/posts/{post_id} endpoint"""
    
    def test_get_post_by_id_success(self, client, mock_cache_manager, sample_posts):
        """Test successful single post retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        
        response = client.get("/api/v1/posts/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["post_id"] == 1
        assert data["content"] == "テスト投稿1です"
        assert data["author"]["username"] == "testuser"
        
        mock_cache_manager.get_post_by_id.assert_called_once_with(1, current_user_id=None)
    
    def test_get_post_by_id_not_found(self, client, mock_cache_manager):
        """Test post retrieval for non-existent post"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = None
        
        response = client.get("/api/v1/posts/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"]
    
    def test_get_post_by_id_cache_not_initialized(self, client, mock_cache_manager):
        """Test post retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/posts/1")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "cache" in data["message"].lower() and "unavailable" in data["message"].lower()


class TestCreatePost:
    """Test POST /api/v1/posts endpoint"""
    
    def test_create_post_success(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test successful post creation"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.add_post_to_cache.return_value = sample_posts[0]
        
        post_data = {
            "content": "新しい投稿です",
            "tags": ["テスト", "新規"]
        }
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_required
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_required] = mock_get_current_user
        
        try:
            response = client.post("/api/v1/posts", json=post_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["post_id"] == 1
            assert data["content"] == "テスト投稿1です"
            
            mock_cache_manager.add_post_to_cache.assert_called_once()
            call_args = mock_cache_manager.add_post_to_cache.call_args
            assert call_args[1]["post_data"]["content"] == "新しい投稿です"
            assert call_args[1]["author"] == sample_user
            assert call_args[1]["tags"] == ["テスト", "新規"]
        finally:
            app.dependency_overrides.clear()
    
    def test_create_post_without_tags(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test post creation without tags"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.add_post_to_cache.return_value = sample_posts[0]
        
        post_data = {
            "content": "タグなしの投稿です"
        }
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_required
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_required] = mock_get_current_user
        
        try:
            response = client.post("/api/v1/posts", json=post_data)
            
            assert response.status_code == 201
            
            call_args = mock_cache_manager.add_post_to_cache.call_args
            assert call_args[1]["tags"] == []
        finally:
            app.dependency_overrides.clear()
    
    def test_create_post_unauthenticated(self, client, mock_cache_manager):
        """Test post creation without authentication"""
        mock_cache_manager.is_initialized.return_value = True
        
        post_data = {
            "content": "認証なしの投稿です"
        }
        
        response = client.post("/api/v1/posts", json=post_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Authentication required" in data["message"]
    
    def test_create_post_invalid_data(self, client, mock_cache_manager, sample_user):
        """Test post creation with invalid data"""
        mock_cache_manager.is_initialized.return_value = True
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_required
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_required] = mock_get_current_user
        
        try:
            # Test empty content
            post_data = {
                "content": ""
            }
            
            response = client.post("/api/v1/posts", json=post_data)
            assert response.status_code == 422
            
            # Test missing content
            post_data = {}
            
            response = client.post("/api/v1/posts", json=post_data)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
    
    def test_create_post_cache_not_initialized(self, client, mock_cache_manager, sample_user):
        """Test post creation when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        post_data = {
            "content": "テスト投稿です"
        }
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_required
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_required] = mock_get_current_user
        
        try:
            response = client.post("/api/v1/posts", json=post_data)
            
            assert response.status_code == 503
            data = response.json()
            assert data["error_code"] == "SERVICE_UNAVAILABLE"
            assert "cache" in data["message"].lower() and "unavailable" in data["message"].lower()
        finally:
            app.dependency_overrides.clear()


class TestGetPostsByTag:
    """Test GET /api/v1/posts/tags/{tag_name} endpoint"""
    
    def test_get_posts_by_tag_success(self, client, mock_cache_manager, sample_posts):
        """Test successful posts retrieval by tag"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts_by_tag.return_value = sample_posts
        
        response = client.get("/api/v1/posts/tags/テスト")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("テスト" in [tag["tag_name"] for tag in post["tags"]] for post in data)
        
        mock_cache_manager.get_posts_by_tag.assert_called_once_with(
            tag_name="テスト", skip=0, limit=20, current_user_id=None
        )
    
    def test_get_posts_by_tag_with_pagination(self, client, mock_cache_manager, sample_posts):
        """Test posts retrieval by tag with pagination"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts_by_tag.return_value = sample_posts[1:]
        
        response = client.get("/api/v1/posts/tags/地域?skip=1&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        mock_cache_manager.get_posts_by_tag.assert_called_once_with(
            tag_name="地域", skip=1, limit=5, current_user_id=None
        )
    
    def test_get_posts_by_tag_empty_result(self, client, mock_cache_manager):
        """Test posts retrieval by tag with no results"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts_by_tag.return_value = []
        
        response = client.get("/api/v1/posts/tags/存在しないタグ")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_get_posts_by_tag_cache_not_initialized(self, client, mock_cache_manager):
        """Test posts retrieval by tag when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/posts/tags/テスト")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "cache" in data["message"].lower() and "unavailable" in data["message"].lower()
    
    def test_get_posts_by_tag_japanese_characters(self, client, mock_cache_manager, sample_posts):
        """Test posts retrieval by tag with Japanese characters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts_by_tag.return_value = sample_posts
        
        # Test with URL encoded Japanese characters
        response = client.get("/api/v1/posts/tags/地域イベント")
        
        assert response.status_code == 200
        
        mock_cache_manager.get_posts_by_tag.assert_called_once_with(
            tag_name="地域イベント", skip=0, limit=20, current_user_id=None
        )


class TestPostsEndpointsIntegration:
    """Integration tests for posts endpoints with authentication"""
    
    def test_get_posts_with_authentication(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test posts retrieval with authenticated user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.return_value = sample_posts
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/posts")
            
            assert response.status_code == 200
            mock_cache_manager.get_posts.assert_called_once_with(
                skip=0, limit=20, current_user_id=1
            )
        finally:
            app.dependency_overrides.clear()
    
    def test_get_post_by_id_with_authentication(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test single post retrieval with authenticated user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/posts/1")
            
            assert response.status_code == 200
            mock_cache_manager.get_post_by_id.assert_called_once_with(1, current_user_id=1)
        finally:
            app.dependency_overrides.clear()
    
    def test_get_posts_by_tag_with_authentication(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test posts by tag retrieval with authenticated user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts_by_tag.return_value = sample_posts
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/posts/tags/テスト")
            
            assert response.status_code == 200
            mock_cache_manager.get_posts_by_tag.assert_called_once_with(
                tag_name="テスト", skip=0, limit=20, current_user_id=1
            )
        finally:
            app.dependency_overrides.clear()


class TestPostsErrorHandling:
    """Test error handling for posts endpoints"""
    
    def test_posts_endpoint_server_error(self, client, mock_cache_manager):
        """Test server error handling"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts.side_effect = Exception("Database error")
        
        response = client.get("/api/v1/posts")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "posts" in data["message"].lower() and "unavailable" in data["message"].lower()
    
    def test_post_by_id_server_error(self, client, mock_cache_manager):
        """Test server error handling for single post retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/posts/1")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "posts" in data["message"].lower() and "unavailable" in data["message"].lower()
    
    def test_create_post_server_error(self, client, mock_cache_manager, sample_user):
        """Test server error handling for post creation"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.add_post_to_cache.side_effect = Exception("Cache error")
        
        post_data = {
            "content": "テスト投稿です"
        }
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_required
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_required] = mock_get_current_user
        
        try:
            response = client.post("/api/v1/posts", json=post_data)
            
            assert response.status_code == 503
            data = response.json()
            assert data["error_code"] == "SERVICE_UNAVAILABLE"
            assert "posts" in data["message"].lower() and "unavailable" in data["message"].lower()
        finally:
            app.dependency_overrides.clear()
    
    def test_posts_by_tag_server_error(self, client, mock_cache_manager):
        """Test server error handling for posts by tag"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_posts_by_tag.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/posts/tags/テスト")
        
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "posts" in data["message"].lower() and "unavailable" in data["message"].lower()