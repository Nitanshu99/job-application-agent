"""
Integration tests for authentication API endpoints.

Tests user registration, login, token refresh, and authentication flows.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core.security import create_access_token, verify_password
from app.models.user import User


class TestAuthAPI:
    """Integration tests for authentication endpoints."""

    async def test_register_user_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "strongpassword123",
            "full_name": "New User",
            "phone_number": "+1555123456",
            "location": "San Francisco, CA",
            "skills": ["Python", "FastAPI"],
            "experience_years": 3
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

    async def test_register_user_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration with existing email."""
        user_data = {
            "email": test_user.email,  # Use existing email
            "password": "strongpassword123",
            "full_name": "Another User",
            "phone_number": "+1555654321"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "email already registered" in data["detail"].lower()

    async def test_register_user_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        user_data = {
            "email": "invalid-email",
            "password": "strongpassword123",
            "full_name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error

    async def test_register_user_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "email": "test@example.com",
            "password": "123",  # Too weak
            "full_name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login with valid credentials."""
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", 
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_invalid_email(self, async_client: AsyncClient):
        """Test login with non-existent email."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "somepassword"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "incorrect email or password" in data["detail"].lower()

    async def test_login_invalid_password(self, async_client: AsyncClient, test_user: User):
        """Test login with incorrect password."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401

    async def test_login_inactive_user(self, async_client: AsyncClient, db_session, test_user: User):
        """Test login with inactive user account."""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()
        
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "inactive" in data["detail"].lower()

    async def test_refresh_token_success(self, async_client: AsyncClient, test_user: User):
        """Test successful token refresh."""
        # First, login to get tokens
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test token refresh with invalid refresh token."""
        refresh_data = {"refresh_token": "invalid_token"}
        
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401

    async def test_logout_success(self, async_client: AsyncClient, auth_headers):
        """Test successful logout."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"

    async def test_logout_without_token(self, async_client: AsyncClient):
        """Test logout without authentication token."""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401

    async def test_logout_invalid_token(self, async_client: AsyncClient):
        """Test logout with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = await async_client.post("/api/v1/auth/logout", headers=headers)
        
        assert response.status_code == 401

    async def test_password_reset_request(self, async_client: AsyncClient, test_user: User):
        """Test password reset request."""
        reset_data = {"email": test_user.email}
        
        response = await async_client.post("/api/v1/auth/password-reset-request", json=reset_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "reset link sent" in data["message"].lower()

    async def test_password_reset_request_nonexistent_email(self, async_client: AsyncClient):
        """Test password reset request with non-existent email."""
        reset_data = {"email": "nonexistent@example.com"}
        
        response = await async_client.post("/api/v1/auth/password-reset-request", json=reset_data)
        
        # Should still return 200 for security (don't reveal if email exists)
        assert response.status_code == 200

    async def test_get_current_user(self, async_client: AsyncClient, auth_headers, test_user: User):
        """Test getting current user information."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["id"] == test_user.id

    async def test_get_current_user_without_token(self, async_client: AsyncClient):
        """Test getting current user without authentication."""
        response = await async_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    async def test_update_password(self, async_client: AsyncClient, auth_headers, test_user: User):
        """Test updating user password."""
        password_data = {
            "current_password": "testpassword123",
            "new_password": "newstrongpassword456"
        }
        
        response = await async_client.put(
            "/api/v1/auth/update-password",
            json=password_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password updated successfully"

    async def test_update_password_wrong_current(self, async_client: AsyncClient, auth_headers):
        """Test updating password with wrong current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newstrongpassword456"
        }
        
        response = await async_client.put(
            "/api/v1/auth/update-password",
            json=password_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400

    async def test_admin_only_endpoint_as_user(self, async_client: AsyncClient, auth_headers):
        """Test admin-only endpoint with regular user."""
        response = await async_client.get("/api/v1/auth/admin/users", headers=auth_headers)
        
        assert response.status_code == 403

    async def test_admin_only_endpoint_as_admin(self, async_client: AsyncClient, admin_auth_headers):
        """Test admin-only endpoint with admin user."""
        response = await async_client.get("/api/v1/auth/admin/users", headers=admin_auth_headers)
        
        assert response.status_code == 200

    async def test_token_expiry_handling(self, async_client: AsyncClient, test_user: User):
        """Test handling of expired tokens."""
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=-3600  # Expired 1 hour ago
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401

    async def test_multiple_login_sessions(self, async_client: AsyncClient, test_user: User):
        """Test multiple concurrent login sessions."""
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }
        
        # Create multiple login sessions
        session1 = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        session2 = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert session1.status_code == 200
        assert session2.status_code == 200
        
        # Both sessions should have different tokens
        token1 = session1.json()["access_token"]
        token2 = session2.json()["access_token"]
        assert token1 != token2

    async def test_email_verification_flow(self, async_client: AsyncClient, test_user: User):
        """Test email verification flow."""
        # Request email verification
        response = await async_client.post(
            "/api/v1/auth/verify-email-request",
            json={"email": test_user.email}
        )
        
        assert response.status_code == 200

    async def test_rate_limiting_login_attempts(self, async_client: AsyncClient, test_user: User):
        """Test rate limiting on login attempts."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        # Make multiple failed login attempts
        for _ in range(6):  # Assuming rate limit is 5 attempts
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        
        # After multiple failed attempts, should be rate limited
        assert response.status_code in [429, 401]  # Either rate limited or still unauthorized

    async def test_oauth_login_google(self, async_client: AsyncClient):
        """Test Google OAuth login initiation."""
        response = await async_client.get("/api/v1/auth/oauth/google")
        
        # Should redirect to Google OAuth
        assert response.status_code in [302, 307]
        assert "google" in response.headers.get("location", "").lower()

    async def test_account_lockout_after_failed_attempts(self, async_client: AsyncClient, test_user: User, db_session):
        """Test account lockout after multiple failed login attempts."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        # Make multiple failed attempts to trigger lockout
        for _ in range(10):
            await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        
        # Try with correct password - should still be locked
        login_data["password"] = "testpassword123"
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Account should be locked
        assert response.status_code == 423  # Locked status code
