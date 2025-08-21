"""
Likes and Bookmarks API endpoints with cache integration
Provides read-only functionality for likes and bookmarks data
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional

from models.responses import PostResponse, UserResponse, ErrorResponse
from auth.middleware import get_current_user_optional
from cache.manager import cache_manager

logger = logging.getLogger(__name__)

# Create router for likes and bookmarks endpoints
router = APIRouter(prefix="/api/v1", tags=["likes", "bookmarks"])


@router.get("/posts/{post_id}/likes", response_model=dict)
async def get_post_likes(
    post_id: int,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get like information for a specific post (requirement 4.1)
    Returns like count and whether current user has liked the post
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing post likes")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized"
            )
        
        # Check if post exists
        post = cache_manager.get_post_by_id(post_id)
        if not post:
            logger.warning(f"Post not found when retrieving likes: {post_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with ID {post_id} not found"
            )
        
        # Get like information from cache
        likes_count = len(cache_manager.likes[post_id])
        is_liked = False
        
        if current_user:
            is_liked = current_user.user_id in cache_manager.likes[post_id]
        
        result = {
            "post_id": post_id,
            "likes_count": likes_count,
            "is_liked": is_liked
        }
        
        logger.info(f"Retrieved likes for post {post_id}: {likes_count} likes, user_liked={is_liked}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving likes for post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve post likes"
        )


@router.get("/users/{user_id}/bookmarks", response_model=List[PostResponse])
async def get_user_bookmarks(
    user_id: int,
    skip: int = Query(0, ge=0, le=10000, description="Number of bookmarks to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of bookmarks to return (optimized for performance)"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get posts bookmarked by a specific user (requirement 4.2, 4.3)
    Returns bookmarked posts sorted by creation date (newest first)
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing user bookmarks")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized"
            )
        
        # Check if user exists
        user = cache_manager.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User not found when retrieving bookmarks: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Get bookmarked posts from cache
        bookmarked_posts = cache_manager.get_user_bookmarks(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        # Set user-specific flags if current user is viewing
        if current_user:
            for post in bookmarked_posts:
                post.is_liked = current_user.user_id in cache_manager.likes[post.post_id]
                post.is_bookmarked = post.post_id in cache_manager.bookmarks[current_user.user_id]
        
        logger.info(f"Retrieved {len(bookmarked_posts)} bookmarks for user {user_id} (skip={skip}, limit={limit})")
        return bookmarked_posts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving bookmarks for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user bookmarks"
        )