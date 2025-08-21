from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, UTC
import logging
import time

from config import get_settings
from logging_config import get_logger
from database import get_db_session, get_db_health, get_db_stats
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
from auth.routes import router as auth_router
from auth.middleware import validate_session_middleware
from api.posts import router as posts_router
from api.likes_bookmarks import router as likes_bookmarks_router
from api.users import router as users_router
from api.tags import router as tags_router
from api.surveys import router as surveys_router
from cache.manager import cache_manager
from error_handlers import register_exception_handlers
from exceptions import ServiceUnavailableError

# Get application settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Create FastAPI application with comprehensive documentation
app = FastAPI(
    title=settings.app_name,
    description="""
    ## 地域SNSアプリ TOMOSU のバックエンドAPI (MVP版)

    TOMOSU（地域SNSアプリ）のMVPバックエンドAPIシステム。地域住民の情報交換体験を検証するための最小限の機能を提供し、
    Azure Container Apps環境でのパフォーマンス最適化を重視した設計。

    ### 主な機能
    - **高速キャッシュベース**: 全データをメモリキャッシュで管理し、95%のリクエストを200ms以内で応答
    - **簡略化認証**: MVP用の固定ユーザー認証システム
    - **投稿管理**: 地域投稿の閲覧・作成・タグ検索
    - **ユーザー関係**: プロフィール・フォロー関係の表示
    - **アンケート機能**: 地域アンケートの閲覧・回答結果表示

    ### パフォーマンス目標
    - 95%のリクエストが200ms以内で応答
    - システム起動時5秒以内でキャッシュ初期化完了
    - 100並行ユーザーをサポート

    ### エラーコード
    - **401**: 認証が必要
    - **403**: アクセス権限なし
    - **404**: リソースが見つからない
    - **422**: リクエストデータの検証エラー
    - **503**: サービス利用不可（キャッシュ未初期化等）

    ### 認証について
    MVP版では簡略化された認証を使用。セッションクッキーによる認証で、
    `/api/v1/auth/login` でログイン後、保護されたエンドポイントにアクセス可能。
    """,
    version=settings.app_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    contact={
        "name": "TOMOSU Development Team",
        "email": "dev@tomosu.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"http://localhost:{settings.port}",
            "description": "Development server",
        },
        {
            "url": "https://tomosu-api.azurewebsites.net",
            "description": "Production server",
        },
    ],
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check endpoints for monitoring service status",
        },
        {"name": "system", "description": "System monitoring and metrics endpoints"},
        {
            "name": "auth",
            "description": "Authentication endpoints for user session management",
        },
        {
            "name": "posts",
            "description": "Post management endpoints for creating and retrieving posts",
        },
        {
            "name": "users",
            "description": "User profile and relationship management endpoints",
        },
        {
            "name": "tags",
            "description": "Tag management endpoints for categorizing posts",
        },
        {
            "name": "surveys",
            "description": "Survey management endpoints for community polls",
        },
        {
            "name": "likes_bookmarks",
            "description": "Like and bookmark management endpoints",
        },
    ],
)

# Response compression middleware (optimized for large payloads)
app.add_middleware(GZipMiddleware, minimum_size=settings.response_compression_threshold)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Request logging and performance tracking middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request with client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    logger.info(
        f"Request: {request.method} {request.url} - IP: {client_ip} - User-Agent: {user_agent[:50]}..."
    )

    response = await call_next(request)

    # Calculate response time
    process_time = time.time() - start_time

    # Record performance metrics in cache manager
    if cache_manager.is_initialized():
        cache_manager.record_request_time(process_time)

    # Log response with status and timing
    logger.info(
        f"Response: {response.status_code} - {process_time:.4f}s - {request.method} {request.url}"
    )

    # Add response time header for monitoring
    response.headers["X-Response-Time"] = f"{process_time:.4f}s"

    return response


# Session validation middleware
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    return await validate_session_middleware(request, call_next)


# Database session dependency is now imported from database module

