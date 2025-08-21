"""
Unit tests for authentication system
Tests the AuthManager class and authentication middleware
"""

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from auth.manager import AuthManager
from auth.middleware import get_current_user_optional, get_current_user_required
from models.responses import UserResponse


class TestAuthManager:
    """Test cases for AuthManager class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.auth_manager = AuthManager()

    def test_initialization(self):
        """Test AuthManager initialization"""
        assert self.auth_manager.default_user.user_id == 1
        assert self.auth_manager.default_user.username == "demo_user"
        assert self.auth_manager.default_user.email == "demo@tomosu.local"
        assert len(self.auth_manager.active_sessions) == 0

    def test_get_default_credentials(self):
        """Test getting default credentials (requirement 1.1)"""
        credentials = self.auth_manager.get_default_credentials()

        assert "email" in credentials
        assert "password" in credentials
        assert credentials["email"] == "demo@tomosu.local"
        assert credentials["password"] == "demo123"

    def test_create_session(self):
        """Test session creation (requirement 1.2)"""
        # Test session creation without user_id
        session_token = self.auth_manager.create_session()

        assert session_token is not None
        assert len(session_token) > 0
        assert session_token in self.auth_manager.active_sessions

        session_data = self.auth_manager.active_sessions[session_token]
        assert session_data["user_id"] == 1  # Always uses fixed user
        assert session_data["username"] == "demo_user"
        assert "created_at" in session_data
        assert "expires_at" in session_data
        assert "last_accessed" in session_data

    def test_create_session_with_user_id(self):
        """Test session creation with user_id (should still use fixed user)"""
        # Even with different user_id, should use fixed user for MVP
        session_token = self.auth_manager.create_session(user_id=999)

        session_data = self.auth_manager.active_sessions[session_token]
        assert session_data["user_id"] == 1  # Always uses fixed user ID

    def test_validate_session_valid(self):
        """Test session validation with valid token (requirement 1.3)"""
        session_token = self.auth_manager.create_session()

        user_id = self.auth_manager.validate_session(session_token)

        assert user_id == 1

        # Check that last_accessed was updated
        session_data = self.auth_manager.active_sessions[session_token]
        assert session_data["last_accessed"] is not None

    def test_validate_session_invalid_token(self):
        """Test session validation with invalid token"""
        user_id = self.auth_manager.validate_session("invalid_token")
        assert user_id is None

    def test_validate_session_empty_token(self):
        """Test session validation with empty token"""
        user_id = self.auth_manager.validate_session("")
        assert user_id is None

        user_id = self.auth_manager.validate_session(None)
        assert user_id is None

    def test_validate_session_expired(self):
        """Test session validation with expired token"""
        session_token = self.auth_manager.create_session()

        # Manually expire the session
        session_data = self.auth_manager.active_sessions[session_token]
        session_data["expires_at"] = datetime.now() - timedelta(hours=1)

        user_id = self.auth_manager.validate_session(session_token)
        assert user_id is None

        # Session should be removed after expiration
        assert session_token not in self.auth_manager.active_sessions

    def test_get_current_user_valid_session(self):
        """Test getting current user with valid session (requirement 1.4)"""
        session_token = self.auth_manager.create_session()

        user = self.auth_manager.get_current_user(session_token)

        assert user is not None
        assert isinstance(user, UserResponse)
        assert user.user_id == 1
        assert user.username == "demo_user"
        assert user.email == "demo@tomosu.local"

    def test_get_current_user_invalid_session(self):
        """Test getting current user with invalid session"""
        user = self.auth_manager.get_current_user("invalid_token")
        assert user is None

    def test_logout_session_valid(self):
        """Test logout with valid session (requirement 1.5)"""
        session_token = self.auth_manager.create_session()

        # Verify session exists
        assert session_token in self.auth_manager.active_sessions

        # Logout
        result = self.auth_manager.logout_session(session_token)

        assert result is True
        assert session_token not in self.auth_manager.active_sessions

    def test_logout_session_invalid(self):
        """Test logout with invalid session"""
        result = self.auth_manager.logout_session("invalid_token")
        assert result is False

    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        # Create multiple sessions
        token1 = self.auth_manager.create_session()
        token2 = self.auth_manager.create_session()
        token3 = self.auth_manager.create_session()

        # Expire some sessions
        self.auth_manager.active_sessions[token1]["expires_at"] = (
            datetime.now() - timedelta(hours=1)
        )
        self.auth_manager.active_sessions[token2]["expires_at"] = (
            datetime.now() - timedelta(hours=2)
        )

        # Clean up expired sessions
        cleaned_count = self.auth_manager.cleanup_expired_sessions()

        assert cleaned_count == 2
        assert token1 not in self.auth_manager.active_sessions
        assert token2 not in self.auth_manager.active_sessions
        assert token3 in self.auth_manager.active_sessions

    def test_get_session_stats(self):
        """Test getting session statistics"""
        # Create some sessions
        token1 = self.auth_manager.create_session()
        token2 = self.auth_manager.create_session()

        # Expire one session
        self.auth_manager.active_sessions[token1]["expires_at"] = (
            datetime.now() - timedelta(hours=1)
        )

        stats = self.auth_manager.get_session_stats()

        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert "expired_sessions" in stats
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["expired_sessions"] == 1

    def test_multiple_sessions_same_user(self):
        """Test creating multiple sessions for the same user"""
        token1 = self.auth_manager.create_session()
        token2 = self.auth_manager.create_session()

        assert token1 != token2
        assert len(self.auth_manager.active_sessions) == 2

        # Both sessions should be valid
        user1 = self.auth_manager.get_current_user(token1)
        user2 = self.auth_manager.get_current_user(token2)

        assert user1 is not None
        assert user2 is not None
        assert user1.user_id == user2.user_id


class TestAuthenticationIntegration:
    """Integration tests for authentication system"""

    def setup_method(self):
        """Set up test fixtures"""
        from main import app

        self.client = TestClient(app)

    def test_get_default_credentials_endpoint(self):
        """Test the default credentials endpoint"""
        response = self.client.get("/api/v1/auth/default-credentials")

        assert response.status_code == 200
        data = response.json()

        assert "email" in data
        assert "password" in data
        assert "message" in data
        assert data["email"] == "demo@tomosu.local"
        assert data["password"] == "demo123"

    def test_login_endpoint_success(self):
        """Test successful login"""
        login_data = {"email": "any@email.com", "password": "anypassword"}

        response = self.client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "user" in data
        assert data["user"]["user_id"] == 1
        assert data["user"]["username"] == "demo_user"

        # Check that session cookie was set
        assert "session_token" in response.cookies

    def test_login_with_default_credentials(self):
        """Test login with default credentials"""
        login_data = {"email": "demo@tomosu.local", "password": "demo123"}

        response = self.client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "demo@tomosu.local"

    def test_get_current_user_authenticated(self):
        """Test getting current user when authenticated"""
        # First login
        login_data = {"email": "test@test.com", "password": "test"}
        login_response = self.client.post("/api/v1/auth/login", json=login_data)

        # Extract session cookie
        session_cookie = login_response.cookies["session_token"]

        # Get current user
        response = self.client.get(
            "/api/v1/auth/me", cookies={"session_token": session_cookie}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == 1
        assert data["username"] == "demo_user"
        assert data["email"] == "demo@tomosu.local"

    def test_get_current_user_unauthenticated(self):
        """Test getting current user when not authenticated"""
        response = self.client.get("/api/v1/auth/me")

        assert response.status_code == 401
        data = response.json()
        assert "error_code" in data or "detail" in data

    def test_logout_endpoint(self):
        """Test logout endpoint"""
        # First login
        login_data = {"email": "test@test.com", "password": "test"}
        login_response = self.client.post("/api/v1/auth/login", json=login_data)
        session_cookie = login_response.cookies["session_token"]

        # Logout
        response = self.client.post(
            "/api/v1/auth/logout", cookies={"session_token": session_cookie}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_session_status_endpoint(self):
        """Test session status endpoint"""
        # Test without authentication
        response = self.client.get("/api/v1/auth/session-status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

        # Test with authentication
        login_data = {"email": "test@test.com", "password": "test"}
        login_response = self.client.post("/api/v1/auth/login", json=login_data)
        session_cookie = login_response.cookies["session_token"]

        response = self.client.get(
            "/api/v1/auth/session-status", cookies={"session_token": session_cookie}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == 1

    def test_auth_stats_endpoint(self):
        """Test authentication statistics endpoint"""
        response = self.client.get("/api/v1/auth/stats")

        assert response.status_code == 200
        data = response.json()

        assert "session_stats" in data
        assert "default_user" in data
        assert "total_sessions" in data["session_stats"]
        assert data["default_user"]["user_id"] == 1


if __name__ == "__main__":
    pytest.main([__file__])
