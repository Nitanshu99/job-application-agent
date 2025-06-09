"""
Security utilities for the Job Automation System.

This module provides authentication, authorization, password hashing,
JWT token management, and other security-related functionality.

Features:
- Password hashing and verification with bcrypt
- JWT token creation and validation
- OAuth2 authentication flow
- Permission and role-based access control
- API key management
- Security headers and CSRF protection
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict, List
from pathlib import Path

import jwt
import bcrypt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Bearer token scheme for API keys
bearer_scheme = HTTPBearer()

# Get settings
settings = get_settings()


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def create_password_reset_token(email: str) -> str:
    """
    Create a password reset token.
    
    Args:
        email: User email address
        
    Returns:
        Encoded password reset token
    """
    delta = timedelta(hours=settings.password_reset_token_expire_hours)
    expire = datetime.utcnow() + delta
    
    to_encode = {
        "exp": expire,
        "email": email,
        "type": "password_reset"
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type (access, refresh, password_reset)
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        
        # Check token type
        if payload.get("type") != token_type:
            return None
            
        return payload
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token and extract email.
    
    Args:
        token: Password reset token
        
    Returns:
        Email address if token is valid, None otherwise
    """
    payload = verify_token(token, "password_reset")
    if payload:
        return payload.get("email")
    return None


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        URL-safe random API key string
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    
    Args:
        api_key: Plain API key
        
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        api_key: Plain API key
        hashed_key: Hashed API key to verify against
        
    Returns:
        True if API key matches, False otherwise
    """
    return hash_api_key(api_key) == hashed_key


def create_csrf_token() -> str:
    """
    Create a CSRF token.
    
    Returns:
        CSRF token string
    """
    return secrets.token_hex(16)


def verify_csrf_token(token: str, expected_token: str) -> bool:
    """
    Verify CSRF token.
    
    Args:
        token: Provided CSRF token
        expected_token: Expected CSRF token
        
    Returns:
        True if tokens match, False otherwise
    """
    return hmac.compare_digest(token, expected_token)


def create_signature(data: str, secret: Optional[str] = None) -> str:
    """
    Create HMAC signature for data integrity.
    
    Args:
        data: Data to sign
        secret: Secret key (uses app secret if not provided)
        
    Returns:
        Hexadecimal signature string
    """
    secret_key = secret or settings.secret_key
    signature = hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    )
    return signature.hexdigest()


def verify_signature(data: str, signature: str, secret: Optional[str] = None) -> bool:
    """
    Verify HMAC signature.
    
    Args:
        data: Original data
        signature: Signature to verify
        secret: Secret key (uses app secret if not provided)
        
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = create_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)


def check_password_strength(password: str) -> Dict[str, Union[bool, str, List[str]]]:
    """
    Check password strength and provide feedback.
    
    Args:
        password: Password to check
        
    Returns:
        Dictionary with strength analysis
    """
    feedback = []
    score = 0
    
    # Length check
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password must be at least 8 characters long")
    
    if len(password) >= 12:
        score += 1
    
    # Character type checks
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
    
    if has_upper:
        score += 1
    else:
        feedback.append("Password should contain uppercase letters")
    
    if has_lower:
        score += 1
    else:
        feedback.append("Password should contain lowercase letters")
    
    if has_digit:
        score += 1
    else:
        feedback.append("Password should contain numbers")
    
    if has_special:
        score += 1
    else:
        feedback.append("Password should contain special characters")
    
    # Common patterns check
    common_patterns = ["123", "abc", "password", "admin", "user"]
    if any(pattern in password.lower() for pattern in common_patterns):
        feedback.append("Password should not contain common patterns")
        score = max(0, score - 1)
    
    # Determine strength level
    if score >= 6:
        strength = "very_strong"
    elif score >= 5:
        strength = "strong"
    elif score >= 4:
        strength = "medium"
    elif score >= 3:
        strength = "weak"
    else:
        strength = "very_weak"
    
    return {
        "is_strong": score >= 4,
        "score": score,
        "max_score": 7,
        "strength": strength,
        "feedback": feedback
    }


def generate_secure_filename(original_filename: str) -> str:
    """
    Generate a secure filename.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Secure filename with random prefix
    """
    # Extract file extension
    path = Path(original_filename)
    extension = path.suffix
    
    # Generate random filename
    random_name = secrets.token_hex(16)
    
    return f"{random_name}{extension}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    
    # Remove dangerous characters
    sanitized = re.sub(r'[^\w\s.-]', '', filename)
    
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    
    # Remove multiple consecutive dots
    sanitized = re.sub(r'\.+', '.', sanitized)
    
    # Ensure filename is not empty
    if not sanitized or sanitized == '.':
        sanitized = "file"
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        sanitized = name[:max_name_length] + ('.' + ext if ext else '')
    
    return sanitized


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data like email addresses, phone numbers, etc.
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at the end
        
    Returns:
        Masked data string
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    if "@" in data:  # Email masking
        local, domain = data.split("@", 1)
        if len(local) <= 2:
            masked_local = mask_char * len(local)
        else:
            masked_local = local[0] + mask_char * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
    else:  # General masking
        visible_part = data[-visible_chars:]
        masked_part = mask_char * (len(data) - visible_chars)
        return masked_part + visible_part


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def generate_session_id() -> str:
    """
    Generate a secure session ID.
    
    Returns:
        Random session ID string
    """
    return secrets.token_urlsafe(32)


class SecurityHeaders:
    """Security headers middleware helper."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Get recommended security headers.
        
        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'"
            ),
            "Permissions-Policy": (
                "accelerometer=(), camera=(), geolocation=(), "
                "gyroscope=(), magnetometer=(), microphone=(), "
                "payment=(), usb=()"
            )
        }


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    
    Args:
        val1: First string
        val2: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    return hmac.compare_digest(val1, val2)


def rate_limit_key(request: Request, identifier: Optional[str] = None) -> str:
    """
    Generate rate limit key for request.
    
    Args:
        request: FastAPI request object
        identifier: Optional identifier (user ID, API key, etc.)
        
    Returns:
        Rate limit key string
    """
    if identifier:
        return f"rate_limit:{identifier}"
    
    # Use IP address as fallback
    client_ip = get_client_ip(request)
    return f"rate_limit:ip:{client_ip}"