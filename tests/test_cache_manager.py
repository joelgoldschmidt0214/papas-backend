"""
Unit tests for cache manager system
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, UTC
from sqlalchemy.orm import Session

from cache.manager import CacheManager
from db_control import mymodels_MySQL as models
from models.responses import UserResponse, PostResponse, TagResponse, CommentResponse, SurveyResponse


class TestCacheManager:
    """Test cases for CacheManager class"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create a fresh cache manager instance for each test"""
        return CacheManager()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_users(self):
        """Sample user data for testing"""
        return [
            models.USERS(
                user_id=1,
                username="user1",
                display_name="User One",
                email="user1@example.com",
                profile_image_url=None,
                bio="Test user 1",
                area="Tokyo",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            models.USERS(
                user_id=2,
                username="user2",
                display_name="User Two",
                email="user2@example.com",
                profile_image_url=None,
                bio="Test user 2",
                area="Osaka",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        ]
    
    @pytest.fixture
    def sample_tags(self):
        """Sample tag data for testing"""
        return [
            models.TAGS(tag_id=1, tag_name="イベント"),
            models.TAGS(tag_id=2, tag_name="お祭り"),
            models.TAGS(tag_id=3, tag_name="地域情報")
        ]
    
    @pytest.fixture
    def sample_posts(self, sample_users):
        """Sample post data for testing"""
        return [
            models.POSTS(
                post_id=1,
                user_id=1,
                content="地域のお祭り情報です！",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            models.POSTS(
                post_id=2,
                user_id=2,
                content="新しいカフェがオープンしました",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        ]
    
    @pytest.fixture
    def sample_comments(self, sample_users, sample_posts):
        """Sample comment data for testing"""
        return [
            models.COMMENTS(
                comment_id=1,
                post_id=1,
                user_id=2,
                content="素晴らしい情報ですね！",
                created_at=datetime.now(UTC)
            ),
            models.COMMENTS(
                comment_id=2,
                post_id=1,
                user_id=1,
                content="ありがとうございます",
                created_at=datetime.now(UTC)
            )
        ]
    
    def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initial state"""
        assert not cache_manager.is_initialized()
        assert cache_manager.cache_stats["initialized"] is False
        assert len(cache_manager.posts) == 0
        assert len(cache_manager.users) == 0
        assert len(cache_manager.comments) == 0
        assert len(cache_manager.tags) == 0
        assert len(cache_manager.surveys) == 0
    
    @patch('cache.manager.crud')
    def test_load_users(self, mock_crud, cache_manager, mock_db_session, sample_users):
        """Test loading users into cache"""
        mock_crud.select_users.return_value = sample_users
        
        cache_manager._load_users(mock_db_session)
        
        assert len(cache_manager.users) == 2
        assert 1 in cache_manager.users
        assert 2 in cache_manager.users
        assert cache_manager.users[1].username == "user1"
        assert cache_manager.users[2].username == "user2"
        mock_crud.select_users.assert_called_once_with(mock_db_session, skip=0, limit=10000)
    
    def test_load_tags(self, cache_manager, mock_db_session, sample_tags):
        """Test loading tags into cache"""
        # Mock database query for tags
        mock_db_session.query.return_value.all.return_value = sample_tags
        
        # Mock post count queries
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [5, 3, 2]
        
        cache_manager._load_tags(mock_db_session)
        
        assert len(cache_manager.tags) == 3
        assert "イベント" in cache_manager.tags
        assert "お祭り" in cache_manager.tags
        assert "地域情報" in cache_manager.tags
        assert cache_manager.tags["イベント"].posts_count == 5
        assert cache_manager.tags["お祭り"].posts_count == 3
    
    @patch('cache.manager.crud')
    def test_load_posts(self, mock_crud, cache_manager, mock_db_session, sample_users, sample_posts, sample_tags):
        """Test loading posts into cache"""
        # Setup users in cache first
        for user in sample_users:
            cache_manager.users[user.user_id] = UserResponse(
                user_id=user.user_id,
                username=user.username,
                display_name=user.display_name,
                email=user.email,
                profile_image_url=user.profile_image_url,
                bio=user.bio,
                area=user.area,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        
        # Setup tags in cache
        for tag in sample_tags:
            cache_manager.tags[tag.tag_name] = TagResponse(
                tag_id=tag.tag_id,
                tag_name=tag.tag_name,
                posts_count=0
            )
        
        mock_crud.select_posts.return_value = sample_posts
        
        # Mock tag relationships query
        mock_db_session.query.return_value.join.return_value.filter.return_value.all.side_effect = [
            [(Mock(), sample_tags[0]), (Mock(), sample_tags[1])],  # Post 1 has tags 1 and 2
            [(Mock(), sample_tags[2])]  # Post 2 has tag 3
        ]
        
        cache_manager._load_posts(mock_db_session)
        
        assert len(cache_manager.posts) == 2
        assert 1 in cache_manager.posts
        assert 2 in cache_manager.posts
        assert cache_manager.posts[1].content == "地域のお祭り情報です！"
        assert cache_manager.posts[1].author.username == "user1"
        assert len(cache_manager.posts[1].tags) == 2
        
        # Check tag relationships
        assert 1 in cache_manager.post_tags
        assert len(cache_manager.post_tags[1]) == 2
        assert "イベント" in cache_manager.tag_posts
        assert 1 in cache_manager.tag_posts["イベント"]
    
    def test_load_comments(self, cache_manager, mock_db_session, sample_users, sample_comments):
        """Test loading comments into cache"""
        # Setup users in cache first
        for user in sample_users:
            cache_manager.users[user.user_id] = UserResponse(
                user_id=user.user_id,
                username=user.username,
                display_name=user.display_name,
                email=user.email,
                profile_image_url=user.profile_image_url,
                bio=user.bio,
                area=user.area,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        
        # Setup a post in cache
        cache_manager.posts[1] = PostResponse(
            post_id=1,
            user_id=1,
            content="Test post",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=cache_manager.users[1],
            tags=[],
            likes_count=0,
            comments_count=0,
            is_liked=False,
            is_bookmarked=False
        )
        
        mock_db_session.query.return_value.order_by.return_value.all.return_value = sample_comments
        
        cache_manager._load_comments(mock_db_session)
        
        assert len(cache_manager.comments) == 1
        assert 1 in cache_manager.comments
        assert len(cache_manager.comments[1]) == 2
        assert cache_manager.comments[1][0].content == "素晴らしい情報ですね！"
        assert cache_manager.posts[1].comments_count == 2
    
    def test_load_likes(self, cache_manager, mock_db_session):
        """Test loading likes into cache"""
        # Setup a post in cache
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        cache_manager.posts[1] = PostResponse(
            post_id=1,
            user_id=1,
            content="Test post",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=user,
            tags=[],
            likes_count=0,
            comments_count=0,
            is_liked=False,
            is_bookmarked=False
        )
        
        sample_likes = [
            models.LIKES(user_id=1, post_id=1),
            models.LIKES(user_id=2, post_id=1),
            models.LIKES(user_id=3, post_id=1)
        ]
        
        mock_db_session.query.return_value.all.return_value = sample_likes
        
        cache_manager._load_likes(mock_db_session)
        
        assert len(cache_manager.likes[1]) == 3
        assert 1 in cache_manager.likes[1]
        assert 2 in cache_manager.likes[1]
        assert 3 in cache_manager.likes[1]
        assert cache_manager.posts[1].likes_count == 3
    
    def test_load_bookmarks(self, cache_manager, mock_db_session):
        """Test loading bookmarks into cache"""
        sample_bookmarks = [
            models.BOOKMARKS(user_id=1, post_id=1),
            models.BOOKMARKS(user_id=1, post_id=2),
            models.BOOKMARKS(user_id=2, post_id=1)
        ]
        
        mock_db_session.query.return_value.all.return_value = sample_bookmarks
        
        cache_manager._load_bookmarks(mock_db_session)
        
        assert len(cache_manager.bookmarks[1]) == 2
        assert 1 in cache_manager.bookmarks[1]
        assert 2 in cache_manager.bookmarks[1]
        assert len(cache_manager.bookmarks[2]) == 1
        assert 1 in cache_manager.bookmarks[2]
    
    def test_load_follows(self, cache_manager, mock_db_session):
        """Test loading follow relationships into cache"""
        sample_follows = [
            models.FOLLOWS(follower_id=1, following_id=2),
            models.FOLLOWS(follower_id=1, following_id=3),
            models.FOLLOWS(follower_id=2, following_id=1)
        ]
        
        mock_db_session.query.return_value.all.return_value = sample_follows
        
        cache_manager._load_follows(mock_db_session)
        
        # Check follows relationships
        assert len(cache_manager.follows[1]) == 2
        assert 2 in cache_manager.follows[1]
        assert 3 in cache_manager.follows[1]
        assert len(cache_manager.follows[2]) == 1
        assert 1 in cache_manager.follows[2]
        
        # Check followers relationships
        assert len(cache_manager.followers[1]) == 1
        assert 2 in cache_manager.followers[1]
        assert len(cache_manager.followers[2]) == 1
        assert 1 in cache_manager.followers[2]
    
    @patch('cache.manager.crud')
    def test_load_surveys(self, mock_crud, cache_manager, mock_db_session):
        """Test loading surveys into cache"""
        sample_surveys = [
            models.SURVEYS(
                survey_id=1,
                title="地域アンケート",
                question_text="地域の課題について",
                points=10,
                deadline=None,
                target_audience="all",
                created_at=datetime.now(UTC)
            )
        ]
        
        mock_crud.select_surveys.return_value = sample_surveys
        mock_db_session.query.return_value.filter.return_value.count.return_value = 5
        
        cache_manager._load_surveys(mock_db_session)
        
        assert len(cache_manager.surveys) == 1
        assert 1 in cache_manager.surveys
        assert cache_manager.surveys[1].title == "地域アンケート"
        assert cache_manager.surveys[1].response_count == 5
    
    @patch('cache.manager.crud')
    def test_full_initialization_success(self, mock_crud, cache_manager, mock_db_session):
        """Test successful cache initialization process"""
        # Mock all CRUD calls to return empty lists for simplicity
        mock_crud.select_users.return_value = []
        mock_crud.select_posts.return_value = []
        mock_crud.select_surveys.return_value = []
        
        # Mock all database queries to return empty results
        mock_query = Mock()
        mock_query.all.return_value = []
        mock_query.filter.return_value.count.return_value = 0
        mock_query.order_by.return_value.all.return_value = []
        mock_query.join.return_value.filter.return_value.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        result = cache_manager.initialize(mock_db_session)
        
        assert result is True
        assert cache_manager.is_initialized()
        assert cache_manager.cache_stats["initialized"] is True
        assert cache_manager.cache_stats["initialization_time"] is not None
    
    def test_initialization_failure(self, cache_manager, mock_db_session):
        """Test cache initialization failure handling"""
        # Mock CRUD to raise an exception
        with patch('cache.manager.crud') as mock_crud:
            mock_crud.select_users.side_effect = Exception("Database error")
            
            result = cache_manager.initialize(mock_db_session)
            
            assert result is False
            assert not cache_manager.is_initialized()
            assert cache_manager.cache_stats["initialized"] is False
    
    def test_get_posts_uninitialized(self, cache_manager):
        """Test getting posts when cache is not initialized"""
        result = cache_manager.get_posts()
        assert result == []
    
    def test_get_posts_with_pagination(self, cache_manager):
        """Test getting posts with pagination"""
        # Setup cache as initialized
        cache_manager.cache_stats["initialized"] = True
        
        # Add sample posts
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        for i in range(5):
            post = PostResponse(
                post_id=i+1,
                user_id=1,
                content=f"Post {i+1}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                author=user,
                tags=[],
                likes_count=0,
                comments_count=0,
                is_liked=False,
                is_bookmarked=False
            )
            cache_manager.posts[i+1] = post
        
        # Test pagination
        result = cache_manager.get_posts(skip=0, limit=3)
        assert len(result) == 3
        
        result = cache_manager.get_posts(skip=3, limit=3)
        assert len(result) == 2
    
    def test_get_posts_with_user_flags(self, cache_manager):
        """Test getting posts with user-specific flags"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        post = PostResponse(
            post_id=1,
            user_id=1,
            content="Test post",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=user,
            tags=[],
            likes_count=1,
            comments_count=0,
            is_liked=False,
            is_bookmarked=False
        )
        cache_manager.posts[1] = post
        
        # Setup likes and bookmarks
        cache_manager.likes[1].add(2)  # User 2 liked post 1
        cache_manager.bookmarks[2].add(1)  # User 2 bookmarked post 1
        
        result = cache_manager.get_posts(current_user_id=2)
        assert len(result) == 1
        assert result[0].is_liked is True
        assert result[0].is_bookmarked is True
    
    def test_get_post_by_id(self, cache_manager):
        """Test getting a single post by ID"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        post = PostResponse(
            post_id=1,
            user_id=1,
            content="Test post",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=user,
            tags=[],
            likes_count=0,
            comments_count=0,
            is_liked=False,
            is_bookmarked=False
        )
        cache_manager.posts[1] = post
        
        result = cache_manager.get_post_by_id(1)
        assert result is not None
        assert result.post_id == 1
        assert result.content == "Test post"
        
        # Test non-existent post
        result = cache_manager.get_post_by_id(999)
        assert result is None
    
    def test_get_posts_by_tag(self, cache_manager):
        """Test getting posts filtered by tag"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        # Create posts
        for i in range(3):
            post = PostResponse(
                post_id=i+1,
                user_id=1,
                content=f"Post {i+1}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                author=user,
                tags=[],
                likes_count=0,
                comments_count=0,
                is_liked=False,
                is_bookmarked=False
            )
            cache_manager.posts[i+1] = post
        
        # Setup tag relationships
        cache_manager.tag_posts["イベント"] = [1, 3]  # Posts 1 and 3 have "イベント" tag
        
        result = cache_manager.get_posts_by_tag("イベント")
        assert len(result) == 2
        assert result[0].post_id in [1, 3]
        assert result[1].post_id in [1, 3]
        
        # Test non-existent tag
        result = cache_manager.get_posts_by_tag("存在しないタグ")
        assert result == []
    
    def test_get_user_profile(self, cache_manager):
        """Test getting user profile with relationship counts"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        cache_manager.users[1] = user
        
        # Setup relationships
        cache_manager.followers[1] = {2, 3}  # User 1 has 2 followers
        cache_manager.follows[1] = {4, 5}    # User 1 follows 2 users
        
        # Add posts by user 1
        for i in range(3):
            post = PostResponse(
                post_id=i+1,
                user_id=1,
                content=f"Post {i+1}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                author=user,
                tags=[],
                likes_count=0,
                comments_count=0,
                is_liked=False,
                is_bookmarked=False
            )
            cache_manager.posts[i+1] = post
        
        result = cache_manager.get_user_profile(1)
        assert result is not None
        assert result.user_id == 1
        assert result.followers_count == 2
        assert result.following_count == 2
        assert result.posts_count == 3
        
        # Test non-existent user
        result = cache_manager.get_user_profile(999)
        assert result is None
    
    def test_get_comments_by_post_id(self, cache_manager):
        """Test getting comments for a specific post"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        # Add comments
        for i in range(5):
            comment = CommentResponse(
                comment_id=i+1,
                post_id=1,
                user_id=1,
                content=f"Comment {i+1}",
                created_at=datetime.now(UTC),
                author=user
            )
            cache_manager.comments[1].append(comment)
        
        result = cache_manager.get_comments_by_post_id(1, skip=0, limit=3)
        assert len(result) == 3
        
        result = cache_manager.get_comments_by_post_id(1, skip=3, limit=3)
        assert len(result) == 2
        
        # Test non-existent post
        result = cache_manager.get_comments_by_post_id(999)
        assert result == []
    
    def test_get_user_bookmarks(self, cache_manager):
        """Test getting user bookmarks"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        # Create posts
        for i in range(3):
            post = PostResponse(
                post_id=i+1,
                user_id=1,
                content=f"Post {i+1}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                author=user,
                tags=[],
                likes_count=0,
                comments_count=0,
                is_liked=False,
                is_bookmarked=False
            )
            cache_manager.posts[i+1] = post
        
        # Setup bookmarks
        cache_manager.bookmarks[1] = {1, 3}  # User 1 bookmarked posts 1 and 3
        
        result = cache_manager.get_user_bookmarks(1)
        assert len(result) == 2
        for post in result:
            assert post.is_bookmarked is True
            assert post.post_id in [1, 3]
    
    def test_get_user_followers_and_following(self, cache_manager):
        """Test getting user followers and following lists"""
        cache_manager.cache_stats["initialized"] = True
        
        # Create users
        for i in range(5):
            user = UserResponse(
                user_id=i+1, username=f"user{i+1}", display_name=f"User {i+1}",
                email=f"user{i+1}@example.com", profile_image_url=None,
                bio=f"Test user {i+1}", area="Tokyo",
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
            )
            cache_manager.users[i+1] = user
        
        # Setup relationships
        cache_manager.followers[1] = {2, 3, 4}  # Users 2, 3, 4 follow user 1
        cache_manager.follows[1] = {3, 5}       # User 1 follows users 3, 5
        
        followers = cache_manager.get_user_followers(1)
        assert len(followers) == 3
        
        following = cache_manager.get_user_following(1)
        assert len(following) == 2
    
    def test_add_post_to_cache(self, cache_manager):
        """Test adding a new post to cache"""
        cache_manager.cache_stats["initialized"] = True
        
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        # Add existing tag
        cache_manager.tags["イベント"] = TagResponse(
            tag_id=1, tag_name="イベント", posts_count=0
        )
        
        post_data = {"content": "新しい投稿です"}
        tags = ["イベント", "新しいタグ"]
        
        result = cache_manager.add_post_to_cache(post_data, user, tags)
        
        assert result.post_id == 1
        assert result.content == "新しい投稿です"
        assert result.user_id == 1
        assert len(result.tags) == 2
        assert result.tags[0].tag_name == "イベント"
        assert result.tags[1].tag_name == "新しいタグ"
        
        # Check cache updates
        assert 1 in cache_manager.posts
        assert "新しいタグ" in cache_manager.tags
        assert 1 in cache_manager.tag_posts["イベント"]
        assert 1 in cache_manager.tag_posts["新しいタグ"]
        assert cache_manager.cache_stats["posts_count"] == 1
    
    def test_add_post_to_cache_uninitialized(self, cache_manager):
        """Test adding post to uninitialized cache raises error"""
        user = UserResponse(
            user_id=1, username="user1", display_name="User One",
            email="user1@example.com", profile_image_url=None,
            bio="Test user", area="Tokyo",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
        )
        
        post_data = {"content": "Test post"}
        
        with pytest.raises(RuntimeError, match="Cache not initialized"):
            cache_manager.add_post_to_cache(post_data, user)
    
    def test_get_cache_stats(self, cache_manager):
        """Test getting cache statistics"""
        stats = cache_manager.get_cache_stats()
        
        assert "initialized" in stats
        assert "initialization_time" in stats
        assert "posts_count" in stats
        assert "users_count" in stats
        assert "comments_count" in stats
        assert "tags_count" in stats
        assert "surveys_count" in stats
        
        # Ensure it returns a copy, not the original
        stats["initialized"] = True
        assert cache_manager.cache_stats["initialized"] is False
    
    def test_get_tags(self, cache_manager):
        """Test getting all tags"""
        cache_manager.cache_stats["initialized"] = True
        
        # Add sample tags
        for i, tag_name in enumerate(["イベント", "お祭り", "地域情報"], 1):
            cache_manager.tags[tag_name] = TagResponse(
                tag_id=i, tag_name=tag_name, posts_count=0
            )
        
        result = cache_manager.get_tags()
        assert len(result) == 3
        tag_names = [tag.tag_name for tag in result]
        assert "イベント" in tag_names
        assert "お祭り" in tag_names
        assert "地域情報" in tag_names
    
    def test_get_surveys(self, cache_manager):
        """Test getting surveys with pagination"""
        cache_manager.cache_stats["initialized"] = True
        
        # Add sample surveys
        for i in range(5):
            survey = SurveyResponse(
                survey_id=i+1,
                title=f"Survey {i+1}",
                question_text=f"Question {i+1}",
                points=10,
                deadline=None,
                target_audience="all",
                created_at=datetime.now(UTC),
                response_count=0
            )
            cache_manager.surveys[i+1] = survey
        
        result = cache_manager.get_surveys(skip=0, limit=3)
        assert len(result) == 3
        
        result = cache_manager.get_surveys(skip=3, limit=3)
        assert len(result) == 2
    
    def test_get_survey_by_id(self, cache_manager):
        """Test getting a single survey by ID"""
        cache_manager.cache_stats["initialized"] = True
        
        survey = SurveyResponse(
            survey_id=1,
            title="Test Survey",
            question_text="Test Question",
            points=10,
            deadline=None,
            target_audience="all",
            created_at=datetime.now(UTC),
            response_count=5
        )
        cache_manager.surveys[1] = survey
        
        result = cache_manager.get_survey_by_id(1)
        assert result is not None
        assert result.survey_id == 1
        assert result.title == "Test Survey"
        
        # Test non-existent survey
        result = cache_manager.get_survey_by_id(999)
        assert result is None