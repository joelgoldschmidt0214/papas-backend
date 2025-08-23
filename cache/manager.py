# --- START OF FILE manager.py ---

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


### 変更点 ###
# 固定のカテゴリ名を定義
FIXED_CATEGORIES = ["フォロー", "ご近所さん", "イベント", "グルメ"]


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
        self.comments: Dict[int, List[CommentResponse]] = defaultdict(list)
        self.tags: Dict[str, TagResponse] = {}
        self.surveys: Dict[int, SurveyResponse] = {}

        # Relationship caches - using sets for O(1) lookups
        self.likes: Dict[int, Set[int]] = defaultdict(set)
        self.bookmarks: Dict[int, Set[int]] = defaultdict(set)
        self.follows: Dict[int, Set[int]] = defaultdict(set)
        self.followers: Dict[int, Set[int]] = defaultdict(set)

        # Tag relationships - optimized for fast lookups
        self.post_tags: Dict[int, List[str]] = defaultdict(list)
        self.tag_posts: Dict[str, List[int]] = defaultdict(list)

        # Performance optimization
        self._sorted_posts_cache: Optional[List[Tuple[int, datetime]]] = None
        self._sorted_posts_by_tag: Dict[str, List[Tuple[int, datetime]]] = {}
        self._cache_dirty = True
        self._tag_cache_dirty: Set[str] = set()
        self._pagination_cache: Dict[str, List[PostResponse]] = {}
        self._pagination_cache_max_size = 50

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

        self.performance_metrics = PerformanceMetrics()

    def initialize(self, db: Session) -> bool:
        """
        Initialize cache by loading all data from database
        Returns True if successful, False otherwise
        """
        try:
            start_time = datetime.now()
            logger.info("Starting cache initialization...")

            self._load_users(db)
            self._load_tags()  ### 変更点: DBセッションが不要に
            self._load_posts(db)
            self._load_comments(db)
            # _load_likes, _load_bookmarks は _load_posts 内でEager Loadingされるため、
            # カウント更新の必要がなければ呼び出し不要。リレーションキャッシュ構築のために残す。
            self._load_likes(db)
            self._load_bookmarks(db)
            self._load_follows(db)
            self._load_surveys(db)

            end_time = datetime.now()
            self.cache_stats.update(
                {
                    "initialized": True,
                    "initialization_time": (end_time - start_time).total_seconds(),
                    "posts_count": len(self.posts),
                    "users_count": len(self.users),
                    "comments_count": sum(len(c) for c in self.comments.values()),
                    "tags_count": len(self.tags),
                    "surveys_count": len(self.surveys),
                    "likes_count": sum(len(u) for u in self.likes.values()),
                    "bookmarks_count": sum(len(p) for p in self.bookmarks.values()),
                    "follows_count": sum(len(f) for f in self.follows.values()),
                }
            )

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

            memory_info = self._get_memory_usage()
            logger.info(f"Cache memory usage: {memory_info['total_mb']:.2f} MB")
            return True

        except Exception as e:
            logger.error(f"Cache initialization failed: {str(e)}", exc_info=True)
            self.cache_stats["initialized"] = False
            return False

    def _load_users(self, db: Session) -> None:
        logger.info("Loading users...")
        db_users = crud.select_users(db, skip=0, limit=10000)
        for db_user in db_users:
            self.users[db_user.user_id] = UserResponse.from_orm(db_user)

    ### 変更点: DBからではなく固定リストからタグ(カテゴリ)を生成 ###
    def _load_tags(self) -> None:
        """Load fixed categories as tags into cache"""
        logger.info("Loading fixed categories as tags...")
        for i, tag_name in enumerate(FIXED_CATEGORIES):
            self.tags[tag_name] = TagResponse(
                tag_id=i + 1, tag_name=tag_name, posts_count=0
            )

    ### 変更点: postsテーブルのフラグからタグ情報を構築 ###
    def _load_posts(self, db: Session) -> None:
        """Load all posts and build their category relationships from flags"""
        logger.info("Loading posts...")

        db_posts = (
            db.query(models.POSTS)
            .options(
                joinedload(models.POSTS.user),
                selectinload(models.POSTS.images),
                selectinload(models.POSTS.likes),
                selectinload(models.POSTS.comments),
                selectinload(models.POSTS.bookmarks),
            )
            .order_by(models.POSTS.created_at.desc())
            .all()
        )

        for db_post in db_posts:
            author = self.users.get(db_post.user_id)
            if not author:
                logger.warning(
                    f"Author with ID {db_post.user_id} not found for post {db_post.post_id}"
                )
                continue

            tag_names = []
            if db_post.is_follow_category:
                tag_names.append("フォロー")
            if db_post.is_neighborhood_category:
                tag_names.append("ご近所さん")
            if db_post.is_event_category:
                tag_names.append("イベント")
            if db_post.is_gourmet_category:
                tag_names.append("グルメ")

            tag_responses = [self.tags[name] for name in tag_names if name in self.tags]

            self.post_tags[db_post.post_id] = tag_names
            for tag_name in tag_names:
                self.tag_posts[tag_name].append(db_post.post_id)
                if tag_name in self.tags:
                    self.tags[tag_name].posts_count += 1

            post_response = PostResponse(
                post_id=db_post.post_id,
                user_id=db_post.user_id,
                content=db_post.content,
                created_at=db_post.created_at,
                updated_at=db_post.updated_at,
                author=author,
                images=[PostImageResponse.from_orm(img) for img in db_post.images],
                tags=tag_responses,
                likes_count=len(db_post.likes),
                comments_count=len(db_post.comments),
                is_liked=False,
                is_bookmarked=False,
            )
            self.posts[db_post.post_id] = post_response

    def _load_comments(self, db: Session) -> None:
        logger.info("Loading comments...")
        db_comments = (
            db.query(models.COMMENTS).order_by(models.COMMENTS.created_at.asc()).all()
        )
        for db_comment in db_comments:
            author = self.users.get(db_comment.user_id)
            if not author:
                logger.warning(f"Author not found for comment {db_comment.comment_id}")
                continue
            self.comments[db_comment.post_id].append(
                CommentResponse(
                    comment_id=db_comment.comment_id,
                    post_id=db_comment.post_id,
                    user_id=db_comment.user_id,
                    content=db_comment.content,
                    created_at=db_comment.created_at,
                    author=author,
                )
            )

    def _load_likes(self, db: Session) -> None:
        logger.info("Loading likes...")
        db_likes = db.query(models.LIKES).all()
        for db_like in db_likes:
            self.likes[db_like.post_id].add(db_like.user_id)

    def _load_bookmarks(self, db: Session) -> None:
        logger.info("Loading bookmarks...")
        db_bookmarks = db.query(models.BOOKMARKS).all()
        for db_bookmark in db_bookmarks:
            self.bookmarks[db_bookmark.user_id].add(db_bookmark.post_id)

    def _load_follows(self, db: Session) -> None:
        logger.info("Loading follows...")
        db_follows = db.query(models.FOLLOWS).all()
        for db_follow in db_follows:
            self.follows[db_follow.follower_id].add(db_follow.following_id)
            self.followers[db_follow.following_id].add(db_follow.follower_id)

    def _load_surveys(self, db: Session) -> None:
        logger.info("Loading surveys...")
        db_surveys = crud.select_surveys(db, skip=0, limit=10000)
        for db_survey in db_surveys:
            response_count = (
                db.query(models.SURVEY_RESPONSES)
                .filter(models.SURVEY_RESPONSES.survey_id == db_survey.survey_id)
                .count()
            )
            self.surveys[db_survey.survey_id] = SurveyResponse(
                survey_id=db_survey.survey_id,
                title=db_survey.title,
                question_text=db_survey.question_text,
                points=db_survey.points,
                deadline=db_survey.deadline,
                target_audience=db_survey.target_audience,
                created_at=db_survey.created_at,
                response_count=response_count,
            )

    # ... (以降のメソッドは、タグ関連のキャッシュ構造に依存しているため、
    #      _load_posts と _load_tags の修正が正しければ、大きな変更は不要です)
    # ... (ただし、add_post_to_cache は修正が必要です)

    ### 変更点: 新しいタグ(カテゴリ)の動的作成ロジックを削除 ###
    def add_post_to_cache(
        self, post_data: dict, author: UserResponse, tags: List[str] = None
    ) -> PostResponse:
        if not self.cache_stats["initialized"]:
            raise RuntimeError("Cache not initialized")

        new_post_id = max(self.posts.keys()) + 1 if self.posts else 1

        tag_responses = []
        tag_names = tags or []

        for tag_name in tag_names:
            # タグは固定なので、新しいタグは作成しない
            if tag_name in self.tags:
                tag_responses.append(self.tags[tag_name])
                self.tags[tag_name].posts_count += 1
                self.tag_posts[tag_name].append(new_post_id)
                self._tag_cache_dirty.add(tag_name)

        self.post_tags[new_post_id] = tag_names

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
            # images と bookmarks_count が PostResponse にあると仮定
            images=[],
            bookmarks_count=0,
        )

        self.posts[new_post_id] = post_response
        self.cache_stats["posts_count"] += 1
        self._cache_dirty = True
        return post_response

    # ... (ここから下のメソッドは、ほぼ変更なしで動作するはずです) ...
    def _rebuild_sorted_posts_cache(self) -> None:
        """Rebuild the sorted posts cache for optimal performance"""
        self._sorted_posts_cache = [
            (post_id, post.created_at) for post_id, post in self.posts.items()
        ]
        self._sorted_posts_cache.sort(key=lambda x: x[1], reverse=True)
        self._cache_dirty = False
        self._pagination_cache.clear()

    def _rebuild_sorted_posts_by_tag(self, tag_name: str) -> None:
        """Rebuild sorted posts cache for a specific tag"""
        if tag_name not in self.tag_posts:
            self._sorted_posts_by_tag[tag_name] = []
            return
        post_ids = self.tag_posts[tag_name]
        posts_with_dates = [
            (post_id, self.posts[post_id].created_at)
            for post_id in post_ids
            if post_id in self.posts
        ]
        posts_with_dates.sort(key=lambda x: x[1], reverse=True)
        self._sorted_posts_by_tag[tag_name] = posts_with_dates
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
        return {
            "total_bytes": total_bytes,
            "total_mb": total_bytes / (1024 * 1024),
            "breakdown": sizes,
        }

    def get_posts(
        self, skip: int = 0, limit: int = 100, current_user_id: Optional[int] = None
    ) -> List[PostResponse]:
        if not self.cache_stats["initialized"]:
            return []
        cache_key = f"posts_{skip}_{limit}_{current_user_id or 'none'}"
        if cache_key in self._pagination_cache and not self._cache_dirty:
            return [p.copy(deep=True) for p in self._pagination_cache[cache_key]]
        if self._cache_dirty or self._sorted_posts_cache is None:
            self._rebuild_sorted_posts_cache()
        end_index = min(skip + limit, len(self._sorted_posts_cache))
        sorted_post_ids = [
            post_id for post_id, _ in self._sorted_posts_cache[skip:end_index]
        ]
        paginated_posts = [
            self.posts[post_id].copy(deep=True)
            for post_id in sorted_post_ids
            if post_id in self.posts
        ]
        if current_user_id:
            user_bookmarks = self.bookmarks.get(current_user_id, set())
            for post in paginated_posts:
                post.is_liked = current_user_id in self.likes.get(post.post_id, set())
                post.is_bookmarked = post.post_id in user_bookmarks
        if len(self._pagination_cache) < self._pagination_cache_max_size:
            self._pagination_cache[cache_key] = paginated_posts
        return paginated_posts

    def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        if not self.is_initialized():
            return []
        sorted_user_ids = sorted(self.users.keys())
        paginated_user_ids = sorted_user_ids[skip : skip + limit]
        return [self.users[user_id] for user_id in paginated_user_ids]

    def get_post_by_id(
        self, post_id: int, current_user_id: Optional[int] = None
    ) -> Optional[PostResponse]:
        if not self.cache_stats["initialized"] or post_id not in self.posts:
            return None
        post = self.posts[post_id].copy(deep=True)
        if current_user_id:
            post.is_liked = current_user_id in self.likes.get(post_id, set())
            post.is_bookmarked = post_id in self.bookmarks.get(current_user_id, set())
        return post

    def get_posts_by_tag(
        self,
        tag_name: str,
        skip: int = 0,
        limit: int = 100,
        current_user_id: Optional[int] = None,
    ) -> List[PostResponse]:
        if not self.cache_stats["initialized"] or tag_name not in self.tag_posts:
            return []
        if (
            tag_name not in self._sorted_posts_by_tag
            or tag_name in self._tag_cache_dirty
        ):
            self._rebuild_sorted_posts_by_tag(tag_name)
        sorted_posts_for_tag = self._sorted_posts_by_tag[tag_name]
        end_index = min(skip + limit, len(sorted_posts_for_tag))
        paginated_post_ids = [
            post_id for post_id, _ in sorted_posts_for_tag[skip:end_index]
        ]
        paginated_posts = [
            self.posts[post_id].copy(deep=True)
            for post_id in paginated_post_ids
            if post_id in self.posts
        ]
        if current_user_id:
            user_bookmarks = self.bookmarks.get(current_user_id, set())
            for post in paginated_posts:
                post.is_liked = current_user_id in self.likes.get(post.post_id, set())
                post.is_bookmarked = post.post_id in user_bookmarks
        return paginated_posts

    def get_user_profile(self, user_id: int) -> Optional[UserProfileResponse]:
        if not self.cache_stats["initialized"] or user_id not in self.users:
            return None
        user = self.users[user_id]
        followers_count = len(self.followers.get(user_id, set()))
        following_count = len(self.follows.get(user_id, set()))
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
        if not self.cache_stats["initialized"]:
            return None
        return self.users.get(user_id)

    def get_comments_by_post_id(
        self, post_id: int, skip: int = 0, limit: int = 100
    ) -> List[CommentResponse]:
        if not self.cache_stats["initialized"] or post_id not in self.comments:
            return []
        return self.comments[post_id][skip : skip + limit]

    def get_user_bookmarks(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[PostResponse]:
        if not self.cache_stats["initialized"] or user_id not in self.bookmarks:
            return []
        bookmarked_post_ids = self.bookmarks[user_id]
        posts_with_dates = [
            (post_id, self.posts[post_id].created_at)
            for post_id in bookmarked_post_ids
            if post_id in self.posts
        ]
        posts_with_dates.sort(key=lambda x: x[1], reverse=True)
        end_index = min(skip + limit, len(posts_with_dates))
        paginated_post_ids = [
            post_id for post_id, _ in posts_with_dates[skip:end_index]
        ]
        paginated_posts = []
        user_likes = self.likes.get(user_id, set())
        for post_id in paginated_post_ids:
            if post_id in self.posts:
                post = self.posts[post_id].copy(deep=True)
                post.is_liked = post_id in user_likes
                post.is_bookmarked = True
                paginated_posts.append(post)
        return paginated_posts

    def get_user_followers(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        if not self.cache_stats["initialized"] or user_id not in self.followers:
            return []
        follower_ids = list(self.followers[user_id])
        return [
            self.users[uid]
            for uid in follower_ids[skip : skip + limit]
            if uid in self.users
        ]

    def get_user_following(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        if not self.cache_stats["initialized"] or user_id not in self.follows:
            return []
        following_ids = list(self.follows[user_id])
        return [
            self.users[uid]
            for uid in following_ids[skip : skip + limit]
            if uid in self.users
        ]

    def get_tags(self) -> List[TagResponse]:
        if not self.cache_stats["initialized"]:
            return []
        return list(self.tags.values())

    def get_tag_by_name(self, tag_name: str) -> Optional[TagResponse]:
        if not self.cache_stats["initialized"]:
            return None
        return self.tags.get(tag_name)

    def get_surveys(self, skip: int = 0, limit: int = 100) -> List[SurveyResponse]:
        if not self.cache_stats["initialized"]:
            return []
        return list(self.surveys.values())[skip : skip + limit]

    def get_survey_by_id(self, survey_id: int) -> Optional[SurveyResponse]:
        if not self.cache_stats["initialized"]:
            return None
        return self.surveys.get(survey_id)

    def get_cache_stats(self) -> dict:
        return self.cache_stats.copy()

    def is_initialized(self) -> bool:
        return self.cache_stats["initialized"]

    def record_request_time(self, response_time: float) -> None:
        self.performance_metrics.add_request_time(response_time)

    def get_average_response_time(self) -> float:
        return self.performance_metrics.get_average_response_time()

    def get_performance_stats(self) -> dict:
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
        return self._get_memory_usage()


cache_manager = CacheManager()
