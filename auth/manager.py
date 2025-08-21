"""
Authentication Manager for simplified MVP authentication
Provides fixed user session handling for TOMOSU backend API
"""

import secrets
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from models.responses import UserResponse

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Simplified authentication manager for MVP
    Uses fixed user sessions without password validation
    """

    def __init__(self):
        # In-memory session storage for MVP
        self.active_sessions: Dict[str, dict] = {}

        # Fixed user data for MVP (matches requirements 1.1, 1.2)
        self.default_user = UserResponse(
            user_id=1,
            username="demo_user",
            display_name="デモユーザー",
            email="demo@tomosu.local",
            profile_image_url="https://example.com/avatar.jpg",
            bio="地域SNS TOMOSU のデモユーザーです",
            area="東京都江東区",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        # Session configuration
        self.session_timeout = timedelta(hours=24)  # 24 hour sessions for MVP

        logger.info("AuthManager initialized with fixed user authentication")

    def create_session(self, user_id: Optional[int] = None) -> str:
        """
        Create a new session for the fixed user (MVP requirement 1.2)
        Always returns a session for the default user regardless of input
        """
        # Generate secure session token
        session_token = secrets.token_urlsafe(32)

        # Create session data (always use fixed user for MVP)
        session_data = {
            "user_id": self.default_user.user_id,
            "username": self.default_user.username,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + self.session_timeout,
            "last_accessed": datetime.now(),
        }

        # Store session
        self.active_sessions[session_token] = session_data

        logger.info(
            f"Created session for user {self.default_user.user_id}: {session_token[:8]}..."
        )
        return session_token

    def validate_session(self, session_token: str) -> Optional[int]:
        """
        Validate session token and return user ID if valid
        Returns None if session is invalid or expired
        """
        if not session_token or session_token not in self.active_sessions:
            return None

        session_data = self.active_sessions[session_token]

        # Check if session has expired
        if datetime.now() > session_data["expires_at"]:
            logger.info(f"Session expired: {session_token[:8]}...")
            self.logout_session(session_token)
            return None

        # Update last accessed time
        session_data["last_accessed"] = datetime.now()

        return session_data["user_id"]

    def get_current_user(self, session_token: str) -> Optional[UserResponse]:
        """
        Get current user information from session token (requirement 1.4)
        Always returns the fixed user for valid sessions
        """
        user_id = self.validate_session(session_token)
        if user_id:
            return self.default_user
        return None

    def logout_session(self, session_token: str) -> bool:
        """
        Logout and remove session (requirement 1.5)
        """
        if session_token in self.active_sessions:
            logger.info(f"Logging out session: {session_token[:8]}...")
            del self.active_sessions[session_token]
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (maintenance function)
        Returns number of sessions cleaned up
        """
        now = datetime.now()
        expired_tokens = [
            token
            for token, data in self.active_sessions.items()
            if now > data["expires_at"]
        ]

        for token in expired_tokens:
            del self.active_sessions[token]

        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

        return len(expired_tokens)

    def get_session_stats(self) -> dict:
        """
        Get session statistics for monitoring
        """
        now = datetime.now()
        active_count = sum(
            1 for data in self.active_sessions.values() if now <= data["expires_at"]
        )

        return {
            "total_sessions": len(self.active_sessions),
            "active_sessions": active_count,
            "expired_sessions": len(self.active_sessions) - active_count,
        }

    def get_default_credentials(self) -> dict:
        """
        Get default credentials for login form (requirement 1.1)
        """
        return {"email": "demo@tomosu.local", "password": "demo123"}


# Global auth manager instance
auth_manager = AuthManager()
