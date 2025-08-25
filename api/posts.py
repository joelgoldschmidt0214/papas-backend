"""
Posts API endpoints with cache integration
Provides high-performance post management functionality
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query, Path
from typing import List, Optional

from models.responses import PostResponse, CommentResponse, ErrorResponse
from models.requests import PostRequest
from auth.middleware import get_current_user_optional, get_current_user_required
from models.responses import UserResponse
from cache.manager import cache_manager
from exceptions import ResourceNotFoundError, ServiceUnavailableError, ValidationError

logger = logging.getLogger(__name__)

# Create router for posts endpoints
router = APIRouter(prefix="/api/v1/posts", tags=["posts"])


# 2025/08/22追記（けいじゅ）@router.get(timeline)、async def get_timeline
@router.get(
    "/timeline",  # エンドポイントを /posts/timeline にする
    response_model=List[PostResponse],
    summary="タイムライン投稿一覧を取得",
    description="UI表示に最適化された投稿一覧を取得します。作成日時の新しい順でソートされます。",
)
async def get_timeline(
    skip: int = Query(0, ge=0, description="スキップする投稿数"),
    limit: int = Query(200, ge=1, le=10000, description="取得する最大投稿数"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """
    UI表示用のタイムラインを取得します。
    このプロジェクトでは、パフォーマンス重視のためキャッシュからデータを取得します。
    """
    try:
        if not cache_manager.is_initialized():
            raise ServiceUnavailableError(
                message="Service temporarily unavailable - cache not initialized",
                service="Cache",
            )

        # キャッシュから投稿データを取得
        # 既存の get_posts メソッドを流用できる
        current_user_id = current_user.user_id if current_user else None
        posts_from_cache = cache_manager.get_posts(
            skip=skip, limit=limit, current_user_id=current_user_id
        )

        # PostResponse モデルに合わせてデータを整形
        # Step1でモデルを修正したので、キャッシュのデータもこれに合わせて更新する必要がある
        # (詳細はStep3で)
        # 現時点では、cache_managerが修正後のPostResponseを返すと仮定する

        logger.info(
            f"Retrieved {len(posts_from_cache)} posts for timeline (skip={skip}, limit={limit})"
        )
        return posts_from_cache

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error retrieving timeline: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Failed to retrieve timeline",
            service="Timeline",
            details={"error": str(e)},
        )


@router.get(
    "",
    response_model=List[PostResponse],
    summary="投稿一覧を取得",
    description="""
    地域投稿の一覧をページネーション付きで取得します。
    
    **機能詳細:**
    - キャッシュから高速取得（200ms以内の応答目標）
    - 投稿は作成日時の新しい順でソート
    - 各投稿にはいいね数、コメント数、タグ情報を含む
    - 認証済みユーザーの場合、is_liked/is_bookmarkedフラグを設定
    
    **パフォーマンス:**
    - 95%のリクエストが200ms以内で応答
    - メモリキャッシュから直接取得
    """,
    responses={
        200: {
            "description": "投稿一覧の取得成功",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "post_id": 1,
                            "user_id": 1,
                            "content": "地域のお祭り情報です！今年も盛大に開催予定です。",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "author": {
                                "user_id": 1,
                                "username": "tanaka_taro",
                                "display_name": "田中太郎",
                                "profile_image_url": "https://example.com/avatar1.jpg",
                                "bio": "地域イベント大好きです",
                                "area": "東京都渋谷区",
                                "created_at": "2024-01-01T00:00:00Z",
                            },
                            "tags": [
                                {
                                    "tag_id": 1,
                                    "tag_name": "イベント",
                                    "posts_count": 25,
                                },
                                {"tag_id": 2, "tag_name": "お祭り", "posts_count": 12},
                            ],
                            "likes_count": 15,
                            "comments_count": 3,
                            "is_liked": False,
                            "is_bookmarked": True,
                        }
                    ]
                }
            },
        },
        503: {
            "description": "サービス利用不可（キャッシュ未初期化）",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Service temporarily unavailable - cache not initialized",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def get_posts(
    skip: int = Query(
        0,
        ge=0,
        le=10000,
        description="スキップする投稿数（ページネーション用）",
        example=0,
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="取得する最大投稿数（パフォーマンス最適化済み）",
        example=20,
    ),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """
    投稿一覧を取得（要件 2.2）
    キャッシュから投稿を作成日時の新しい順で取得
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing posts")
            raise ServiceUnavailableError(
                message="Service temporarily unavailable - cache not initialized",
                service="Cache",
            )

        current_user_id = current_user.user_id if current_user else None
        posts = cache_manager.get_posts(
            skip=skip, limit=limit, current_user_id=current_user_id
        )

        logger.info(f"Retrieved {len(posts)} posts (skip={skip}, limit={limit})")
        return posts

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error retrieving posts: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Failed to retrieve posts",
            service="Posts",
            details={"error": str(e)},
        )


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="投稿詳細を取得",
    description="""
    指定されたIDの投稿詳細を取得します。
    
    **機能詳細:**
    - キャッシュから高速取得
    - 投稿者情報、タグ、いいね数、コメント数を含む
    - 認証済みユーザーの場合、個人的な状態（いいね済み、ブックマーク済み）を表示
    """,
    responses={
        200: {
            "description": "投稿詳細の取得成功",
            "content": {
                "application/json": {
                    "example": {
                        "post_id": 1,
                        "user_id": 1,
                        "content": "地域のお祭り情報です！今年も盛大に開催予定です。",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "author": {
                            "user_id": 1,
                            "username": "tanaka_taro",
                            "display_name": "田中太郎",
                        },
                        "tags": [
                            {"tag_id": 1, "tag_name": "イベント", "posts_count": 25}
                        ],
                        "likes_count": 15,
                        "comments_count": 3,
                        "is_liked": False,
                        "is_bookmarked": True,
                    }
                }
            },
        },
        404: {
            "description": "投稿が見つからない",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "RESOURCE_NOT_FOUND",
                        "message": "Post not found",
                        "resource_type": "Post",
                        "resource_id": "999",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def get_post_by_id(
    post_id: int = Path(..., description="取得する投稿のID", example=1),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """
    投稿詳細を取得
    キャッシュから指定IDの投稿を取得
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing post")
            raise ServiceUnavailableError(
                message="Service temporarily unavailable - cache not initialized",
                service="Cache",
            )

        current_user_id = current_user.user_id if current_user else None
        post = cache_manager.get_post_by_id(post_id, current_user_id=current_user_id)

        if not post:
            logger.warning(f"Post not found: {post_id}")
            raise ResourceNotFoundError(resource_type="Post", resource_id=str(post_id))

        logger.info(f"Retrieved post: {post_id}")
        return post

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error retrieving post {post_id}: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Failed to retrieve post",
            service="Posts",
            details={"post_id": post_id, "error": str(e)},
        )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新規投稿を作成",
    description="""
    新しい投稿を作成します（MVP版：キャッシュのみ）。
    
    **機能詳細:**
    - 投稿はキャッシュに追加されますが、データベースには保存されません
    - タグの自動関連付け
    - 認証が必要
    - 投稿内容の検証
    
    **制限事項:**
    - MVP版のため、投稿はアプリケーション再起動時に失われます
    - 最大文字数制限あり
    """,
    responses={
        201: {
            "description": "投稿作成成功",
            "content": {
                "application/json": {
                    "example": {
                        "post_id": 101,
                        "user_id": 1,
                        "content": "新しい地域イベントの提案です！",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "author": {
                            "user_id": 1,
                            "username": "tanaka_taro",
                            "display_name": "田中太郎",
                        },
                        "tags": [
                            {"tag_id": 1, "tag_name": "イベント", "posts_count": 26}
                        ],
                        "likes_count": 0,
                        "comments_count": 0,
                        "is_liked": False,
                        "is_bookmarked": False,
                    }
                }
            },
        },
        401: {
            "description": "認証が必要",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "AUTHENTICATION_REQUIRED",
                        "message": "Authentication required",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        422: {
            "description": "リクエストデータの検証エラー",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "field_errors": {"content": "Content is required"},
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def create_post(
    post_request: PostRequest,
    current_user: UserResponse = Depends(get_current_user_required),
):
    """
    新規投稿を作成（キャッシュのみ、MVP版）（要件 2.4, 2.5）
    投稿はキャッシュに追加されるが、データベースには保存されない
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when creating post")
            raise ServiceUnavailableError(
                message="Service temporarily unavailable - cache not initialized",
                service="Cache",
            )

        # Validate post content
        if not post_request.content or not post_request.content.strip():
            raise ValidationError(
                message="Post content cannot be empty",
                field_errors={"content": "Content is required"},
            )

        # Create post data
        post_data = {"content": post_request.content.strip()}

        # Add post to cache
        new_post = cache_manager.add_post_to_cache(
            post_data=post_data, author=current_user, tags=post_request.tags
        )

        logger.info(
            f"Created new post: {new_post.post_id} by user {current_user.user_id}"
        )
        return new_post

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Failed to create post",
            service="Posts",
            details={"user_id": current_user.user_id, "error": str(e)},
        )


@router.get("/tags/{tag_name}", response_model=List[PostResponse])
async def get_posts_by_tag(
    tag_name: str,
    skip: int = Query(
        0, ge=0, le=10000, description="Number of posts to skip for pagination"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of posts to return (optimized for performance)",
    ),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """
    Get posts filtered by tag name with pagination (requirement 2.3, 6.4)
    Returns posts with the specified tag sorted by creation date (newest first)
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing posts by tag")
            raise ServiceUnavailableError(
                message="Service temporarily unavailable - cache not initialized",
                service="Cache",
            )

        # Validate tag name
        if not tag_name or not tag_name.strip():
            raise ValidationError(
                message="Tag name cannot be empty",
                field_errors={"tag_name": "Tag name is required"},
            )

        current_user_id = current_user.user_id if current_user else None
        posts = cache_manager.get_posts_by_tag(
            tag_name=tag_name.strip(),
            skip=skip,
            limit=limit,
            current_user_id=current_user_id,
        )

        logger.info(
            f"Retrieved {len(posts)} posts for tag '{tag_name}' (skip={skip}, limit={limit})"
        )
        return posts

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving posts by tag '{tag_name}': {str(e)}", exc_info=True
        )
        raise ServiceUnavailableError(
            message="Failed to retrieve posts by tag",
            service="Posts",
            details={"tag_name": tag_name, "error": str(e)},
        )


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def get_post_comments(
    post_id: int,
    skip: int = Query(
        0, ge=0, le=10000, description="Number of comments to skip for pagination"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of comments to return (optimized for performance)",
    ),
):
    """
    Get comments for a specific post with pagination (requirement 3.1, 3.2, 3.3)
    Returns comments sorted chronologically (oldest first)
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing comments")
            raise ServiceUnavailableError(
                message="Service temporarily unavailable - cache not initialized",
                service="Cache",
            )

        # Check if post exists
        post = cache_manager.get_post_by_id(post_id)
        if not post:
            logger.warning(f"Post not found when retrieving comments: {post_id}")
            raise ResourceNotFoundError(resource_type="Post", resource_id=str(post_id))

        comments = cache_manager.get_comments_by_post_id(
            post_id=post_id, skip=skip, limit=limit
        )

        logger.info(
            f"Retrieved {len(comments)} comments for post {post_id} (skip={skip}, limit={limit})"
        )
        return comments

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving comments for post {post_id}: {str(e)}", exc_info=True
        )
        raise ServiceUnavailableError(
            message="Failed to retrieve comments",
            service="Comments",
            details={"post_id": post_id, "error": str(e)},
        )
