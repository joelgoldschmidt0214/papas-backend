"""
Integration tests for tags API endpoints
Tests all tags endpoints with cache integration
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from main import app
from models.responses import TagResponse


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing"""
    with patch('api.tags.cache_manager') as mock:
        yield mock


@pytest.fixture
def sample_tags():
    """Sample tags for testing"""
    return [
        TagResponse(
            tag_id=1,
            tag_name="イベント",
            posts_count=15
        ),
        TagResponse(
            tag_id=2,
            tag_name="お祭り",
            posts_count=8
        ),
        TagResponse(
            tag_id=3,
            tag_name="地域",
            posts_count=25
        ),
        TagResponse(
            tag_id=4,
            tag_name="テスト",
            posts_count=3
        ),
        TagResponse(
            tag_id=5,
            tag_name="ニュース",
            posts_count=12
        )
    ]


class TestGetTags:
    """Test GET /api/v1/tags endpoint"""
    
    def test_get_tags_success(self, client, mock_cache_manager, sample_tags):
        """Test successful tags retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        
        # Verify tags are sorted alphabetically by tag name
        tag_names = [tag["tag_name"] for tag in data]
        assert tag_names == sorted(tag_names, key=str.lower)
        
        # Verify tag data structure
        assert data[0]["tag_id"] > 0
        assert data[0]["tag_name"]
        assert data[0]["posts_count"] >= 0
        
        mock_cache_manager.get_tags.assert_called_once()
    
    def test_get_tags_with_pagination(self, client, mock_cache_manager, sample_tags):
        """Test tags retrieval with pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        
        response = client.get("/api/v1/tags?skip=2&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should still be sorted alphabetically
        tag_names = [tag["tag_name"] for tag in data]
        assert tag_names == sorted(tag_names, key=str.lower)
        
        mock_cache_manager.get_tags.assert_called_once()
    
    def test_get_tags_empty_result(self, client, mock_cache_manager):
        """Test tags retrieval with no tags available"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = []
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        
        mock_cache_manager.get_tags.assert_called_once()
    
    def test_get_tags_cache_not_initialized(self, client, mock_cache_manager):
        """Test tags retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
        assert data["error_code"] == "HTTP_503"
    
    def test_get_tags_invalid_pagination(self, client, mock_cache_manager):
        """Test tags retrieval with invalid pagination parameters"""
        mock_cache_manager.is_initialized.return_value = True
        
        # Test negative skip
        response = client.get("/api/v1/tags?skip=-1")
        assert response.status_code == 422
        
        # Test limit too large
        response = client.get("/api/v1/tags?limit=1000")
        assert response.status_code == 422
        
        # Test limit too small
        response = client.get("/api/v1/tags?limit=0")
        assert response.status_code == 422
    
    def test_get_tags_large_limit(self, client, mock_cache_manager, sample_tags):
        """Test tags retrieval with maximum allowed limit"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        
        response = client.get("/api/v1/tags?limit=500")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # All available tags
        
        mock_cache_manager.get_tags.assert_called_once()


class TestGetTagByName:
    """Test GET /api/v1/tags/{tag_name} endpoint"""
    
    def test_get_tag_by_name_success(self, client, mock_cache_manager, sample_tags):
        """Test successful single tag retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.return_value = sample_tags[0]
        
        response = client.get("/api/v1/tags/イベント")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tag_id"] == 1
        assert data["tag_name"] == "イベント"
        assert data["posts_count"] == 15
        
        mock_cache_manager.get_tag_by_name.assert_called_once_with("イベント")
    
    def test_get_tag_by_name_not_found(self, client, mock_cache_manager):
        """Test tag retrieval for non-existent tag"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.return_value = None
        
        response = client.get("/api/v1/tags/存在しないタグ")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"]
        assert "存在しないタグ" in data["message"]
        assert data["error_code"] == "HTTP_404"
        
        mock_cache_manager.get_tag_by_name.assert_called_once_with("存在しないタグ")
    
    def test_get_tag_by_name_cache_not_initialized(self, client, mock_cache_manager):
        """Test tag retrieval when cache is not initialized"""
        mock_cache_manager.is_initialized.return_value = False
        
        response = client.get("/api/v1/tags/テスト")
        
        assert response.status_code == 503
        data = response.json()
        assert "cache not initialized" in data["message"]
        assert data["error_code"] == "HTTP_503"
    
    def test_get_tag_by_name_japanese_characters(self, client, mock_cache_manager, sample_tags):
        """Test tag retrieval with Japanese characters"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.return_value = sample_tags[1]
        
        response = client.get("/api/v1/tags/お祭り")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tag_name"] == "お祭り"
        
        mock_cache_manager.get_tag_by_name.assert_called_once_with("お祭り")
    
    def test_get_tag_by_name_english_characters(self, client, mock_cache_manager):
        """Test tag retrieval with English characters"""
        english_tag = TagResponse(
            tag_id=10,
            tag_name="test",
            posts_count=5
        )
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.return_value = english_tag
        
        response = client.get("/api/v1/tags/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tag_name"] == "test"
        
        mock_cache_manager.get_tag_by_name.assert_called_once_with("test")
    
    def test_get_tag_by_name_special_characters(self, client, mock_cache_manager):
        """Test tag retrieval with special characters"""
        special_tag = TagResponse(
            tag_id=11,
            tag_name="C++",
            posts_count=2
        )
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.return_value = special_tag
        
        response = client.get("/api/v1/tags/C++")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tag_name"] == "C++"
        
        mock_cache_manager.get_tag_by_name.assert_called_once_with("C++")


class TestTagsErrorHandling:
    """Test error handling for tags endpoints"""
    
    def test_get_tags_server_error(self, client, mock_cache_manager):
        """Test server error handling for tags list"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve tags" in data["message"]
        assert data["error_code"] == "HTTP_500"
    
    def test_get_tag_by_name_server_error(self, client, mock_cache_manager):
        """Test server error handling for single tag retrieval"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.side_effect = Exception("Cache error")
        
        response = client.get("/api/v1/tags/テスト")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve tag" in data["message"]
        assert data["error_code"] == "HTTP_500"
    
    def test_get_tags_http_exception_passthrough(self, client, mock_cache_manager):
        """Test that HTTP exceptions are passed through correctly"""
        from fastapi import HTTPException, status
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.side_effect = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Custom service error"
        )
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 503
        data = response.json()
        assert "Custom service error" in data["message"]
    
    def test_get_tag_by_name_http_exception_passthrough(self, client, mock_cache_manager):
        """Test that HTTP exceptions are passed through correctly for single tag"""
        from fastapi import HTTPException, status
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.side_effect = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Custom service error"
        )
        
        response = client.get("/api/v1/tags/テスト")
        
        assert response.status_code == 503
        data = response.json()
        assert "Custom service error" in data["message"]


