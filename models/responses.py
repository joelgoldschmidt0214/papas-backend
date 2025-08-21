"""
Pydantic response models for API data validation
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from typing import List, Optional
from datetime import datetime, UTC


class ErrorResponse(BaseModel):
    """Standard error response model for consistent error handling"""
    error_code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Error timestamp")

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()

    model_config = ConfigDict()


class UserResponse(BaseModel):
    """User response model with basic user information"""
    user_id: int = Field(..., gt=0, description="Unique user identifier")
    username: str = Field(..., min_length=1, max_length=50, description="Username")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    email: str = Field(..., description="User email address")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    area: Optional[str] = Field(None, max_length=100, description="User area/location")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Basic email validation"""
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserResponse):
    """Extended user profile response with relationship counts"""
    followers_count: int = Field(default=0, ge=0, description="Number of followers")
    following_count: int = Field(default=0, ge=0, description="Number of users being followed")
    posts_count: int = Field(default=0, ge=0, description="Number of posts created")


class TagResponse(BaseModel):
    """Tag response model"""
    tag_id: int = Field(..., gt=0, description="Unique tag identifier")
    tag_name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    posts_count: int = Field(default=0, ge=0, description="Number of posts with this tag")

    @field_validator('tag_name')
    @classmethod
    def validate_tag_name(cls, v):
        """Validate tag name format"""
        if not v.strip():
            raise ValueError('Tag name cannot be empty')
        return v.strip()

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    """Comment response model"""
    comment_id: int = Field(..., gt=0, description="Unique comment identifier")
    post_id: int = Field(..., gt=0, description="Associated post identifier")
    user_id: int = Field(..., gt=0, description="Comment author user identifier")
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")
    created_at: datetime = Field(..., description="Comment creation timestamp")
    author: UserResponse = Field(..., description="Comment author information")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate comment content"""
        if not v.strip():
            raise ValueError('Comment content cannot be empty')
        return v.strip()

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    model_config = ConfigDict(from_attributes=True)


class PostResponse(BaseModel):
    """Post response model with all related information"""
    post_id: int = Field(..., gt=0, description="Unique post identifier")
    user_id: int = Field(..., gt=0, description="Post author user identifier")
    content: str = Field(..., min_length=1, max_length=2000, description="Post content")
    created_at: datetime = Field(..., description="Post creation timestamp")
    updated_at: datetime = Field(..., description="Post last update timestamp")
    author: UserResponse = Field(..., description="Post author information")
    tags: List[TagResponse] = Field(default=[], description="Associated tags")
    likes_count: int = Field(default=0, ge=0, description="Number of likes")
    comments_count: int = Field(default=0, ge=0, description="Number of comments")
    is_liked: bool = Field(default=False, description="Whether current user liked this post")
    is_bookmarked: bool = Field(default=False, description="Whether current user bookmarked this post")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate post content"""
        if not v.strip():
            raise ValueError('Post content cannot be empty')
        return v.strip()

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    model_config = ConfigDict(from_attributes=True)


class SurveyResponse(BaseModel):
    """Survey response model"""
    survey_id: int = Field(..., gt=0, description="Unique survey identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Survey title")
    question_text: Optional[str] = Field(None, max_length=1000, description="Survey question text")
    points: int = Field(default=0, ge=0, description="Points awarded for participation")
    deadline: Optional[datetime] = Field(None, description="Survey deadline")
    target_audience: str = Field(default="all", max_length=100, description="Target audience")
    created_at: datetime = Field(..., description="Survey creation timestamp")
    response_count: int = Field(default=0, ge=0, description="Number of responses received")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate survey title"""
        if not v.strip():
            raise ValueError('Survey title cannot be empty')
        return v.strip()

    @field_validator('deadline')
    @classmethod
    def validate_deadline(cls, v):
        """Validate survey deadline is in the future"""
        if v and v < datetime.now(UTC):
            raise ValueError('Survey deadline must be in the future')
        return v

    @field_serializer('created_at', 'deadline')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None

    model_config = ConfigDict(from_attributes=True)