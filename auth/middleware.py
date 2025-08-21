"""
Authentication middleware for session cookie validation
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException, status, Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.responses import UserResponse
from .manager import auth_manager
from exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# Security scheme for optional authentication
security = HTTPBearer(auto_error=False)


async def get_session_token(request: Request) -> Optional[str]:
    """
    Extract session token from cookies
    """
    return request.cookies.get("session_token")


async def get_current_user_optional(
    session_token: Optional[str] = Depends(get_session_token)
) -> Optional[UserResponse]:
    """
    Get current user from session token (optional - returns None if not authenticated)
    Used for endpoints that work with or without authentication
    """
    if not session_token:
        return None
    
    return auth_manager.get_current_user(session_token)


async def get_current_user_required(
    session_token: Optional[str] = Depends(get_session_token)
) -> UserResponse:
    """
    Get current user from session token (required - raises 401 if not authenticated)
    Used for protected endpoints that require authentication
    """
    if not session_token:
        logger.warning("Missing session token in protected endpoint")
        raise AuthenticationError(
            message="Authentication required",
            details={"reason": "missing_session_token"}
        )
    
    user = auth_manager.get_current_user(session_token)
    if not user:
        logger.warning(f"Invalid or expired session token: {session_token[:8]}...")
        raise AuthenticationError(
            message="Invalid or expired session",
            details={"reason": "invalid_session_token"}
        )
    
    return user


async def validate_session_middleware(request: Request, call_next):
    """
    Middleware to validate session tokens and clean up expired sessions
    This is optional middleware that can be added to the FastAPI app
    """
    # Clean up expired sessions periodically (every 100 requests)
    if hasattr(validate_session_middleware, 'request_count'):
        validate_session_middleware.request_count += 1
    else:
        validate_session_middleware.request_count = 1
    
    if validate_session_middleware.request_count % 100 == 0:
        auth_manager.cleanup_expired_sessions()
    
    # Process request normally
    response = await call_next(request)
    return response