"""
Authentication routes for simplified MVP authentication
"""
import logging
from fastapi import APIRouter, HTTPException, status, Response, Depends
from pydantic import BaseModel, Field
from typing import Optional

from models.responses import UserResponse, ErrorResponse
from .manager import auth_manager
from .middleware import get_current_user_required, get_current_user_optional, get_session_token

logger = logging.getLogger(__name__)

# Create router for authentication endpoints
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model (MVP - accepts any credentials)"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response model"""
    message: str = Field(..., description="Login success message")
    user: UserResponse = Field(..., description="User information")


class DefaultCredentialsResponse(BaseModel):
    """Default credentials response for MVP"""
    email: str = Field(..., description="Default email")
    password: str = Field(..., description="Default password")
    message: str = Field(..., description="Instructions")


@router.get("/default-credentials", response_model=DefaultCredentialsResponse)
async def get_default_credentials():
    """
    Get default credentials for MVP login (requirement 1.1)
    Returns pre-filled credentials for the login form
    """
    credentials = auth_manager.get_default_credentials()
    return DefaultCredentialsResponse(
        email=credentials["email"],
        password=credentials["password"],
        message="これらの認証情報を使用してログインできます（MVP版では任意の値でもログイン可能）"
    )


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, response: Response):
    """
    Login endpoint for MVP (requirement 1.2)
    Accepts any credentials and always logs in as the fixed user
    """
    try:
        # Create session (always succeeds for MVP)
        session_token = auth_manager.create_session()
        
        # Set secure session cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        logger.info(f"User logged in successfully: {login_request.email}")
        
        return LoginResponse(
            message="ログインに成功しました",
            user=auth_manager.default_user
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ログイン処理中にエラーが発生しました"
        )


@router.post("/logout")
async def logout(
    response: Response, 
    session_token: Optional[str] = Depends(get_session_token),
    current_user: UserResponse = Depends(get_current_user_required)
):
    """
    Logout endpoint (requirement 1.5)
    Removes session cookie and invalidates session
    """
    try:
        # Invalidate session if token exists
        if session_token:
            auth_manager.logout_session(session_token)
        
        # Clear session cookie
        response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        logger.info(f"User logged out: {current_user.username}")
        
        return {"message": "ログアウトしました"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ログアウト処理中にエラーが発生しました"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user_required)):
    """
    Get current user information (requirement 1.4)
    Returns the fixed user profile for authenticated sessions
    """
    return current_user


@router.get("/session-status")
async def get_session_status(current_user: Optional[UserResponse] = Depends(get_current_user_optional)):
    """
    Check session status for debugging and monitoring
    """
    if current_user:
        return {
            "authenticated": True,
            "user_id": current_user.user_id,
            "username": current_user.username
        }
    else:
        return {"authenticated": False}


@router.get("/stats")
async def get_auth_stats():
    """
    Get authentication statistics for monitoring
    """
    stats = auth_manager.get_session_stats()
    return {
        "session_stats": stats,
        "default_user": {
            "user_id": auth_manager.default_user.user_id,
            "username": auth_manager.default_user.username
        }
    }