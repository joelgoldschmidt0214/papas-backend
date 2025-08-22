"""
Cache Manager for in-memory data storage
Provides high-performance data access for the TOMOSU backend API
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from collections import defaultdict
import logging
import sys
from dataclasses import dataclass

from db_control import crud, mymodels_MySQL as models
from models.responses import (
    PostResponse,
    UserResponse,
    UserProfileResponse,
    CommentResponse,
    TagResponse,
    SurveyResponse,
    PostImageResponse,
)

from sqlalchemy.orm import selectinload, joinedload

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Lightweight performance metrics tracking"""

    total_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    requests_under_200ms: int = 0

    def add_request_time(self, response_time: float) -> None:
        """Add a request time measurement"""
        self.total_requests += 1
        self.total_response_time += response_time
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)

        if response_time < 0.2:  # 200ms
            self.requests_under_200ms += 1

    def get_average_response_time(self) -> float:
        """Get average response time in seconds"""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests

    def get_performance_percentage(self) -> float:
        """Get percentage of requests under 200ms"""
        if self.total_requests == 0:
            return 100.0
        return (self.requests_under_200ms / self.total_requests) * 100


class CacheManager:
    """
    Central cache manager for in-memory data storage
    Loads all data from database on initialization for optimal performance
    """

    def __init__(self):
        # Core data caches - optimized for memory efficiency
        self.posts: Dict[int, PostResponse] = {}
        self.users: Dict[int, UserResponse] = {}
        self.comments: Dict[int, List[CommentResponse]] = defaultdict(
            list
        )  # post_id -> comments
        self.tags: Dict[str, TagResponse] = {}
        self.surveys: Dict[int, SurveyResponse] = {}

        # Relationship caches - using sets for O(1) lookups
        self.likes: Dict[int, Set[int]] = defaultdict(set)  # post_id -> user_ids
        self.bookmarks: Dict[int, Set[int]] = defaultdict(set)  # user_id -> post_ids
        self.follows: Dict[int, Set[int]] = defaultdict(
            set
        )  # user_id -> following_user_ids
        self.followers: Dict[int, Set[int]] = defaultdict(
            set
        )  # user_id -> follower_user_ids

        # Tag relationships - optimized for fast lookups
        self.post_tags: Dict[int, List[str]] = defaultdict(list)  # post_id -> tag_names
        self.tag_posts: Dict[str, List[int]] = defaultdict(list)  # tag_name -> post_ids

        # Performance optimization: Pre-computed sorted indices for pagination
        self._sorted_posts_cache: Optional[List[Tuple[int, datetime]]] = None
        self._sorted_posts_by_tag: Dict[str, List[Tuple[int, datetime]]] = {}
        self._cache_dirty = True
        self._tag_cache_dirty: Set[str] = set()

        # Memory-efficient pagination cache for frequently accessed ranges
        self._pagination_cache: Dict[str, List[PostResponse]] = {}
        self._pagination_cache_max_size = 50  # Limit cache size

        # Cache statistics
        self.cache_stats = {
            "initialized": False,
            "initialization_time": None,
            "posts_count": 0,
            "users_count": 0,
            "comments_count": 0,
            "tags_count": 0,
            "surveys_count": 0,
            "likes_count": 0,
            "bookmarks_count": 0,
            "follows_count": 0,
        }

        # Performance tracking with optimized metrics
        self.performance_metrics = PerformanceMetrics()

    def initialize(self, db: Session) -> bool:
        """
        Initialize cache by loading all data from database
        Returns True if successful, False otherwise
        """
        # try:
        start_time = datetime.now()
        logger.info("Starting cache initialization...")

        # Load all data in order of dependencies
        self._load_users(db)
        self._load_tags(db)
        self._load_posts(db)
        self._load_comments(db)
        self._load_likes(db)
        self._load_bookmarks(db)
        self._load_follows(db)
        self._load_surveys(db)

        # Update cache statistics
        end_time = datetime.now()
        self.cache_stats.update(
            {
                "initialized": True,
                "initialization_time": (end_time - start_time).total_seconds(),
                "posts_count": len(self.posts),
                "users_count": len(self.users),
                "comments_count": sum(
                    len(comments) for comments in self.comments.values()
                ),
                "tags_count": len(self.tags),
                "surveys_count": len(self.surveys),
                "likes_count": sum(len(user_ids) for user_ids in self.likes.values()),
                "bookmarks_count": sum(
                    len(post_ids) for post_ids in self.bookmarks.values()
                ),
                "follows_count": sum(
                    len(following_ids) for following_ids in self.follows.values()
                ),
            }
        )

        # Pre-compute sorted post list for performance
        self._rebuild_sorted_posts_cache()

        logger.info(
            f"Cache initialization completed in {self.cache_stats['initialization_time']:.2f} seconds"
        )
        logger.info(
            f"Loaded: {self.cache_stats['posts_count']} posts, "
            f"{self.cache_stats['users_count']} users, "
            f"{self.cache_stats['comments_count']} comments, "
            f"{self.cache_stats['tags_count']} tags, "
            f"{self.cache_stats['surveys_count']} surveys"
        )

        # Log memory usage for monitoring
        memory_info = self._get_memory_usage()
        logger.info(f"Cache memory usage: {memory_info['total_mb']:.2f} MB")

        return True

        # except Exception as e:
        #     logger.error(f"Cache initialization failed: {str(e)}")
        #     self.cache_stats["initialized"] = False
        #     return False

    def _load_users(self, db: Session) -> None:
        """Load all users into cache"""
        logger.info("Loading users...")
        db_users = crud.select_users(db, skip=0, limit=10000)  # Load all users

        for db_user in db_users:
            user_response = UserResponse(
                user_id=db_user.user_id,
                username=db_user.username,
                display_name=db_user.display_name,
                email=db_user.email,
                profile_image_url=db_user.profile_image_url,
                bio=db_user.bio,
                area=db_user.area,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
            )
            self.users[db_user.user_id] = user_response

    def _load_tags(self, db: Session) -> None:
        """Load all tags into cache"""
        logger.info("Loading tags...")
        db_tags = db.query(models.TAGS).all()

        for db_tag in db_tags:
            # Count posts for this tag
            posts_count = (
                db.query(models.POST_TAGS)
                .filter(models.POST_TAGS.tag_id == db_tag.tag_id)
                .count()
            )

            tag_response = TagResponse(
                tag_id=db_tag.tag_id, tag_name=db_tag.tag_name, posts_count=posts_count
            )
            self.tags[db_tag.tag_name] = tag_response

    def _load_posts(self, db: Session) -> None:
        """Load all posts with their tags into cache"""
        logger.info("Loading posts...")

        # db_posts = crud.select_posts(db, skip=0, limit=10000)  # Load all posts
        db_posts = (
            db.query(models.POSTS)
            .options(
                # to-one（ユーザー情報）は joinedload
                joinedload(models.POSTS.user),
                # to-many（画像、タグ、いいね、コメント、ブックマーク）は selectinload
                selectinload(models.POSTS.images),
                selectinload(models.POSTS.post_tags).joinedload(models.POST_TAGS.tag),
                selectinload(models.POSTS.likes),
                selectinload(models.POSTS.comments),
                selectinload(models.POSTS.bookmarks),
            )
            .order_by(models.POSTS.created_at.desc())
            .all()
        )

        # for db_post in db_posts:
        #     # Get author information
        #     author = self.users.get(db_post.user_id)
        #     if not author:
        #         logger.warning(f"Author not found for post {db_post.post_id}")
        #         continue

        #     # Get tags for this post
        #     post_tags = (
        #         db.query(models.POST_TAGS, models.TAGS)
        #         .join(models.TAGS, models.POST_TAGS.tag_id == models.TAGS.tag_id)
        #         .filter(models.POST_TAGS.post_id == db_post.post_id)
        #         .all()
        #     )

        #     tag_responses = []
        #     tag_names = []
        #     for post_tag, tag in post_tags:
        #         if tag.tag_name in self.tags:
        #             tag_responses.append(self.tags[tag.tag_name])
        #             tag_names.append(tag.tag_name)

        #     # Store tag relationships
        #     self.post_tags[db_post.post_id] = tag_names
        #     for tag_name in tag_names:
        #         self.tag_posts[tag_name].append(db_post.post_id)

        #     # Create post response (likes and comments counts will be updated later)
        #     post_response = PostResponse(
        #         post_id=db_post.post_id,
        #         user_id=db_post.user_id,
        #         content=db_post.content,
        #         created_at=db_post.created_at,
        #         updated_at=db_post.updated_at,
        #         author=author,
        #         tags=tag_responses,
        #         likes_count=0,  # Will be updated in _load_likes
        #         comments_count=0,  # Will be updated in _load_comments
        #         is_liked=False,  # Will be set per user request
        #         is_bookmarked=False,  # Will be set per user request
        #     )
        #     self.posts[db_post.post_id] = post_response

        for db_post in db_posts:
            # 2. 取得したデータを使ってPostResponseオブジェクトを構築します
            #    (ループ内での追加DBクエリは不要になります)

            # 既に user 情報は db_post に含まれている
            author = self.users.get(db_post.user_id)
            if not author:
                logger.warning(
                    f"Author with ID {db_post.user_id} not found in pre-loaded users for post {db_post.post_id}"
                )
                continue

            # タグ情報も db_post に含まれている
            tag_responses = [
                self.tags[pt.tag.tag_name]
                for pt in db_post.post_tags
                if pt.tag.tag_name in self.tags
            ]
            tag_names = [pt.tag.tag_name for pt in db_post.post_tags]

            # タグの関連付けをキャッシュに保存
            self.post_tags[db_post.post_id] = tag_names
            for tag_name in tag_names:
                # setdefaultでキーが存在しない場合のみ初期化
                self.tag_posts.setdefault(tag_name, []).append(db_post.post_id)

            # 3. 拡張したPostResponseモデルに合わせてオブジェクトを作成します
            post_response = PostResponse(
                post_id=db_post.post_id,
                user_id=db_post.user_id,
                content=db_post.content,
                created_at=db_post.created_at,
                updated_at=db_post.updated_at,
                author=author,
                # ↓↓↓ ここが今回の修正の核心部分 ↓↓↓
                images=[PostImageResponse.from_orm(img) for img in db_post.images],
                tags=tag_responses,
                likes_count=len(db_post.likes),
                comments_count=len(db_post.comments),
                bookmarks_count=len(db_post.bookmarks),
                # is_liked と is_bookmarked はリクエストごとに動的に設定されるため、
                # キャッシュのマスターデータとしては False のままでOK
                is_liked=False,
                is_bookmarked=False,
            )
            self.posts[db_post.post_id] = post_response

    def _load_comments(self, db: Session) -> None:
        """Load all comments into cache"""
        logger.info("Loading comments...")
        db_comments = (
            db.query(models.COMMENTS).order_by(models.COMMENTS.created_at.asc()).all()
        )

        for db_comment in db_comments:
            # Get author information
            author = self.users.get(db_comment.user_id)
            if not author:
                logger.warning(f"Author not found for comment {db_comment.comment_id}")
                continue

            comment_response = CommentResponse(
                comment_id=db_comment.comment_id,
                post_id=db_comment.post_id,
                user_id=db_comment.user_id,
                content=db_comment.content,
                created_at=db_comment.created_at,
                author=author,
            )

            self.comments[db_comment.post_id].append(comment_response)

        # Update comments count in posts
        for post_id, comments in self.comments.items():
            if post_id in self.posts:
                self.posts[post_id].comments_count = len(comments)

    def _load_likes(self, db: Session) -> None:
        """Load all likes into cache"""
        logger.info("Loading likes...")
        db_likes = db.query(models.LIKES).all()

        for db_like in db_likes:
            self.likes[db_like.post_id].add(db_like.user_id)

        # Update likes count in posts
        for post_id, user_ids in self.likes.items():
            if post_id in self.posts:
                self.posts[post_id].likes_count = len(user_ids)

    def _load_bookmarks(self, db: Session) -> None:
        """Load all bookmarks into cache"""
        logger.info("Loading bookmarks...")
        db_bookmarks = db.query(models.BOOKMARKS).all()

        for db_bookmark in db_bookmarks:
            self.bookmarks[db_bookmark.user_id].add(db_bookmark.post_id)

    def _load_follows(self, db: Session) -> None:
        """Load all follow relationships into cache"""
        logger.info("Loading follows...")
        db_follows = db.query(models.FOLLOWS).all()

        for db_follow in db_follows:
            self.follows[db_follow.follower_id].add(db_follow.following_id)
            self.followers[db_follow.following_id].add(db_follow.follower_id)

    def _load_surveys(self, db: Session) -> None:
        """Load all surveys into cache"""
        logger.info("Loading surveys...")
        db_surveys = crud.select_surveys(db, skip=0, limit=10000)  # Load all surveys

        for db_survey in db_surveys:
            # Count responses for this survey
            response_count = (
                db.query(models.SURVEY_RESPONSES)
                .filter(models.SURVEY_RESPONSES.survey_id == db_survey.survey_id)
                .count()
            )

            survey_response = SurveyResponse(
                survey_id=db_survey.survey_id,
                title=db_survey.title,
                question_text=db_survey.question_text,
                points=db_survey.points,
                deadline=db_survey.deadline,
                target_audience=db_survey.target_audience,
                created_at=db_survey.created_at,
                response_count=response_count,
            )
            self.surveys[db_survey.survey_id] = survey_response

    def _rebuild_sorted_posts_cache(self) -> None:
        """Rebuild the sorted posts cache for optimal performance"""
        self._sorted_posts_cache = [
            (post_id, post.created_at) for post_id, post in self.posts.items()
        ]
        # Sort by creation date descending (newest first)
        self._sorted_posts_cache.sort(key=lambda x: x[1], reverse=True)
        self._cache_dirty = False

        # Clear pagination cache when posts change
        self._pagination_cache.clear()

    def _rebuild_sorted_posts_by_tag(self, tag_name: str) -> None:
        """Rebuild sorted posts cache for a specific tag"""
        if tag_name not in self.tag_posts:
            self._sorted_posts_by_tag[tag_name] = []
            return

        post_ids = self.tag_posts[tag_name]

        # Create sorted list for this tag
        posts_with_dates = [
            (post_id, self.posts[post_id].created_at)
            for post_id in post_ids
            if post_id in self.posts
        ]

        # Sort by creation date (newest first)
        posts_with_dates.sort(key=lambda x: x[1], reverse=True)

        self._sorted_posts_by_tag[tag_name] = posts_with_dates

        # Remove from dirty set
        self._tag_cache_dirty.discard(tag_name)

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get approximate memory usage of cache data structures"""

        def get_size(obj):
            return sys.getsizeof(obj)

        sizes = {
            "posts": get_size(self.posts),
            "users": get_size(self.users),
            "comments": get_size(self.comments),
            "tags": get_size(self.tags),
            "surveys": get_size(self.surveys),
            "likes": get_size(self.likes),
            "bookmarks": get_size(self.bookmarks),
            "follows": get_size(self.follows),
            "followers": get_size(self.followers),
            "post_tags": get_size(self.post_tags),
            "tag_posts": get_size(self.tag_posts),
        }

        total_bytes = sum(sizes.values())
        total_mb = total_bytes / (1024 * 1024)

        return {"total_bytes": total_bytes, "total_mb": total_mb, "breakdown": sizes}

    # Data retrieval methods

    def get_posts(
        self, skip: int = 0, limit: int = 100, current_user_id: Optional[int] = None
    ) -> List[PostResponse]:
        """
        Get posts with pagination, sorted by creation date (newest first)
        Optimized with pre-sorted cache and pagination caching for better performance
        """
        if not self.cache_stats["initialized"]:
            return []

        # Create cache key for pagination
        cache_key = f"posts_{skip}_{limit}_{current_user_id or 'none'}"

        # Check pagination cache first for frequently accessed ranges
        if cache_key in self._pagination_cache and not self._cache_dirty:
            return self._pagination_cache[cache_key].copy()

        # Rebuild sorted cache if dirty (after new posts added)
        if self._cache_dirty or self._sorted_posts_cache is None:
            self._rebuild_sorted_posts_cache()

        # Use pre-sorted cache for optimal performance
        end_index = min(skip + limit, len(self._sorted_posts_cache))
        sorted_post_ids = [
            post_id for post_id, _ in self._sorted_posts_cache[skip:end_index]
        ]

        # Get post objects efficiently with batch lookup
        paginated_posts = []
        for post_id in sorted_post_ids:
            if post_id in self.posts:
                post = (
                    self.posts[post_id].copy()
                    if hasattr(self.posts[post_id], "copy")
                    else self.posts[post_id]
                )
                paginated_posts.append(post)

        # Set user-specific flags if current_user_id is provided
        if current_user_id:
            # Pre-fetch user's likes and bookmarks for efficiency
            user_likes = self.likes.get(current_user_id, set())
            user_bookmarks = self.bookmarks.get(current_user_id, set())

            for post in paginated_posts:
                post.is_liked = post.post_id in user_likes
                post.is_bookmarked = post.post_id in user_bookmarks

        # Cache result for frequently accessed ranges (limit cache size)
        if len(self._pagination_cache) < self._pagination_cache_max_size:
            self._pagination_cache[cache_key] = [
                post.copy() if hasattr(post, "copy") else post
                for post in paginated_posts
            ]

        return paginated_posts

    def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        Get users with pagination, sorted by user_id.
        (This method was missing for startup tests)
        """
        if not self.cache_stats["initialized"]:
            return []

        # ユーザーIDでソートされたリストを取得
        sorted_user_ids = sorted(self.users.keys())

        # ページネーションを適用
        paginated_user_ids = sorted_user_ids[skip : skip + limit]

        # ユーザーオブジェクトのリストを返す
        return [self.users[user_id] for user_id in paginated_user_ids]

    def get_post_by_id(
        self, post_id: int, current_user_id: Optional[int] = None
    ) -> Optional[PostResponse]:
        """
        Get a single post by ID
        """
        if not self.cache_stats["initialized"] or post_id not in self.posts:
            return None

        post = self.posts[post_id]

        # Set user-specific flags if current_user_id is provided
        if current_user_id:
            post.is_liked = current_user_id in self.likes[post_id]
            post.is_bookmarked = post_id in self.bookmarks[current_user_id]

        return post

    def get_posts_by_tag(
        self,
        tag_name: str,
        skip: int = 0,
        limit: int = 100,
        current_user_id: Optional[int] = None,
    ) -> List[PostResponse]:
        """
        Get posts filtered by tag name with pagination
        Optimized with pre-sorted tag caches for better performance
        """
        if not self.cache_stats["initialized"] or tag_name not in self.tag_posts:
            return []

        # Check if we need to rebuild sorted cache for this tag
        if (
            tag_name not in self._sorted_posts_by_tag
            or tag_name in self._tag_cache_dirty
        ):
            self._rebuild_sorted_posts_by_tag(tag_name)

        # Use pre-sorted cache for this tag
        sorted_posts_for_tag = self._sorted_posts_by_tag[tag_name]

        # Apply pagination efficiently
        end_index = min(skip + limit, len(sorted_posts_for_tag))
        paginated_post_ids = [
            post_id for post_id, _ in sorted_posts_for_tag[skip:end_index]
        ]

        # Get post objects with batch lookup
        paginated_posts = []
        for post_id in paginated_post_ids:
            if post_id in self.posts:
                post = (
                    self.posts[post_id].copy()
                    if hasattr(self.posts[post_id], "copy")
                    else self.posts[post_id]
                )
                paginated_posts.append(post)

        # Set user-specific flags if current_user_id is provided
        if current_user_id:
            # Pre-fetch user's likes and bookmarks for efficiency
            user_likes = self.likes.get(current_user_id, set())
            user_bookmarks = self.bookmarks.get(current_user_id, set())

            for post in paginated_posts:
                post.is_liked = post.post_id in user_likes
                post.is_bookmarked = post.post_id in user_bookmarks

        return paginated_posts

    def get_user_profile(self, user_id: int) -> Optional[UserProfileResponse]:
        """
        Get user profile with relationship counts
        """
        if not self.cache_stats["initialized"] or user_id not in self.users:
            return None

        user = self.users[user_id]

        # Count relationships
        followers_count = len(self.followers[user_id])
        following_count = len(self.follows[user_id])
        posts_count = sum(1 for post in self.posts.values() if post.user_id == user_id)

        return UserProfileResponse(
            user_id=user.user_id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            profile_image_url=user.profile_image_url,
            bio=user.bio,
            area=user.area,
            created_at=user.created_at,
            updated_at=user.updated_at,
            followers_count=followers_count,
            following_count=following_count,
            posts_count=posts_count,
        )

    def get_user_by_id(self, user_id: int) -> Optional[UserResponse]:
        """
        Get basic user information by ID
        """
        if not self.cache_stats["initialized"]:
            return None
        return self.users.get(user_id)

    def get_comments_by_post_id(
        self, post_id: int, skip: int = 0, limit: int = 100
    ) -> List[CommentResponse]:
        """
        Get comments for a specific post with pagination
        Comments are sorted chronologically (oldest first)
        """
        if not self.cache_stats["initialized"] or post_id not in self.comments:
            return []

        comments = self.comments[post_id]
        return comments[skip : skip + limit]

    def get_user_bookmarks(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[PostResponse]:
        """
        Get posts bookmarked by a specific user with optimized pagination
        """
        if not self.cache_stats["initialized"] or user_id not in self.bookmarks:
            return []

        bookmarked_post_ids = self.bookmarks[user_id]

        # Create sorted list of (post_id, created_at) for efficient pagination
        posts_with_dates = [
            (post_id, self.posts[post_id].created_at)
            for post_id in bookmarked_post_ids
            if post_id in self.posts
        ]

        # Sort by creation date (newest first)
        posts_with_dates.sort(key=lambda x: x[1], reverse=True)

        # Apply pagination efficiently
        end_index = min(skip + limit, len(posts_with_dates))
        paginated_post_ids = [
            post_id for post_id, _ in posts_with_dates[skip:end_index]
        ]

        # Get post objects
        paginated_posts = []
        user_likes = self.likes.get(user_id, set())  # Pre-fetch user likes

        for post_id in paginated_post_ids:
            if post_id in self.posts:
                post = (
                    self.posts[post_id].copy()
                    if hasattr(self.posts[post_id], "copy")
                    else self.posts[post_id]
                )
                post.is_liked = post_id in user_likes
                post.is_bookmarked = (
                    True  # All posts in this list are bookmarked by the user
                )
                paginated_posts.append(post)

        return paginated_posts

    def get_user_followers(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Get users who follow the specified user
        """
        if not self.cache_stats["initialized"] or user_id not in self.followers:
            return []

        follower_ids = list(self.followers[user_id])
        followers = [
            self.users[user_id] for user_id in follower_ids if user_id in self.users
        ]

        return followers[skip : skip + limit]

    def get_user_following(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Get users that the specified user is following
        """
        if not self.cache_stats["initialized"] or user_id not in self.follows:
            return []

        following_ids = list(self.follows[user_id])
        following = [
            self.users[user_id] for user_id in following_ids if user_id in self.users
        ]

        return following[skip : skip + limit]

    def get_tags(self) -> List[TagResponse]:
        """
        Get all available tags
        """
        if not self.cache_stats["initialized"]:
            return []

        return list(self.tags.values())

    def get_tag_by_name(self, tag_name: str) -> Optional[TagResponse]:
        """
        Get a specific tag by name
        """
        if not self.cache_stats["initialized"]:
            return None
        return self.tags.get(tag_name)

    def get_surveys(self, skip: int = 0, limit: int = 100) -> List[SurveyResponse]:
        """
        Get surveys with pagination
        """
        if not self.cache_stats["initialized"]:
            return []

        surveys = list(self.surveys.values())
        return surveys[skip : skip + limit]

    def get_survey_by_id(self, survey_id: int) -> Optional[SurveyResponse]:
        """
        Get a single survey by ID
        """
        if not self.cache_stats["initialized"]:
            return None
        return self.surveys.get(survey_id)

    def add_post_to_cache(
        self, post_data: dict, author: UserResponse, tags: List[str] = None
    ) -> PostResponse:
        """
        Add a new post to cache (MVP feature - cache-only, not persisted to database)
        Optimized to handle cache invalidation efficiently
        """
        if not self.cache_stats["initialized"]:
            raise RuntimeError("Cache not initialized")

        # Generate a new post ID (use max existing ID + 1)
        new_post_id = max(self.posts.keys()) + 1 if self.posts else 1

        # Process tags
        tag_responses = []
        tag_names = tags or []

        for tag_name in tag_names:
            if tag_name in self.tags:
                tag_responses.append(self.tags[tag_name])
                # Update post count for existing tag
                self.tags[tag_name].posts_count += 1
            else:
                # Create new tag in cache
                new_tag_id = (
                    max([tag.tag_id for tag in self.tags.values()]) + 1
                    if self.tags
                    else 1
                )
                new_tag = TagResponse(
                    tag_id=new_tag_id, tag_name=tag_name, posts_count=1
                )
                self.tags[tag_name] = new_tag
                tag_responses.append(new_tag)

            # Update tag relationships
            self.tag_posts[tag_name].append(new_post_id)
            # Mark tag cache as dirty for efficient rebuilding
            self._tag_cache_dirty.add(tag_name)

        self.post_tags[new_post_id] = tag_names

        # Create post response
        now = datetime.now()
        post_response = PostResponse(
            post_id=new_post_id,
            user_id=author.user_id,
            content=post_data["content"],
            created_at=now,
            updated_at=now,
            author=author,
            tags=tag_responses,
            likes_count=0,
            comments_count=0,
            is_liked=False,
            is_bookmarked=False,
        )

        # Add to cache
        self.posts[new_post_id] = post_response
        self.cache_stats["posts_count"] += 1

        # Mark main cache as dirty to trigger resort on next query
        self._cache_dirty = True

        return post_response

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics and status information
        """
        return self.cache_stats.copy()

    def is_initialized(self) -> bool:
        """
        Check if cache is properly initialized
        """
        return self.cache_stats["initialized"]

    def record_request_time(self, response_time: float) -> None:
        """
        Record a request response time for metrics
        """
        self.performance_metrics.add_request_time(response_time)

    def get_average_response_time(self) -> float:
        """
        Get average response time in seconds
        """
        return self.performance_metrics.get_average_response_time()

    def get_performance_stats(self) -> dict:
        """
        Get comprehensive performance statistics
        """
        metrics = self.performance_metrics
        return {
            "total_requests": metrics.total_requests,
            "average_response_time_ms": round(
                metrics.get_average_response_time() * 1000, 2
            ),
            "min_response_time_ms": round(metrics.min_response_time * 1000, 2)
            if metrics.min_response_time != float("inf")
            else 0,
            "max_response_time_ms": round(metrics.max_response_time * 1000, 2),
            "total_response_time": round(metrics.total_response_time, 4),
            "requests_under_200ms": metrics.requests_under_200ms,
            "performance_percentage": round(metrics.get_performance_percentage(), 2),
        }

    def get_memory_stats(self) -> dict:
        """
        Get memory usage statistics
        """
        return self._get_memory_usage()


# Global cache manager instance
cache_manager = CacheManager()
