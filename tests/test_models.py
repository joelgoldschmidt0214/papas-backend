"""
Unit tests for Pydantic models
"""
import pytest
from datetime import datetime, timedelta, UTC
from pydantic import ValidationError

from models import (
    ErrorResponse,
    UserResponse,
    UserProfileResponse,
    TagResponse,
    CommentResponse,
    PostResponse,
    SurveyResponse,
    PostRequest,
    UserProfileUpdateRequest,
)


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_error_response_valid(self):
        """Test valid ErrorResponse creation"""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message"
        )
        assert error.error_code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.details is None
        assert isinstance(error.timestamp, datetime)

    def test_error_response_with_details(self):
        """Test ErrorResponse with details"""
        details = {"field": "value", "code": 123}
        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            details=details
        )
        assert error.details == details

    def test_error_response_missing_required_fields(self):
        """Test ErrorResponse with missing required fields"""
        with pytest.raises(ValidationError):
            ErrorResponse()

        with pytest.raises(ValidationError):
            ErrorResponse(error_code="TEST")


class TestUserResponse:
    """Test UserResponse model"""

    def test_user_response_valid(self):
        """Test valid UserResponse creation"""
        user = UserResponse(
            user_id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        assert user.user_id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.display_name is None

    def test_user_response_with_optional_fields(self):
        """Test UserResponse with optional fields"""
        user = UserResponse(
            user_id=1,
            username="testuser",
            display_name="Test User",
            email="test@example.com",
            profile_image_url="https://example.com/image.jpg",
            bio="Test bio",
            area="Tokyo",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        assert user.display_name == "Test User"
        assert user.bio == "Test bio"
        assert user.area == "Tokyo"

    def test_user_response_invalid_user_id(self):
        """Test UserResponse with invalid user_id"""
        with pytest.raises(ValidationError):
            UserResponse(
                user_id=0,  # Invalid: must be > 0
                username="testuser",
                email="test@example.com",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )

    def test_user_response_invalid_email(self):
        """Test UserResponse with invalid email"""
        with pytest.raises(ValidationError):
            UserResponse(
                user_id=1,
                username="testuser",
                email="invalid-email",  # Invalid: no @
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )

    def test_user_response_empty_username(self):
        """Test UserResponse with empty username"""
        with pytest.raises(ValidationError):
            UserResponse(
                user_id=1,
                username="",  # Invalid: empty string
                email="test@example.com",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )


class TestUserProfileResponse:
    """Test UserProfileResponse model"""

    def test_user_profile_response_valid(self):
        """Test valid UserProfileResponse creation"""
        profile = UserProfileResponse(
            user_id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            followers_count=10,
            following_count=5,
            posts_count=20
        )
        assert profile.followers_count == 10
        assert profile.following_count == 5
        assert profile.posts_count == 20

    def test_user_profile_response_default_counts(self):
        """Test UserProfileResponse with default counts"""
        profile = UserProfileResponse(
            user_id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        assert profile.followers_count == 0
        assert profile.following_count == 0
        assert profile.posts_count == 0

    def test_user_profile_response_negative_counts(self):
        """Test UserProfileResponse with negative counts"""
        with pytest.raises(ValidationError):
            UserProfileResponse(
                user_id=1,
                username="testuser",
                email="test@example.com",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                followers_count=-1  # Invalid: must be >= 0
            )


class TestTagResponse:
    """Test TagResponse model"""

    def test_tag_response_valid(self):
        """Test valid TagResponse creation"""
        tag = TagResponse(
            tag_id=1,
            tag_name="テスト",
            posts_count=5
        )
        assert tag.tag_id == 1
        assert tag.tag_name == "テスト"
        assert tag.posts_count == 5

    def test_tag_response_default_posts_count(self):
        """Test TagResponse with default posts_count"""
        tag = TagResponse(
            tag_id=1,
            tag_name="テスト"
        )
        assert tag.posts_count == 0

    def test_tag_response_empty_tag_name(self):
        """Test TagResponse with empty tag name"""
        with pytest.raises(ValidationError):
            TagResponse(
                tag_id=1,
                tag_name=""  # Invalid: empty string
            )

    def test_tag_response_whitespace_tag_name(self):
        """Test TagResponse with whitespace-only tag name"""
        with pytest.raises(ValidationError):
            TagResponse(
                tag_id=1,
                tag_name="   "  # Invalid: whitespace only
            )

    def test_tag_response_strips_whitespace(self):
        """Test TagResponse strips whitespace from tag name"""
        tag = TagResponse(
            tag_id=1,
            tag_name="  テスト  "
        )
        assert tag.tag_name == "テスト"


class TestCommentResponse:
    """Test CommentResponse model"""

    def test_comment_response_valid(self):
        """Test valid CommentResponse creation"""
        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        comment = CommentResponse(
            comment_id=1,
            post_id=1,
            user_id=1,
            content="Test comment",
            created_at=datetime.now(UTC),
            author=author
        )
        assert comment.comment_id == 1
        assert comment.post_id == 1
        assert comment.content == "Test comment"
        assert comment.author.username == "author"

    def test_comment_response_empty_content(self):
        """Test CommentResponse with empty content"""
        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        with pytest.raises(ValidationError):
            CommentResponse(
                comment_id=1,
                post_id=1,
                user_id=1,
                content="",  # Invalid: empty content
                created_at=datetime.now(UTC),
                author=author
            )

    def test_comment_response_strips_whitespace(self):
        """Test CommentResponse strips whitespace from content"""
        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        comment = CommentResponse(
            comment_id=1,
            post_id=1,
            user_id=1,
            content="  Test comment  ",
            created_at=datetime.now(UTC),
            author=author
        )
        assert comment.content == "Test comment"


class TestPostResponse:
    """Test PostResponse model"""

    def test_post_response_valid(self):
        """Test valid PostResponse creation"""
        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        post = PostResponse(
            post_id=1,
            user_id=1,
            content="Test post content",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author=author
        )
        assert post.post_id == 1
        assert post.content == "Test post content"
        assert post.tags == []
        assert post.likes_count == 0
        assert post.is_liked is False

    def test_post_response_with_tags(self):
        """Test PostResponse with tags"""
        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        tags = [
            TagResponse(tag_id=1, tag_name="tag1"),
            TagResponse(tag_id=2, tag_name="tag2")
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
            is_bookmarked=True
        )
        assert len(post.tags) == 2
        assert post.likes_count == 5
        assert post.is_liked is True

    def test_post_response_empty_content(self):
        """Test PostResponse with empty content"""
        author = UserResponse(
            user_id=1,
            username="author",
            email="author@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        with pytest.raises(ValidationError):
            PostResponse(
                post_id=1,
                user_id=1,
                content="",  # Invalid: empty content
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                author=author
            )


class TestSurveyResponse:
    """Test SurveyResponse model"""

    def test_survey_response_valid(self):
        """Test valid SurveyResponse creation"""
        survey = SurveyResponse(
            survey_id=1,
            title="Test Survey",
            created_at=datetime.now(UTC)
        )
        assert survey.survey_id == 1
        assert survey.title == "Test Survey"
        assert survey.points == 0
        assert survey.target_audience == "all"

    def test_survey_response_with_optional_fields(self):
        """Test SurveyResponse with optional fields"""
        future_date = datetime.now(UTC) + timedelta(days=7)
        survey = SurveyResponse(
            survey_id=1,
            title="Test Survey",
            question_text="What do you think?",
            points=10,
            deadline=future_date,
            target_audience="residents",
            created_at=datetime.now(UTC),
            response_count=5
        )
        assert survey.question_text == "What do you think?"
        assert survey.points == 10
        assert survey.deadline == future_date
        assert survey.response_count == 5

    def test_survey_response_empty_title(self):
        """Test SurveyResponse with empty title"""
        with pytest.raises(ValidationError):
            SurveyResponse(
                survey_id=1,
                title="",  # Invalid: empty title
                created_at=datetime.now(UTC)
            )

    def test_survey_response_past_deadline(self):
        """Test SurveyResponse with past deadline"""
        past_date = datetime.now(UTC) - timedelta(days=1)
        with pytest.raises(ValidationError):
            SurveyResponse(
                survey_id=1,
                title="Test Survey",
                deadline=past_date,  # Invalid: past deadline
                created_at=datetime.now(UTC)
            )


class TestPostRequest:
    """Test PostRequest model"""

    def test_post_request_valid(self):
        """Test valid PostRequest creation"""
        request = PostRequest(
            content="Test post content",
            tags=["tag1", "tag2"]
        )
        assert request.content == "Test post content"
        assert request.tags == ["tag1", "tag2"]

    def test_post_request_default_tags(self):
        """Test PostRequest with default tags"""
        request = PostRequest(content="Test post content")
        assert request.tags == []

    def test_post_request_empty_content(self):
        """Test PostRequest with empty content"""
        with pytest.raises(ValidationError):
            PostRequest(content="")  # Invalid: empty content

    def test_post_request_strips_whitespace(self):
        """Test PostRequest strips whitespace from content"""
        request = PostRequest(content="  Test post content  ")
        assert request.content == "Test post content"

    def test_post_request_cleans_tags(self):
        """Test PostRequest cleans tags list"""
        request = PostRequest(
            content="Test content",
            tags=["tag1", "  tag2  ", "", "tag1", "tag3"]  # Duplicates and empty
        )
        assert request.tags == ["tag1", "tag2", "tag3"]

    def test_post_request_limits_tags(self):
        """Test PostRequest limits number of tags"""
        many_tags = [f"tag{i}" for i in range(15)]  # 15 tags
        request = PostRequest(
            content="Test content",
            tags=many_tags
        )
        assert len(request.tags) == 10  # Limited to 10


class TestUserProfileUpdateRequest:
    """Test UserProfileUpdateRequest model"""

    def test_user_profile_update_request_valid(self):
        """Test valid UserProfileUpdateRequest creation"""
        request = UserProfileUpdateRequest(
            display_name="New Display Name",
            bio="New bio",
            area="New Area"
        )
        assert request.display_name == "New Display Name"
        assert request.bio == "New bio"
        assert request.area == "New Area"

    def test_user_profile_update_request_all_none(self):
        """Test UserProfileUpdateRequest with all None values"""
        request = UserProfileUpdateRequest()
        assert request.display_name is None
        assert request.bio is None
        assert request.area is None

    def test_user_profile_update_request_empty_display_name(self):
        """Test UserProfileUpdateRequest with empty display name"""
        with pytest.raises(ValidationError):
            UserProfileUpdateRequest(display_name="")  # Invalid: empty string

    def test_user_profile_update_request_strips_whitespace(self):
        """Test UserProfileUpdateRequest strips whitespace"""
        request = UserProfileUpdateRequest(
            display_name="  Test Name  ",
            bio="  Test bio  ",
            area="  Test Area  "
        )
        assert request.display_name == "Test Name"
        assert request.bio == "Test bio"
        assert request.area == "Test Area"