class TestTagsIntegration:
    """Integration tests for tags functionality"""
    
    def test_tags_sorting_consistency(self, client, mock_cache_manager):
        """Test that tags are consistently sorted alphabetically"""
        # Create tags with mixed case and characters
        mixed_tags = [
            TagResponse(tag_id=1, tag_name="Zulu", posts_count=1),
            TagResponse(tag_id=2, tag_name="alpha", posts_count=2),
            TagResponse(tag_id=3, tag_name="Beta", posts_count=3),
            TagResponse(tag_id=4, tag_name="あいうえお", posts_count=4),
            TagResponse(tag_id=5, tag_name="かきくけこ", posts_count=5),
        ]
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = mixed_tags
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorting (case-insensitive)
        tag_names = [tag["tag_name"] for tag in data]
        expected_order = sorted([tag.tag_name for tag in mixed_tags], key=str.lower)
        assert tag_names == expected_order
    
    def test_tags_pagination_edge_cases(self, client, mock_cache_manager, sample_tags):
        """Test pagination edge cases"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        
        # Test skip beyond available tags
        response = client.get("/api/v1/tags?skip=100&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        
        # Test limit larger than available tags
        response = client.get("/api/v1/tags?skip=0&limit=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # All available tags
        
        # Test skip at exact boundary
        response = client.get("/api/v1/tags?skip=5&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_tags_response_structure(self, client, mock_cache_manager, sample_tags):
        """Test that tag responses have correct structure"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags[:1]
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        tag = data[0]
        # Verify all required fields are present
        assert "tag_id" in tag
        assert "tag_name" in tag
        assert "posts_count" in tag
        
        # Verify field types
        assert isinstance(tag["tag_id"], int)
        assert isinstance(tag["tag_name"], str)
        assert isinstance(tag["posts_count"], int)
        
        # Verify field constraints
        assert tag["tag_id"] > 0
        assert len(tag["tag_name"]) > 0
        assert tag["posts_count"] >= 0
    
    def test_tag_name_url_encoding(self, client, mock_cache_manager, sample_tags):
        """Test that tag names with special characters work correctly in URLs"""
        special_tag = TagResponse(
            tag_id=20,
            tag_name="test-tag",
            posts_count=7
        )
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tag_by_name.return_value = special_tag
        
        # Test with simple tag name first
        response = client.get("/api/v1/tags/test-tag")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tag_name"] == "test-tag"
        
        # Verify the mock was called with the tag name
        mock_cache_manager.get_tag_by_name.assert_called_once_with("test-tag")


class TestTagsRequirements:
    """Test that tags endpoints meet specific requirements"""
    
    def test_requirement_6_1_tags_list(self, client, mock_cache_manager, sample_tags):
        """Test requirement 6.1: Get available tags list"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all tags are returned
        assert len(data) == len(sample_tags)
        
        # Verify each tag has required information
        for tag in data:
            assert "tag_id" in tag
            assert "tag_name" in tag
            assert "posts_count" in tag
    
    def test_requirement_6_2_tag_post_counts(self, client, mock_cache_manager, sample_tags):
        """Test requirement 6.2: Tag information includes post counts"""
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all tags have post counts
        for tag in data:
            assert "posts_count" in tag
            assert isinstance(tag["posts_count"], int)
            assert tag["posts_count"] >= 0
    
    def test_requirement_6_3_tag_filtering_integration(self, client, mock_cache_manager, sample_tags):
        """Test requirement 6.3: Tag filtering works correctly with cache data"""
        # This test verifies that the tag endpoint returns tags that can be used
        # for filtering posts (integration with posts/tags/{tag_name} endpoint)
        
        mock_cache_manager.is_initialized.return_value = True
        mock_cache_manager.get_tags.return_value = sample_tags
        mock_cache_manager.get_tag_by_name.return_value = sample_tags[0]
        
        # First, get all tags
        response = client.get("/api/v1/tags")
        assert response.status_code == 200
        tags_data = response.json()
        
        # Then, verify we can get individual tags by name
        for tag in tags_data:
            tag_name = tag["tag_name"]
            mock_cache_manager.get_tag_by_name.return_value = TagResponse(**tag)
            
            response = client.get(f"/api/v1/tags/{tag_name}")
            assert response.status_code == 200
            
            individual_tag_data = response.json()
            assert individual_tag_data["tag_name"] == tag_name
            assert individual_tag_data["posts_count"] == tag["posts_count"]