# Pydantic models are now imported from the models package

# --- Register Exception Handlers ---
register_exception_handlers(app)

# --- Include API Routes ---
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(likes_bookmarks_router)
app.include_router(users_router)
app.include_router(tags_router)
app.include_router(surveys_router)

# --- Startup Event ---

# Startup event is now handled by startup.py script


# --- Health Check and System Monitoring Endpoints ---


@app.get(
    "/",
    tags=["health"],
    summary="基本ヘルスチェック",
    description="""
    APIサービスの基本的な健全性をチェックします。
    
    **用途:**
    - サービスが起動しているかの確認
    - キャッシュの初期化状態の確認
    - 基本的な動作確認
    
    **レスポンス時間:** 通常50ms以内
    """,
    responses={
        200: {
            "description": "サービス正常",
            "content": {
                "application/json": {
                    "example": {
                        "message": "TOMOSU Backend API is running",
                        "version": "1.0.0",
                        "status": "healthy",
                        "cache_status": "initialized",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        503: {
            "description": "サービス利用不可",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Service not ready - cache not initialized",
                        "service": "Cache",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def root():
    """ルートエンドポイント - 基本ヘルスチェック"""
    try:
        cache_status = (
            "initialized" if cache_manager.is_initialized() else "not_initialized"
        )

        # If cache is not initialized, this is a service issue
        if not cache_manager.is_initialized():
            raise ServiceUnavailableError(
                message="Service not ready - cache not initialized",
                service="Cache",
                details={"cache_status": cache_status},
            )

        return {
            "message": "TOMOSU Backend API is running",
            "version": "1.0.0",
            "status": "healthy",
            "cache_status": cache_status,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ServiceUnavailableError:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Health check failed", details={"error": str(e)}
        )


@app.get(
    "/api/v1/system/health",
    tags=["system"],
    summary="詳細ヘルスチェック",
    description="""
    システムの詳細な健全性をチェックします。
    
    **監視項目:**
    - キャッシュの初期化状態
    - データベース接続状態
    - 各コンポーネントの状態
    
    **用途:**
    - 監視システムでの定期チェック
    - ロードバランサーのヘルスチェック
    - デプロイ後の動作確認
    """,
    responses={
        200: {
            "description": "システム正常",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "version": "1.0.0",
                        "components": {
                            "cache": {"status": "healthy", "initialized": True},
                            "database": {"status": "healthy", "error": None},
                        },
                    }
                }
            },
        },
        503: {
            "description": "システム異常",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "version": "1.0.0",
                        "components": {
                            "cache": {"status": "unhealthy", "initialized": False},
                            "database": {
                                "status": "unhealthy",
                                "error": "Connection timeout",
                            },
                        },
                    }
                }
            },
        },
    },
)
async def detailed_health_check():
    """詳細ヘルスチェックエンドポイント（監視用）"""
    try:
        cache_initialized = cache_manager.is_initialized()

        # Test database connection
        db_health = get_db_health()
        db_healthy = db_health["status"] == "healthy"
        db_error = db_health.get("error")

        # Overall health status
        overall_status = "healthy" if cache_initialized and db_healthy else "unhealthy"

        health_data = {
            "status": overall_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0",
            "components": {
                "cache": {
                    "status": "healthy" if cache_initialized else "unhealthy",
                    "initialized": cache_initialized,
                },
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "error": db_error,
                },
            },
        }

        # Return appropriate status code
        status_code = 200 if overall_status == "healthy" else 503

        return JSONResponse(status_code=status_code, content=health_data)

    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Health check system failure", details={"error": str(e)}
        )


