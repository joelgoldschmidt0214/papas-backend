"""
Pydantic request models for API data validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class PostRequest(BaseModel):
    """Post creation request model"""
    content: str = Field(..., min_length=1, max_length=2000, description="Post content")
    tags: Optional[List[str]] = Field(default=[], description="Associated tag names")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate post content"""
        if not v.strip():
            raise ValueError('Post content cannot be empty')
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags list"""
        if v is None:
            return []
        # Remove duplicates and empty tags
        cleaned_tags = []
        for tag in v:
            if isinstance(tag, str) and tag.strip():
                cleaned_tag = tag.strip()
                if cleaned_tag not in cleaned_tags and len(cleaned_tag) <= 50:
                    cleaned_tags.append(cleaned_tag)
        return cleaned_tags[:10]  # Limit to 10 tags maximum


class UserProfileUpdateRequest(BaseModel):
    """User profile update request model"""
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    area: Optional[str] = Field(None, max_length=100, description="User area/location")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v):
        """Validate display name"""
        if v is not None and not v.strip():
            raise ValueError('Display name cannot be empty')
        return v.strip() if v else None

    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v):
        """Validate bio"""
        if v is not None:
            return v.strip()
        return v

    @field_validator('area')
    @classmethod
    def validate_area(cls, v):
        """Validate area"""
        if v is not None and not v.strip():
            raise ValueError('Area cannot be empty')
        return v.strip() if v else None


class SurveyResponseRequest(BaseModel):
    """Survey response request model"""
    choice: str = Field(..., pattern="^(agree|disagree)$", description="回答選択 (agree or disagree)")
    comment: Optional[str] = Field(None, max_length=1000, description="自由記述コメント")

    @field_validator('choice')
    @classmethod
    def validate_choice(cls, v):
        """Validate choice"""
        if v not in ['agree', 'disagree']:
            raise ValueError('Choice must be either "agree" or "disagree"')
        return v

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        """Validate comment"""
        if v is not None:
            return v.strip() if v.strip() else None
        return v