"""
Users API endpoints with cache integration
Provides user profile and follow relationship functionality
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional

from models.responses import UserResponse, UserProfileResponse, ErrorResponse
from auth.middleware import get_current_user_optional
from cache.manager import cache_manager

logger = logging.getLogger(__name__)

# Create router for users endpoints
router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get user profile with relationship counts (requirement 5.1)
    Returns user profile information including followers/following counts
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing user profile")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized"
            )
        
        user_profile = cache_manager.get_user_profile(user_id)
        
        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        logger.info(f"Retrieved user profile: {user_id}")
        return user_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user profile {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.get("/{user_id}/followers", response_model=List[UserResponse])
async def get_user_followers(
    user_id: int,
    skip: int = Query(0, ge=0, le=10000, description="Number of followers to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of followers to return (optimized for performance)"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get users who follow the specified user (requirement 5.2)
    Returns list of users who are following the specified user
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing user followers")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized"
            )
        
        # Check if user exists
        user = cache_manager.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User not found when retrieving followers: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        followers = cache_manager.get_user_followers(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(followers)} followers for user {user_id} (skip={skip}, limit={limit})")
        return followers
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving followers for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user followers"
        )


@router.get("/{user_id}/following", response_model=List[UserResponse])
async def get_user_following(
    user_id: int,
    skip: int = Query(0, ge=0, le=10000, description="Number of following to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of following to return (optimized for performance)"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get users that the specified user is following (requirement 5.3)
    Returns list of users that the specified user is following
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing user following")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized"
            )
        
        # Check if user exists
        user = cache_manager.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User not found when retrieving following: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        following = cache_manager.get_user_following(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(following)} following for user {user_id} (skip={skip}, limit={limit})")
        return following
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving following for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user following"
        )