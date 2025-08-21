"""
Tags API endpoints with cache integration
Provides tag management functionality for the TOMOSU backend API
"""

import logging
from fastapi import APIRouter, HTTPException, status, Query
from typing import List

from models.responses import TagResponse, ErrorResponse
from cache.manager import cache_manager

logger = logging.getLogger(__name__)

# Create router for tags endpoints
router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


@router.get("", response_model=List[TagResponse])
async def get_tags(
    skip: int = Query(
        0, ge=0, le=10000, description="Number of tags to skip for pagination"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum number of tags to return (optimized for performance)",
    ),
):
    """
    Get all available tags with post counts (requirement 6.1, 6.2)
    Returns tags sorted by tag name alphabetically
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing tags")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # Get all tags from cache
        all_tags = cache_manager.get_tags()

        # Sort tags alphabetically by tag name
        sorted_tags = sorted(all_tags, key=lambda tag: tag.tag_name.lower())

        # Apply pagination
        paginated_tags = sorted_tags[skip : skip + limit]

        logger.info(
            f"Retrieved {len(paginated_tags)} tags (skip={skip}, limit={limit}, total={len(all_tags)})"
        )
        return paginated_tags

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tags: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tags",
        )


@router.get("/{tag_name}", response_model=TagResponse)
async def get_tag_by_name(tag_name: str):
    """
    Get a specific tag by name with post count (requirement 6.2, 6.3)
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing tag")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # Get tag from cache
        tag = cache_manager.get_tag_by_name(tag_name)

        if not tag:
            logger.warning(f"Tag not found: {tag_name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag '{tag_name}' not found",
            )

        logger.info(f"Retrieved tag: {tag_name}")
        return tag

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tag '{tag_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tag",
        )
