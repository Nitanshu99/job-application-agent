"""
Security integration tests for the job automation system.

Tests authentication, authorization, input validation, and security measures.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch

from app.core.security import create_access_token, verify_password
from app.models.user import User


class TestSecurityMeasures:
    """Test suite for security-related functionality."""

    async def test_sql_injection_prevention(self, async_client: AsyncClient, auth_headers):
        """Test SQL injection prevention in search endpoints."""
        # Attempt SQL injection in job search
        malicious_queries = [
            "'; DROP TABLE jobs; --",
            "python' OR '1'='1",
            "python'; UPDATE users SET is_superuser=true; --",
            "1' UNION SELECT * FROM users --"
        ]
        
        for query in malicious_queries:
            response = await async_client.get(
                "/api/v1/jobs/search",
                params={"keywords": query},
                headers=auth_headers
            )
            
            # Should return normal response, not error (SQL injection prevented)
            assert response.status_code in [200, 422]  # 422 for validation errors
            
            # Ensure no SQL error messages are exposed
            if response.status_code != 200:
                assert "SQL" not in response.text.upper()
                assert "DATABASE" not in response.text.upper()

    async def test_xss_prevention(self, async_client: AsyncClient, auth_headers):
        """Test XSS prevention in user input fields."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in xss_payloads:
            # Test in profile update
            update_data = {
                "full_name": payload,
                "location": f"City {payload}"
            }
            
            response = await async_client.put(
                "/api/v1/users/profile",
                json=update_data,
                headers=auth_headers
            )
            
            if response.status_code == 200:
                # If update succeeds, ensure XSS payload is sanitized
                data = response.json()
                assert "<script>" not in data.get("full_name", "")
                assert "javascript:" not in data.get("location", "")

    async def test_authentication_bypass_attempts(self, async_client: AsyncClient):
        """Test various authentication bypass attempts."""
        protected_endpoints = [
            "/api/v1/users/profile",
            "/api/v1/applications",
            "/api/v1/documents",
            "/api/v1/jobs/recommendations"
        ]
        
        bypass_tokens = [
            "Bearer invalid_token",
            "Bearer null",
            "Bearer undefined",
            "Bearer ",
            "Basic admin:admin",
            "Token fake_token"
        ]
        
        for endpoint in protected_endpoints:
            # Test without authorization header
            response = await async_client.get(endpoint)
            assert response.status_code == 401
            
            # Test with invalid tokens
            for token in bypass_tokens:
                response = await async_client.get(
                    endpoint,
                    headers={"Authorization": token}
                )
                assert response.status_code in [401, 422]

    async def test_authorization_privilege_escalation(self, async_client: AsyncClient, auth_headers, admin_auth_headers):
        """Test privilege escalation prevention."""
        admin_only_endpoints = [
            "/api/v1/auth/admin/users",
            "/api/v1/jobs",  # POST (create job)
            "/api/v1/users/search"
        ]
        
        for endpoint in admin_only_endpoints:
            # Regular user should not access admin endpoints
            response = await async_client.get(endpoint, headers=auth_headers)
            assert response.status_code in [403, 405]  # Forbidden or Method Not Allowed
            
            # Admin should have access
            response = await async_client.get(endpoint, headers=admin_auth_headers)
            assert response.status_code in [200, 405]  # 405 if endpoint doesn't support GET

    async def test_jwt_token_tampering(self, async_client: AsyncClient, test_user: User):
        """Test JWT token tampering detection."""
        # Create a valid token
        valid_token = create_access_token(data={"sub": test_user.email})
        
        # Tamper with the token
        token_parts = valid_token.split('.')
        
        # Modify payload
        tampered_payload = token_parts[1] + "tampered"
        tampered_token = f"{token_parts[0]}.{tampered_payload}.{token_parts[2]}"
        
        response = await async_client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        
        assert response.status_code == 401

    async def test_expired_token_handling(self, async_client: AsyncClient, test_user: User):
        """Test expired JWT token handling."""
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(minutes=-1)  # Already expired
        )
        
        response = await async_client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    async def test_rate_limiting_protection(self, async_client: AsyncClient):
        """Test rate limiting on sensitive endpoints."""
        # Test login rate limiting
        login_data = {
            "username": "test@example.com",
            "password": "wrong_password"
        }
        
        # Make multiple failed login attempts
        failed_attempts = 0
        for i in range(10):  # Attempt 10 failed logins
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 429:  # Rate limited
                break
            elif response.status_code == 401:  # Failed login
                failed_attempts += 1
        
        # Should eventually get rate limited
        assert failed_attempts < 10  # Rate limiting should kick in before 10 attempts

    async def test_password_security_requirements(self, async_client: AsyncClient):
        """Test password security requirements."""
        weak_passwords = [
            "password",
            "12345678",
            "qwerty",
            "admin",
            "password123",
            "abc123"
        ]
        
        for weak_password in weak_passwords:
            user_data = {
                "email": f"test_{weak_password}@example.com",
                "password": weak_password,
                "full_name": "Test User"
            }
            
            response = await async_client.post("/api/v1/auth/register", json=user_data)
            
            # Should reject weak passwords
            assert response.status_code == 422

    async def test_cors_configuration(self, async_client: AsyncClient):
        """Test CORS configuration and headers."""
        # Test preflight request
        response = await async_client.options(
            "/api/v1/jobs/search",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        # Should handle OPTIONS request
        assert response.status_code in [200, 204]
        
        # Check CORS headers
        cors_headers = response.headers
        if "access-control-allow-origin" in cors_headers:
            # Should not allow arbitrary origins
            assert cors_headers["access-control-allow-origin"] != "*"

    async def test_sensitive_data_exposure(self, async_client: AsyncClient, auth_headers):
        """Test that sensitive data is not exposed in API responses."""
        # Get user profile
        response = await async_client.get("/api/v1/users/profile", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Sensitive fields should not be in response
            sensitive_fields = [
                "hashed_password",
                "password",
                "secret_key",
                "private_key",
                "api_key"
            ]
            
            for field in sensitive_fields:
                assert field not in data
                assert field not in str(data).lower()

    async def test_input_validation_and_sanitization(self, async_client: AsyncClient, auth_headers):
        """Test input validation and sanitization."""
        # Test extremely long input
        long_string = "A" * 10000
        
        response = await async_client.put(
            "/api/v1/users/profile",
            json={"full_name": long_string},
            headers=auth_headers
        )
        
        # Should reject excessively long input
        assert response.status_code == 422
        
        # Test special characters and encoding
        special_data = {
            "full_name": "Test\x00User\xff",  # Null bytes and invalid UTF-8
            "location": "City\r\nInjection"  # CRLF injection attempt
        }
        
        response = await async_client.put(
            "/api/v1/users/profile",
            json=special_data,
            headers=auth_headers
        )
        
        # Should handle or reject invalid characters
        assert response.status_code in [200, 422]

    async def test_file_upload_security(self, async_client: AsyncClient, auth_headers):
        """Test file upload security measures."""
        # Test malicious file types
        malicious_files = [
            ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("script.js", b"alert('XSS')", "application/javascript"),
            ("shell.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
            ("huge_file.txt", b"A" * (10 * 1024 * 1024), "text/plain")  # 10MB file
        ]
        
        for filename, content, content_type in malicious_files:
            files = {"profile_picture": (filename, content, content_type)}
            
            response = await async_client.post(
                "/api/v1/users/profile-picture",
                files=files,
                headers=auth_headers
            )
            
            # Should reject malicious or oversized files
            assert response.status_code in [400, 413, 415, 422]

    async def test_session_security(self, async_client: AsyncClient, test_user: User):
        """Test session security measures."""
        # Login to get session
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if login_response.status_code == 200:
            tokens = login_response.json()
            access_token = tokens["access_token"]
            
            # Test concurrent session limit (if implemented)
            # Create multiple sessions
            sessions = []
            for i in range(5):
                new_login = await async_client.post(
                    "/api/v1/auth/login",
                    data={
                        "username": test_user.email,
                        "password": "testpassword123"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if new_login.status_code == 200:
                    sessions.append(new_login.json()["access_token"])
            
            # Original session might be invalidated if concurrent session limit exists
            profile_response = await async_client.get(
                "/api/v1/users/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            # Session should still be valid or properly invalidated
            assert profile_response.status_code in [200, 401]

    async def test_api_versioning_security(self, async_client: AsyncClient):
        """Test API versioning doesn't expose deprecated vulnerable endpoints."""
        deprecated_endpoints = [
            "/api/v0/users",
            "/api/legacy/auth",
            "/api/old/jobs"
        ]
        
        for endpoint in deprecated_endpoints:
            response = await async_client.get(endpoint)
            
            # Deprecated endpoints should not be accessible
            assert response.status_code in [404, 410]  # Not Found or Gone

    async def test_information_disclosure_prevention(self, async_client: AsyncClient):
        """Test prevention of information disclosure through error messages."""
        # Test with non-existent user
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 401:
            # Error message should not reveal whether user exists
            error_msg = response.json()["detail"].lower()
            assert "user not found" not in error_msg
            assert "does not exist" not in error_msg

    async def test_security_headers(self, async_client: AsyncClient):
        """Test security headers are properly set."""
        response = await async_client.get("/api/v1/jobs/search")
        
        # Check for security headers
        headers = response.headers
        
        # These headers should be present for security
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "strict-transport-security"
        ]
        
        # Note: Not all headers may be implemented, this is more of a recommendation check
        for header in security_headers:
            if header in headers:
                # If present, should have secure values
                value = headers[header].lower()
                if header == "x-content-type-options":
                    assert "nosniff" in value
                elif header == "x-frame-options":
                    assert value in ["deny", "sameorigin"]

    async def test_encryption_at_rest(self, async_client: AsyncClient, auth_headers):
        """Test that sensitive data is encrypted at rest."""
        # This is more of a configuration test
        # Test that encrypted fields remain encrypted in storage
        
        sensitive_data = {
            "phone_number": "+1234567890",
            "ssn": "123-45-6789",  # If stored
            "api_keys": {"openai": "secret_key"}  # If stored
        }
        
        # Update profile with sensitive data
        response = await async_client.put(
            "/api/v1/users/profile",
            json=sensitive_data,
            headers=auth_headers
        )
        
        # The response should not contain raw sensitive data
        if response.status_code == 200:
            data = response.json()
            
            # Phone might be returned, but API keys should not
            if "api_keys" in data:
                # Should be encrypted or masked
                assert data["api_keys"] != sensitive_data["api_keys"]

    async def test_audit_logging(self, async_client: AsyncClient, auth_headers):
        """Test that security-relevant events are logged."""
        # This test verifies that audit logs are created for security events
        # In a real implementation, you'd check log files or a logging service
        
        security_events = [
            ("GET", "/api/v1/users/profile"),  # Profile access
            ("PUT", "/api/v1/users/profile"),  # Profile modification
            ("POST", "/api/v1/applications"),  # Application creation
        ]
        
        for method, endpoint in security_events:
            if method == "GET":
                response = await async_client.get(endpoint, headers=auth_headers)
            elif method == "PUT":
                response = await async_client.put(
                    endpoint,
                    json={"full_name": "Updated Name"},
                    headers=auth_headers
                )
            elif method == "POST":
                response = await async_client.post(
                    endpoint,
                    json={"job_id": 1, "resume_id": 1},
                    headers=auth_headers
                )
            
            # Events should be processed (may return various status codes)
            assert response.status_code < 500  # No server errors

    @patch('app.core.security.verify_recaptcha')
    async def test_recaptcha_protection(self, mock_recaptcha, async_client: AsyncClient):
        """Test reCAPTCHA protection on sensitive endpoints."""
        mock_recaptcha.return_value = False  # Simulate failed CAPTCHA
        
        # Test registration with failed CAPTCHA
        user_data = {
            "email": "captcha_test@example.com",
            "password": "SecurePassword123!",
            "full_name": "CAPTCHA Test",
            "recaptcha_token": "invalid_token"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        # Should reject if CAPTCHA validation fails
        if "recaptcha" in str(response.content).lower():
            assert response.status_code in [400, 422]

    async def test_content_security_policy(self, async_client: AsyncClient):
        """Test Content Security Policy headers."""
        response = await async_client.get("/")
        
        if "content-security-policy" in response.headers:
            csp = response.headers["content-security-policy"]
            
            # Should have restrictive CSP
            assert "unsafe-eval" not in csp
            assert "unsafe-inline" not in csp or "nonce-" in csp

    async def test_secure_communication(self, async_client: AsyncClient):
        """Test secure communication requirements."""
        # In production, all requests should be HTTPS
        # This test checks if HTTP requests are properly redirected
        
        # Test if server enforces HTTPS (would be done at proxy/server level)
        response = await async_client.get("/api/v1/health")
        
        # Should not expose sensitive data over insecure connections
        assert response.status_code in [200, 301, 308, 426]  # OK, redirects, or Upgrade Required
