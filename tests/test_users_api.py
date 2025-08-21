"""
Integration tests for users API endpoints
Tests all user profile and follow relationship endpoints with cache integration
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from main import app
from models.responses import UserResponse, UserProfileResponse
from cache.manager import cache_manager


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing"""
    with patch('api.users.cache_manager') as mock:
        yield mock


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return UserResponse(
        user_id=1,
        username="testuser",
        display_name="Test User",
        email="test@example.com",
        profile_image_url="https://example.com/profile.jpg",
        bio="テストユーザーです",
        area="東京都",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def sample_user_profile():
    """Sample user profile for testing"""
    return UserProfileResponse(
        user_id=1,
        username="testuser",
        display_name="Test User",
        email="test@example.com",
        profile_image_url="https://example.com/profile.jpg",
        bio="テストユーザーです",
        area="東京都",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        followers_count=10,
        following_count=5,
        posts_count=15
    )


@pytest.fixture
def sample_followers():
    """Sample followers for testing"""
    return [
        UserResponse(
            user_id=2,
            username="follower1",
            display_name="Follower One",
            email="follower1@example.com",
            profile_image_url=None,
            bio="フォロワー1です",
            area="神奈川県",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        ),
        UserResponse(
            user_id=3,
            username="follower2",
            display_name="Follower Two",
            email="follower2@example.com",
            profile_image_url="https://example.com/follower2.jpg",
            bio="フォロワー2です",
            area="千葉県",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
    ]


@pytest.fixture
def sample_following():
    """Sample following users for testing"""
    return [
        UserResponse(
            user_id=4,
            username="following1",
            display_name="Following One",
            email="following1@example.com",
            profile_image_url="https://example.com/following1.jpg",
            bio="フォロー中1です",
            area="埼玉県",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        ),
        UserResponse(
            user_id=5,
            username="following2",
            display_name="Following Two",
            email="following2@example.com",
            profile_image_url=None,
            bio="フォロー中2です",
            area="茨城県",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
    ]


class TestGetUserProfile:
    """Test GET /api/v1/users/{user_id} endpoint"""
    
    def test_get_user_profile_success(self, client, mock_cache_manager, sample_user_profile):
        """Test successful user profile retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.return_value = sample_user_profile
        
        response = client.get("/api/v1/users/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 1
        assert data["username"] == "testuser"
        assert data["display_name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["bio"] == "テストユーザーです"
        assert data["area"] == "東京都"
        assert data["followers_count"] == 10
        assert data["following_count"] == 5
        assert data["posts_count"] == 15
        
        mock_cache_manager.get_user_profile.assert_called_once_with(1)
    
    def test_get_user_profile_not_found(self, client, mock_cache_manager):
        """Test user profile retrieval for non-existent user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.return_value = None
        
        response = client.get("/api/v1/users/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "User with ID 999 not found" in data["message"]
        
        mock_cache_manager.get_user_profile.assert_called_once_with(999)
    
    def test_get_user_profile_cache_not_initialized(self, client, mock_cache_manager):
        """Test user profile retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/users/1")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
    
    def test_get_user_profile_server_error(self, client, mock_cache_manager):
        """Test server error handling for user profile retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/users/1")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve user profile" in data["message"]


class TestGetUserFollowers:
    """Test GET /api/v1/users/{user_id}/followers endpoint"""
    
    def test_get_user_followers_success(self, client, mock_cache_manager, sample_user, sample_followers):
        """Test successful user followers retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.return_value = sample_followers
        
        response = client.get("/api/v1/users/1/followers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["user_id"] == 2
        assert data[0]["username"] == "follower1"
        assert data[0]["display_name"] == "Follower One"
        assert data[1]["user_id"] == 3
        assert data[1]["username"] == "follower2"
        
        mock_cache_manager.get_user_by_id.assert_called_once_with(1)
        mock_cache_manager.get_user_followers.assert_called_once_with(
            user_id=1, skip=0, limit=20
        )
    
    def test_get_user_followers_with_pagination(self, client, mock_cache_manager, sample_user, sample_followers):
        """Test user followers retrieval with pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.return_value = sample_followers[1:]
        
        response = client.get("/api/v1/users/1/followers?skip=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 3
        
        mock_cache_manager.get_user_followers.assert_called_once_with(
            user_id=1, skip=1, limit=10
        )
    
    def test_get_user_followers_user_not_found(self, client, mock_cache_manager):
        """Test followers retrieval for non-existent user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = None
        
        response = client.get("/api/v1/users/999/followers")
        
        assert response.status_code == 404
        data = response.json()
        assert "User with ID 999 not found" in data["message"]
        
        mock_cache_manager.get_user_by_id.assert_called_once_with(999)
    
    def test_get_user_followers_empty_result(self, client, mock_cache_manager, sample_user):
        """Test followers retrieval with no followers"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.return_value = []
        
        response = client.get("/api/v1/users/1/followers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_get_user_followers_cache_not_initialized(self, client, mock_cache_manager):
        """Test followers retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/users/1/followers")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
    
    def test_get_user_followers_invalid_pagination(self, client, mock_cache_manager):
        """Test followers retrieval with invalid pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        
        # Test negative skip
        response = client.get("/api/v1/users/1/followers?skip=-1")
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get("/api/v1/users/1/followers?limit=200")
        assert response.status_code == 422
        
        # Test limit too small
        response = client.get("/api/v1/users/1/followers?limit=0")
        assert response.status_code == 422
    
    def test_get_user_followers_server_error(self, client, mock_cache_manager, sample_user):
        """Test server error handling for followers retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/users/1/followers")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve user followers" in data["message"]


class TestGetUserFollowing:
    """Test GET /api/v1/users/{user_id}/following endpoint"""
    
    def test_get_user_following_success(self, client, mock_cache_manager, sample_user, sample_following):
        """Test successful user following retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.return_value = sample_following
        
        response = client.get("/api/v1/users/1/following")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["user_id"] == 4
        assert data[0]["username"] == "following1"
        assert data[0]["display_name"] == "Following One"
        assert data[1]["user_id"] == 5
        assert data[1]["username"] == "following2"
        
        mock_cache_manager.get_user_by_id.assert_called_once_with(1)
        mock_cache_manager.get_user_following.assert_called_once_with(
            user_id=1, skip=0, limit=20
        )
    
    def test_get_user_following_with_pagination(self, client, mock_cache_manager, sample_user, sample_following):
        """Test user following retrieval with pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.return_value = sample_following[1:]
        
        response = client.get("/api/v1/users/1/following?skip=1&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 5
        
        mock_cache_manager.get_user_following.assert_called_once_with(
            user_id=1, skip=1, limit=5
        )
    
    def test_get_user_following_user_not_found(self, client, mock_cache_manager):
        """Test following retrieval for non-existent user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = None
        
        response = client.get("/api/v1/users/999/following")
        
        assert response.status_code == 404
        data = response.json()
        assert "User with ID 999 not found" in data["message"]
        
        mock_cache_manager.get_user_by_id.assert_called_once_with(999)
    
    def test_get_user_following_empty_result(self, client, mock_cache_manager, sample_user):
        """Test following retrieval with no following users"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.return_value = []
        
        response = client.get("/api/v1/users/1/following")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_get_user_following_cache_not_initialized(self, client, mock_cache_manager):
        """Test following retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/users/1/following")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
    
    def test_get_user_following_invalid_pagination(self, client, mock_cache_manager):
        """Test following retrieval with invalid pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        
        # Test negative skip
        response = client.get("/api/v1/users/1/following?skip=-1")
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get("/api/v1/users/1/following?limit=200")
        assert response.status_code == 422
        
        # Test limit too small
        response = client.get("/api/v1/users/1/following?limit=0")
        assert response.status_code == 422
    
    def test_get_user_following_server_error(self, client, mock_cache_manager, sample_user):
        """Test server error handling for following retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/users/1/following")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve user following" in data["message"]


class TestUsersEndpointsIntegration:
    """Integration tests for users endpoints with authentication"""
    
    def test_get_user_profile_with_authentication(self, client, mock_cache_manager, sample_user, sample_user_profile):
        """Test user profile retrieval with authenticated user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.return_value = sample_user_profile
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/users/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == 1
            
            mock_cache_manager.get_user_profile.assert_called_once_with(1)
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_followers_with_authentication(self, client, mock_cache_manager, sample_user, sample_followers):
        """Test user followers retrieval with authenticated user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.return_value = sample_followers
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/users/1/followers")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            
            mock_cache_manager.get_user_followers.assert_called_once_with(
                user_id=1, skip=0, limit=20
            )
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_following_with_authentication(self, client, mock_cache_manager, sample_user, sample_following):
        """Test user following retrieval with authenticated user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.return_value = sample_following
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/users/1/following")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            
            mock_cache_manager.get_user_following.assert_called_once_with(
                user_id=1, skip=0, limit=20
            )
        finally:
            app.dependency_overrides.clear()


class TestUsersEndpointsEdgeCases:
    """Test edge cases and special scenarios for users endpoints"""
    
    def test_get_user_profile_with_zero_counts(self, client, mock_cache_manager):
        """Test user profile with zero followers, following, and posts"""
        user_profile_zero = UserProfileResponse(
            user_id=1,
            username="newuser",
            display_name="New User",
            email="new@example.com",
            profile_image_url=None,
            bio=None,
            area=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            followers_count=0,
            following_count=0,
            posts_count=0
        )
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.return_value = user_profile_zero
        
        response = client.get("/api/v1/users/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["followers_count"] == 0
        assert data["following_count"] == 0
        assert data["posts_count"] == 0
        assert data["bio"] is None
        assert data["area"] is None
    
    def test_get_user_profile_with_japanese_data(self, client, mock_cache_manager):
        """Test user profile with Japanese characters"""
        user_profile_jp = UserProfileResponse(
            user_id=1,
            username="日本ユーザー",
            display_name="田中太郎",
            email="tanaka@example.jp",
            profile_image_url="https://example.jp/profile.jpg",
            bio="こんにちは！地域SNSを楽しんでいます。よろしくお願いします。",
            area="東京都渋谷区",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            followers_count=100,
            following_count=50,
            posts_count=200
        )
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.return_value = user_profile_jp
        
        response = client.get("/api/v1/users/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "日本ユーザー"
        assert data["display_name"] == "田中太郎"
        assert data["bio"] == "こんにちは！地域SNSを楽しんでいます。よろしくお願いします。"
        assert data["area"] == "東京都渋谷区"
    
    def test_get_followers_large_pagination(self, client, mock_cache_manager, sample_user):
        """Test followers retrieval with large pagination values"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.return_value = []
        
        response = client.get("/api/v1/users/1/followers?skip=1000&limit=100")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        
        mock_cache_manager.get_user_followers.assert_called_once_with(
            user_id=1, skip=1000, limit=100
        )
    
    def test_get_following_large_pagination(self, client, mock_cache_manager, sample_user):
        """Test following retrieval with large pagination values"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.return_value = []
        
        response = client.get("/api/v1/users/1/following?skip=500&limit=50")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        
        mock_cache_manager.get_user_following.assert_called_once_with(
            user_id=1, skip=500, limit=50
        )


class TestUsersEndpointsPerformance:
    """Test performance-related aspects of users endpoints"""
    
    def test_get_user_profile_response_structure(self, client, mock_cache_manager, sample_user_profile):
        """Test that user profile response has all required fields"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_profile.return_value = sample_user_profile
        
        response = client.get("/api/v1/users/1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields are present
        required_fields = [
            "user_id", "username", "display_name", "email", "profile_image_url",
            "bio", "area", "created_at", "updated_at", "followers_count",
            "following_count", "posts_count"
        ]
        
        for field in required_fields:
            assert field in data
    
    def test_get_followers_response_structure(self, client, mock_cache_manager, sample_user, sample_followers):
        """Test that followers response has correct structure"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_followers.return_value = sample_followers
        
        response = client.get("/api/v1/users/1/followers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            # Check first follower has all required fields
            follower = data[0]
            required_fields = [
                "user_id", "username", "display_name", "email", "profile_image_url",
                "bio", "area", "created_at", "updated_at"
            ]
            
            for field in required_fields:
                assert field in follower
    
    def test_get_following_response_structure(self, client, mock_cache_manager, sample_user, sample_following):
        """Test that following response has correct structure"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_following.return_value = sample_following
        
        response = client.get("/api/v1/users/1/following")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            # Check first following user has all required fields
            following_user = data[0]
            required_fields = [
                "user_id", "username", "display_name", "email", "profile_image_url",
                "bio", "area", "created_at", "updated_at"
            ]
            
            for field in required_fields:
                assert field in following_user