"""
Integration tests for likes and bookmarks API endpoints
Tests all likes and bookmarks endpoints with cache integration
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
    with patch('api.likes_bookmarks.cache_manager') as mock:
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
def sample_user2():
    """Second sample user for testing"""
    return UserResponse(
        user_id=2,
        username="testuser2",
        display_name="Test User 2",
        email="test2@example.com",
        profile_image_url=None,
        bio="Test bio 2",
        area="Test Area 2",
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


class TestGetPostLikes:
    """Test GET /api/v1/posts/{post_id}/likes endpoint"""
    
    def test_get_post_likes_success(self, client, mock_cache_manager, sample_posts):
        """Test successful post likes retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        mock_cache_manager.likes = {1: {1, 2, 3, 4, 5}}  # 5 users liked post 1
        
        response = client.get("/api/v1/posts/1/likes")
        
        assert response.status_code == 200
        data = response.json()
        assert data["post_id"] == 1
        assert data["likes_count"] == 5
        assert data["is_liked"] == False  # No authenticated user
        
        mock_cache_manager.get_post_by_id.assert_called_once_with(1)
    
    def test_get_post_likes_with_authenticated_user_liked(self, client, mock_cache_manager, sample_posts, sample_user):
        """Test post likes retrieval with authenticated user who liked the post"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        mock_cache_manager.likes = {1: {1, 2, 3}}  # User 1 liked post 1
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/posts/1/likes")
            
            assert response.status_code == 200
            data = response.json()
            assert data["post_id"] == 1
            assert data["likes_count"] == 3
            assert data["is_liked"] == True  # User 1 liked the post
        finally:
            app.dependency_overrides.clear()
    
    def test_get_post_likes_with_authenticated_user_not_liked(self, client, mock_cache_manager, sample_posts, sample_user):
        """Test post likes retrieval with authenticated user who didn't like the post"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        mock_cache_manager.likes = {1: {2, 3, 4}}  # User 1 didn't like post 1
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/posts/1/likes")
            
            assert response.status_code == 200
            data = response.json()
            assert data["post_id"] == 1
            assert data["likes_count"] == 3
            assert data["is_liked"] == False  # User 1 didn't like the post
        finally:
            app.dependency_overrides.clear()
    
    def test_get_post_likes_no_likes(self, client, mock_cache_manager, sample_posts):
        """Test post likes retrieval for post with no likes"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        mock_cache_manager.likes = {1: set()}  # No likes for post 1
        
        response = client.get("/api/v1/posts/1/likes")
        
        assert response.status_code == 200
        data = response.json()
        assert data["post_id"] == 1
        assert data["likes_count"] == 0
        assert data["is_liked"] == False
    
    def test_get_post_likes_post_not_found(self, client, mock_cache_manager):
        """Test post likes retrieval for non-existent post"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = None
        
        response = client.get("/api/v1/posts/999/likes")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"]
        assert "999" in data["message"]
    
    def test_get_post_likes_cache_not_initialized(self, client, mock_cache_manager):
        """Test post likes retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/posts/1/likes")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
    
    def test_get_post_likes_server_error(self, client, mock_cache_manager):
        """Test server error handling for post likes"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/posts/1/likes")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve post likes" in data["message"]


