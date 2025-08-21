"""
Integration tests for comments API endpoints
Tests comments endpoints with cache integration
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from main import app
from models.responses import CommentResponse, UserResponse, PostResponse, TagResponse
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
def sample_author():
    """Sample comment author for testing"""
    return UserResponse(
        user_id=2,
        username="commenter",
        display_name="Comment Author",
        email="commenter@example.com",
        profile_image_url=None,
        bio="Comment author bio",
        area="Comment Area",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def sample_post(sample_user):
    """Sample post for testing"""
    tag1 = TagResponse(tag_id=1, tag_name="テスト", posts_count=1)
    
    return PostResponse(
        post_id=1,
        user_id=1,
        content="テスト投稿です",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author=sample_user,
        tags=[tag1],
        likes_count=5,
        comments_count=3,
        is_liked=False,
        is_bookmarked=False
    )


@pytest.fixture
def sample_comments(sample_author):
    """Sample comments for testing"""
    base_time = datetime.now(UTC)
    
    return [
        CommentResponse(
            comment_id=1,
            post_id=1,
            user_id=2,
            content="最初のコメントです",
            created_at=base_time,
            author=sample_author
        ),
        CommentResponse(
            comment_id=2,
            post_id=1,
            user_id=2,
            content="2番目のコメントです",
            created_at=base_time.replace(minute=base_time.minute + 1),
            author=sample_author
        ),
        CommentResponse(
            comment_id=3,
            post_id=1,
            user_id=2,
            content="3番目のコメントです",
            created_at=base_time.replace(minute=base_time.minute + 2),
            author=sample_author
        )
    ]


class TestGetPostComments:
    """Test GET /api/v1/posts/{post_id}/comments endpoint"""
    
    def test_get_post_comments_success(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test successful comments retrieval for a post"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Verify comments are returned with proper structure
        assert data[0]["comment_id"] == 1
        assert data[0]["post_id"] == 1
        assert data[0]["content"] == "最初のコメントです"
        assert data[0]["author"]["username"] == "commenter"
        assert data[0]["author"]["display_name"] == "Comment Author"
        
        assert data[1]["comment_id"] == 2
        assert data[1]["content"] == "2番目のコメントです"
        
        assert data[2]["comment_id"] == 3
        assert data[2]["content"] == "3番目のコメントです"
        
        # Verify cache manager calls
        mock_cache_manager.get_post_by_id.assert_called_once_with(1)
        mock_cache_manager.get_comments_by_post_id.assert_called_once_with(
            post_id=1, skip=0, limit=50
        )
    
    def test_get_post_comments_with_pagination(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test comments retrieval with pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments[1:]
        
        response = client.get("/api/v1/posts/1/comments?skip=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["comment_id"] == 2
        assert data[1]["comment_id"] == 3
        
        mock_cache_manager.get_comments_by_post_id.assert_called_once_with(
            post_id=1, skip=1, limit=10
        )
    
    def test_get_post_comments_empty_result(self, client, mock_cache_manager, sample_post):
        """Test comments retrieval for post with no comments"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = []
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        
        mock_cache_manager.get_comments_by_post_id.assert_called_once_with(
            post_id=1, skip=0, limit=50
        )
    
    def test_get_post_comments_post_not_found(self, client, mock_cache_manager):
        """Test comments retrieval for non-existent post"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = None
        
        response = client.get("/api/v1/posts/999/comments")
        
        assert response.status_code == 404
        data = response.json()
        assert "Post with ID 999 not found" in data["message"]
        
        # Should not call get_comments_by_post_id if post doesn't exist
        mock_cache_manager.get_comments_by_post_id.assert_not_called()
    
    def test_get_post_comments_cache_not_initialized(self, client, mock_cache_manager):
        """Test comments retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
    
    def test_get_post_comments_invalid_pagination(self, client, mock_cache_manager, sample_post):
        """Test comments retrieval with invalid pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        
        # Test negative skip
        response = client.get("/api/v1/posts/1/comments?skip=-1")
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get("/api/v1/posts/1/comments?limit=200")
        assert response.status_code == 422
        
        # Test limit too small
        response = client.get("/api/v1/posts/1/comments?limit=0")
        assert response.status_code == 422
    
    def test_get_post_comments_chronological_order(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test that comments are returned in chronological order (oldest first)"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify comments are in chronological order (oldest first)
        # Comment IDs should be in ascending order as they were created chronologically
        comment_ids = [comment["comment_id"] for comment in data]
        assert comment_ids == [1, 2, 3]
        
        # Verify timestamps are in ascending order
        timestamps = [comment["created_at"] for comment in data]
        assert timestamps == sorted(timestamps)
    
    def test_get_post_comments_author_information(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test that comments include complete author information"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify each comment has complete author information
        for comment in data:
            author = comment["author"]
            assert "user_id" in author
            assert "username" in author
            assert "display_name" in author
            assert "email" in author
            assert "profile_image_url" in author
            assert "bio" in author
            assert "area" in author
            assert "created_at" in author
            assert "updated_at" in author
            
            # Verify author data matches expected values
            assert author["username"] == "commenter"
            assert author["display_name"] == "Comment Author"
            assert author["email"] == "commenter@example.com"


class TestCommentsErrorHandling:
    """Test error handling for comments endpoints"""
    
    def test_get_post_comments_server_error(self, client, mock_cache_manager, sample_post):
        """Test server error handling for comments retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve comments" in data["message"]
    
    def test_get_post_comments_post_check_error(self, client, mock_cache_manager):
        """Test server error handling when post existence check fails"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.side_effect = Exception("Database error")
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve comments" in data["message"]


class TestCommentsIntegrationWithPosts:
    """Integration tests for comments functionality with posts"""
    
    def test_post_response_includes_comments_count(self, client, mock_cache_manager, sample_post):
        """Test that post responses include accurate comments count"""
        # This test verifies that the comments_count field in PostResponse
        # reflects the actual number of comments (requirement 3.2)
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        
        response = client.get("/api/v1/posts/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["comments_count"] == 3  # As defined in sample_post fixture
    
    def test_comments_endpoint_consistency_with_post_count(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test that comments endpoint returns count consistent with post's comments_count"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        # Get post to check comments_count
        post_response = client.get("/api/v1/posts/1")
        assert post_response.status_code == 200
        post_data = post_response.json()
        
        # Get comments to verify actual count
        comments_response = client.get("/api/v1/posts/1/comments")
        assert comments_response.status_code == 200
        comments_data = comments_response.json()
        
        # Verify consistency
        assert post_data["comments_count"] == len(comments_data)


class TestCommentsRequirementCompliance:
    """Test compliance with specific requirements"""
    
    def test_requirement_3_1_comments_endpoint_implementation(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test requirement 3.1: Implement GET /api/v1/posts/{post_id}/comments endpoint"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0
    
    def test_requirement_3_2_author_information_included(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test requirement 3.2: Add comment data to post responses with author information"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify each comment includes author information
        for comment in data:
            assert "author" in comment
            author = comment["author"]
            assert "user_id" in author
            assert "username" in author
            assert "display_name" in author
    
    def test_requirement_3_3_chronological_sorting(self, client, mock_cache_manager, sample_post, sample_comments):
        """Test requirement 3.3: Ensure comments are sorted chronologically (oldest first)"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_post_by_id.return_value = sample_post
        mock_cache_manager.get_comments_by_post_id.return_value = sample_comments
        
        response = client.get("/api/v1/posts/1/comments")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify chronological order (oldest first)
        timestamps = [comment["created_at"] for comment in data]
        assert timestamps == sorted(timestamps), "Comments should be sorted chronologically (oldest first)"
        
        # Verify comment IDs are in ascending order (assuming they were created chronologically)
        comment_ids = [comment["comment_id"] for comment in data]
        assert comment_ids == sorted(comment_ids), "Comment IDs should be in ascending order"