@app.get(
    "/api/v1/system/metrics",
    tags=["system"],
    summary="システムメトリクス取得",
    description="""
    システムのパフォーマンスメトリクスと統計情報を取得します。
    
    **提供情報:**
    - キャッシュ統計（データ件数、メモリ使用量）
    - パフォーマンス統計（応答時間、成功率）
    - システム稼働時間
    
    **用途:**
    - パフォーマンス監視
    - キャパシティプランニング
    - SLA監視（95%のリクエストが200ms以内）
    """,
    responses={
        200: {
            "description": "メトリクス取得成功",
            "content": {
                "application/json": {
                    "example": {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "cache": {
                            "status": "initialized",
                            "initialization_time_seconds": 2.5,
                            "data_counts": {
                                "posts": 100,
                                "users": 50,
                                "comments": 200,
                                "tags": 20,
                                "surveys": 5,
                                "likes": 500,
                                "bookmarks": 150,
                                "follows": 300,
                            },
                            "memory_usage": {
                                "total_mb": 128.5,
                                "total_bytes": 134742016,
                            },
                        },
                        "performance": {
                            "total_requests": 1000,
                            "average_response_time_ms": 150.5,
                            "requests_under_200ms": 950,
                            "performance_target_percentage": 95.0,
                            "meets_200ms_target": True,
                        },
                        "system": {
                            "status": "operational",
                            "uptime": {"hours": 1.0, "days": 0.04},
                            "version": "1.0.0",
                        },
                    }
                }
            },
        },
        503: {
            "description": "メトリクス取得不可",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "SERVICE_UNAVAILABLE",
                        "message": "Metrics unavailable - cache not initialized",
                        "service": "Cache",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def get_system_metrics():
    """システムメトリクスと統計情報を取得"""
    try:
        if not cache_manager.is_initialized():
            raise ServiceUnavailableError(
                message="Metrics unavailable - cache not initialized", service="Cache"
            )

        # Get cache statistics
        cache_stats = cache_manager.get_cache_stats()
        performance_stats = cache_manager.get_performance_stats()
        memory_stats = cache_manager.get_memory_stats()

        # Calculate uptime
        if not hasattr(get_system_metrics, "start_time"):
            get_system_metrics.start_time = time.time()

        uptime_seconds = time.time() - get_system_metrics.start_time
        uptime_hours = uptime_seconds / 3600
        uptime_days = uptime_hours / 24

        metrics = {
            "timestamp": datetime.now(UTC).isoformat(),
            "cache": {
                "status": "initialized"
                if cache_stats["initialized"]
                else "not_initialized",
                "initialization_time_seconds": cache_stats.get("initialization_time"),
                "data_counts": {
                    "posts": cache_stats["posts_count"],
                    "users": cache_stats["users_count"],
                    "comments": cache_stats["comments_count"],
                    "tags": cache_stats["tags_count"],
                    "surveys": cache_stats["surveys_count"],
                    "likes": cache_stats["likes_count"],
                    "bookmarks": cache_stats["bookmarks_count"],
                    "follows": cache_stats["follows_count"],
                },
                "memory_usage": {
                    "total_mb": round(memory_stats["total_mb"], 2),
                    "total_bytes": memory_stats["total_bytes"],
                },
            },
            "performance": {
                "total_requests": performance_stats["total_requests"],
                "average_response_time_ms": performance_stats[
                    "average_response_time_ms"
                ],
                "min_response_time_ms": performance_stats["min_response_time_ms"],
                "max_response_time_ms": performance_stats["max_response_time_ms"],
                "total_response_time_seconds": performance_stats["total_response_time"],
                "requests_under_200ms": performance_stats["requests_under_200ms"],
                "performance_target_percentage": performance_stats[
                    "performance_percentage"
                ],
                "meets_200ms_target": performance_stats["performance_percentage"]
                >= 95.0,
            },
            "system": {
                "status": "operational",
                "uptime": {
                    "seconds": round(uptime_seconds, 2),
                    "hours": round(uptime_hours, 2),
                    "days": round(uptime_days, 2),
                },
                "version": "1.0.0",
            },
        }

        return metrics

    except ServiceUnavailableError:
        raise
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}", exc_info=True)
        raise ServiceUnavailableError(
            message="Metrics collection failed", details={"error": str(e)}
        )