class TestGetUserBookmarks:
    """Test GET /api/v1/users/{user_id}/bookmarks endpoint"""
    
    def test_get_user_bookmarks_success(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test successful user bookmarks retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_bookmarks.return_value = sample_posts
        mock_cache_manager.likes = {1: {1}, 2: {1}}  # User 1 liked both posts
        mock_cache_manager.bookmarks = {1: {1, 2}}  # User 1 bookmarked both posts
        
        response = client.get("/api/v1/users/1/bookmarks")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["post_id"] == 1
        assert data[1]["post_id"] == 2
        
        mock_cache_manager.get_user_by_id.assert_called_once_with(1)
        mock_cache_manager.get_user_bookmarks.assert_called_once_with(
            user_id=1, skip=0, limit=20
        )
    
    def test_get_user_bookmarks_with_pagination(self, client, mock_cache_manager, sample_user, sample_posts):
        """Test user bookmarks retrieval with pagination"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_bookmarks.return_value = sample_posts[1:]
        mock_cache_manager.likes = {2: set()}
        mock_cache_manager.bookmarks = {1: {2}}
        
        response = client.get("/api/v1/users/1/bookmarks?skip=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["post_id"] == 2
        
        mock_cache_manager.get_user_bookmarks.assert_called_once_with(
            user_id=1, skip=1, limit=10
        )
    
    def test_get_user_bookmarks_with_authenticated_user(self, client, mock_cache_manager, sample_user, sample_user2, sample_posts):
        """Test user bookmarks retrieval with authenticated user viewing"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_bookmarks.return_value = sample_posts
        mock_cache_manager.likes = {1: {2}, 2: {2}}  # User 2 liked both posts
        mock_cache_manager.bookmarks = {1: {1, 2}, 2: {1}}  # User 2 bookmarked post 1 only
        
        # Mock the dependency directly in the app
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user2  # User 2 is viewing user 1's bookmarks
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            response = client.get("/api/v1/users/1/bookmarks")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            
            # Check that user-specific flags are set correctly for user 2
            post1 = next(p for p in data if p["post_id"] == 1)
            post2 = next(p for p in data if p["post_id"] == 2)
            
            assert post1["is_liked"] == True  # User 2 liked post 1
            assert post1["is_bookmarked"] == True  # User 2 bookmarked post 1
            assert post2["is_liked"] == True  # User 2 liked post 2
            assert post2["is_bookmarked"] == False  # User 2 didn't bookmark post 2
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_bookmarks_empty_result(self, client, mock_cache_manager, sample_user):
        """Test user bookmarks retrieval with no bookmarks"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        mock_cache_manager.get_user_bookmarks.return_value = []
        
        response = client.get("/api/v1/users/1/bookmarks")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_get_user_bookmarks_user_not_found(self, client, mock_cache_manager):
        """Test user bookmarks retrieval for non-existent user"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = None
        
        response = client.get("/api/v1/users/999/bookmarks")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"]
        assert "999" in data["message"]
    
    def test_get_user_bookmarks_cache_not_initialized(self, client, mock_cache_manager):
        """Test user bookmarks retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/users/1/bookmarks")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
    
    def test_get_user_bookmarks_invalid_pagination(self, client, mock_cache_manager, sample_user):
        """Test user bookmarks retrieval with invalid pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = sample_user
        
        # Test negative skip
        response = client.get("/api/v1/users/1/bookmarks?skip=-1")
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get("/api/v1/users/1/bookmarks?limit=200")
        assert response.status_code == 422
        
        # Test limit too small
        response = client.get("/api/v1/users/1/bookmarks?limit=0")
        assert response.status_code == 422
    
    def test_get_user_bookmarks_server_error(self, client, mock_cache_manager):
        """Test server error handling for user bookmarks"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/users/1/bookmarks")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve user bookmarks" in data["message"]


class TestLikesBookmarksIntegration:
    """Integration tests for likes and bookmarks functionality"""
    
    def test_post_response_includes_like_bookmark_flags(self, client, sample_user, sample_posts):
        """Test that post responses include correct like and bookmark flags"""
        # This test verifies that the existing posts endpoints correctly set
        # is_liked and is_bookmarked flags, which is part of task 7 requirements
        
        # Mock both cache managers (posts and likes_bookmarks)
        with patch('api.posts.cache_manager') as mock_posts_cache, \
             patch('api.likes_bookmarks.cache_manager') as mock_likes_cache:
            
            mock_posts_cache.is_initialized.return_value = True
            mock_posts_cache.get_posts.return_value = sample_posts
            mock_likes_cache.is_initialized.return_value = True
            
            # Mock the dependency directly in the app
            from main import app
            from auth.middleware import get_current_user_optional
            
            def mock_get_current_user():
                return sample_user
            
            app.dependency_overrides[get_current_user_optional] = mock_get_current_user
            
            try:
                response = client.get("/api/v1/posts")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify that posts include like and bookmark information
                for post in data:
                    assert "likes_count" in post
                    assert "is_liked" in post
                    assert "is_bookmarked" in post
                    assert isinstance(post["likes_count"], int)
                    assert isinstance(post["is_liked"], bool)
                    assert isinstance(post["is_bookmarked"], bool)
            finally:
                app.dependency_overrides.clear()
    
    def test_likes_and_bookmarks_consistency(self, client, sample_user, sample_posts):
        """Test consistency between likes/bookmarks endpoints and post responses"""
        
        # Mock both cache managers (posts and likes_bookmarks)
        with patch('api.posts.cache_manager') as mock_posts_cache, \
             patch('api.likes_bookmarks.cache_manager') as mock_likes_cache:
            
            # Set up posts cache mock
            mock_posts_cache.is_initialized.return_value = True
            mock_posts_cache.get_post_by_id.return_value = sample_posts[0]
            
            # Set up likes/bookmarks cache mock
            mock_likes_cache.is_initialized.return_value = True
            mock_likes_cache.get_post_by_id.return_value = sample_posts[0]
            mock_likes_cache.get_user_by_id.return_value = sample_user
            mock_likes_cache.get_user_bookmarks.return_value = [sample_posts[0]]
            mock_likes_cache.likes = {1: {1, 2, 3}}  # 3 likes for post 1, including user 1
            mock_likes_cache.bookmarks = {1: {1}}  # User 1 bookmarked post 1
            
            # Mock the dependency directly in the app
            from main import app
            from auth.middleware import get_current_user_optional
            
            def mock_get_current_user():
                return sample_user
            
            app.dependency_overrides[get_current_user_optional] = mock_get_current_user
            
            try:
                # Get post likes
                likes_response = client.get("/api/v1/posts/1/likes")
                assert likes_response.status_code == 200
                likes_data = likes_response.json()
                
                # Get user bookmarks
                bookmarks_response = client.get("/api/v1/users/1/bookmarks")
                assert bookmarks_response.status_code == 200
                bookmarks_data = bookmarks_response.json()
                
                # Get single post
                post_response = client.get("/api/v1/posts/1")
                assert post_response.status_code == 200
                post_data = post_response.json()
                
                # Verify consistency
                assert likes_data["likes_count"] == 3
                assert likes_data["is_liked"] == True
                assert post_data["is_bookmarked"] == True  # User bookmarked this post
                
                # Verify post appears in bookmarks
                assert len(bookmarks_data) == 1
                assert bookmarks_data[0]["post_id"] == 1
                assert bookmarks_data[0]["is_bookmarked"] == True
            finally:
                app.dependency_overrides.clear()
    
    def test_likes_bookmarks_different_users(self, client, mock_cache_manager, sample_user, sample_user2, sample_posts):
        """Test likes and bookmarks behavior with different users"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_posts[0]
        mock_cache_manager.get_user_by_id.return_value = sample_user2
        mock_cache_manager.get_user_bookmarks.return_value = []
        mock_cache_manager.likes = {1: {1}}  # Only user 1 liked post 1
        mock_cache_manager.bookmarks = {1: {1}, 2: set()}  # Only user 1 bookmarked post 1
        
        # Test with user 2 (who didn't like or bookmark)
        from main import app
        from auth.middleware import get_current_user_optional
        
        def mock_get_current_user():
            return sample_user2
        
        app.dependency_overrides[get_current_user_optional] = mock_get_current_user
        
        try:
            # Get post likes as user 2
            likes_response = client.get("/api/v1/posts/1/likes")
            assert likes_response.status_code == 200
            likes_data = likes_response.json()
            assert likes_data["likes_count"] == 1
            assert likes_data["is_liked"] == False  # User 2 didn't like it
            
            # Get user 2's bookmarks (should be empty)
            bookmarks_response = client.get("/api/v1/users/2/bookmarks")
            assert bookmarks_response.status_code == 200
            bookmarks_data = bookmarks_response.json()
            assert len(bookmarks_data) == 0
        finally:
            app.dependency_overrides.clear()


class TestLikesBookmarksErrorHandling:
    """Test error handling for likes and bookmarks endpoints"""
    
    def test_likes_endpoint_various_errors(self, client, mock_cache_manager):
        """Test various error scenarios for likes endpoint"""
        # Test with invalid post ID type (should be handled by FastAPI)
        response = client.get("/api/v1/posts/invalid/likes")
        assert response.status_code == 422
        
        # Test with very large post ID
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = None
        
        response = client.get("/api/v1/posts/999999999/likes")
        assert response.status_code == 404
    
    def test_bookmarks_endpoint_various_errors(self, client, mock_cache_manager):
        """Test various error scenarios for bookmarks endpoint"""
        # Test with invalid user ID type (should be handled by FastAPI)
        response = client.get("/api/v1/users/invalid/bookmarks")
        assert response.status_code == 422
        
        # Test with very large user ID
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_user_by_id.return_value = None
        
        response = client.get("/api/v1/users/999999999/bookmarks")
        assert response.status_code == 404