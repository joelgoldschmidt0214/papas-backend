"""
Surveys API endpoints with cache integration
Provides survey management functionality for the TOMOSU backend API
"""

import logging
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Any
from collections import Counter

from models.responses import SurveyResponse, ErrorResponse
from models.requests import SurveyResponseRequest
from cache.manager import cache_manager
from db_control import crud, mymodels_MySQL as models
from sqlalchemy.orm import sessionmaker
from db_control.connect_MySQL import engine

logger = logging.getLogger(__name__)

# Create router for surveys endpoints
router = APIRouter(prefix="/api/v1/surveys", tags=["surveys"])

# Database session configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global variable for testing override
_test_session_factory = None


def get_session_factory():
    """Get the session factory, allowing for test overrides"""
    return _test_session_factory if _test_session_factory else SessionLocal


@router.get("", response_model=List[SurveyResponse])
async def get_surveys(
    skip: int = Query(
        0, ge=0, le=10000, description="Number of surveys to skip for pagination"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum number of surveys to return (optimized for performance)",
    ),
):
    """
    Get all available surveys with response counts (requirement 7.1, 7.2)
    Returns surveys sorted by creation date (newest first)
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing surveys")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # Get all surveys from cache
        all_surveys = cache_manager.get_surveys(
            skip=0, limit=10000
        )  # Get all surveys first

        # Sort surveys by created_at descending (newest first)
        sorted_surveys = sorted(all_surveys, key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        paginated_surveys = sorted_surveys[skip : skip + limit]

        logger.info(
            f"Retrieved {len(paginated_surveys)} surveys (skip={skip}, limit={limit}, total={len(all_surveys)})"
        )
        return paginated_surveys

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving surveys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve surveys",
        )


@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey_by_id(survey_id: int):
    """
    Get a specific survey by ID with response count (requirement 7.1, 7.2)
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing survey")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # Get survey from cache
        survey = cache_manager.get_survey_by_id(survey_id)

        if not survey:
            logger.warning(f"Survey not found: {survey_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey with ID {survey_id} not found",
            )

        logger.info(f"Retrieved survey: {survey_id}")
        return survey

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving survey '{survey_id}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve survey",
        )


@router.get("/{survey_id}/responses", response_model=Dict[str, Any])
async def get_survey_responses(survey_id: int):
    """
    Get aggregated response statistics for a specific survey (requirement 7.3)
    Returns response counts and statistics grouped by choice
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing survey responses")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # First check if survey exists
        survey = cache_manager.get_survey_by_id(survey_id)
        if not survey:
            logger.warning(f"Survey not found: {survey_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey with ID {survey_id} not found",
            )

        # Get survey responses from database (not cached for MVP)
        session_factory = get_session_factory()
        db = session_factory()
        try:
            db_responses = crud.select_responses_by_survey_id(
                db, survey_id, skip=0, limit=10000
            )
        finally:
            db.close()

        # Aggregate response statistics
        total_responses = len(db_responses)

        # Count responses by choice
        choice_counts = Counter(
            response.choice for response in db_responses if response.choice
        )

        # Calculate percentages
        choice_statistics = {}
        for choice, count in choice_counts.items():
            percentage = (count / total_responses * 100) if total_responses > 0 else 0
            choice_statistics[choice] = {
                "count": count,
                "percentage": round(percentage, 2),
            }

        # Count responses with comments
        responses_with_comments = sum(
            1
            for response in db_responses
            if response.comment and response.comment.strip()
        )

        response_data = {
            "survey_id": survey_id,
            "survey_title": survey.title,
            "total_responses": total_responses,
            "choice_statistics": choice_statistics,
            "responses_with_comments": responses_with_comments,
            "response_rate_info": {
                "total_responses": total_responses,
                "target_audience": survey.target_audience,
            },
        }

        logger.info(
            f"Retrieved response statistics for survey {survey_id}: {total_responses} total responses"
        )
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving survey responses for survey '{survey_id}': {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve survey responses",
        )


@router.post("/{survey_id}/responses")
async def submit_survey_response(
    survey_id: int,
    response_request: SurveyResponseRequest,
):
    """
    アンケート回答を投稿（認証なし・重複チェックなし）
    誰でも何度でも投稿可能なMVP版
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when submitting survey response")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # アンケート存在チェックのみ
        survey = cache_manager.get_survey_by_id(survey_id)
        if not survey:
            logger.warning(f"Survey not found: {survey_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey with ID {survey_id} not found",
            )

        # データベースに直接保存（認証・重複チェックなし）
        session_factory = get_session_factory()
        db = session_factory()
        try:
            response_data = {
                "user_id": None,  # 匿名なのでNULL
                "survey_id": survey_id,
                "choice": response_request.choice,
                "comment": response_request.comment,
            }
            
            # 重複チェックなしで直接保存
            db_response = crud.insert_survey_response(db, response_data)
            
            logger.info(f"Anonymous response submitted for survey {survey_id}: choice={response_request.choice}")
            
            return {
                "message": "回答を受け付けました",
                "survey_id": survey_id,
                "response_id": db_response.response_id,
                "choice": response_request.choice,
            }
            
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting anonymous survey response for survey {survey_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="回答の保存に失敗しました"
        )


@router.get("/{survey_id}/comments")
async def get_survey_comments(
    survey_id: int,
    skip: int = Query(0, ge=0, description="Number of comments to skip for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of comments to return"),
):
    """
    アンケートのコメント付き回答を取得
    コメントがある回答のみを返す
    """
    try:
        if not cache_manager.is_initialized():
            logger.error("Cache not initialized when accessing survey comments")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable - cache not initialized",
            )

        # アンケート存在チェック
        survey = cache_manager.get_survey_by_id(survey_id)
        if not survey:
            logger.warning(f"Survey not found: {survey_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey with ID {survey_id} not found",
            )

        # データベースからコメント付き回答を取得
        session_factory = get_session_factory()
        db = session_factory()
        try:
            # コメントがある回答のみを取得
            db_responses = (
                db.query(models.SURVEY_RESPONSES)
                .filter(
                    models.SURVEY_RESPONSES.survey_id == survey_id,
                    models.SURVEY_RESPONSES.comment.isnot(None),
                    models.SURVEY_RESPONSES.comment != "",
                )
                .order_by(models.SURVEY_RESPONSES.submitted_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
        finally:
            db.close()

        # レスポンス形式に変換
        comments = []
        for response in db_responses:
            comments.append({
                "response_id": response.response_id,
                "choice": response.choice,
                "comment": response.comment,
                "submitted_at": response.submitted_at.isoformat(),
                "is_anonymous": response.user_id is None,
            })

        return {
            "survey_id": survey_id,
            "survey_title": survey.title,
            "comments": comments,
            "total_comments": len(comments),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving survey comments for survey {survey_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve survey comments",
        )
