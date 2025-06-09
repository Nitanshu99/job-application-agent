"""
Unit Tests Package for Job Automation System

This package contains isolated unit tests that test individual components,
functions, and classes without external dependencies like databases or APIs.

Test Organization:
- test_models/: Database model unit tests
- test_services/: Business logic service tests  
- test_utils/: Utility function tests
- test_schemas/: Pydantic schema validation tests
- test_core/: Core infrastructure tests

Testing Principles:
- Fast execution (< 1 second per test)
- No external dependencies (database, network, files)
- High code coverage (>90%)
- Isolated and independent tests
- Comprehensive edge case coverage
- Mock external dependencies

Usage:
    # Run all unit tests
    pytest backend/tests/unit/

    # Run with coverage
    pytest backend/tests/unit/ --cov=app --cov-report=html

    # Run specific test module
    pytest backend/tests/unit/test_services/test_document_service.py
"""

import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from typing import Any, Dict, List, Optional

import pytest

# Add app to Python path for imports
app_dir = Path(__file__).parent.parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Configure test logging
logging.getLogger("app").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)

# Test configuration constants
TEST_CONFIG = {
    "database_url": "sqlite+aiosqlite:///:memory:",
    "secret_key": "test-secret-key-unit-tests",
    "access_token_expire_minutes": 30,
    "debug": True,
    "testing": True,
    "log_level": "CRITICAL"
}

# Common test data
SAMPLE_USER_DATA = {
    "email": "test@example.com",
    "full_name": "Test User",
    "phone_number": "+1234567890",
    "location": "San Francisco, CA",
    "skills": ["Python", "FastAPI", "React"],
    "experience_years": 5,
    "education": "Bachelor's in Computer Science"
}

SAMPLE_JOB_DATA = {
    "title": "Senior Software Engineer",
    "company": "TechCorp Inc.",
    "location": "San Francisco, CA",
    "job_type": "full-time",
    "salary_min": 120000,
    "salary_max": 180000,
    "description": "We are seeking a Senior Software Engineer...",
    "requirements": ["5+ years experience", "Python expertise"],
    "url": "https://techcorp.com/jobs/senior-engineer"
}

SAMPLE_APPLICATION_DATA = {
    "status": "pending",
    "applied_at": "2024-01-15T10:30:00Z",
    "application_method": "automated",
    "notes": "Applied through automation system"
}


def create_mock_settings(**overrides):
    """Create mock settings for testing."""
    mock_settings = MagicMock()
    
    # Default test settings
    for key, value in TEST_CONFIG.items():
        setattr(mock_settings, key, value)
    
    # Apply overrides
    for key, value in overrides.items():
        setattr(mock_settings, key, value)
    
    # Add commonly used properties
    mock_settings.is_testing = True
    mock_settings.is_production = False
    mock_settings.is_development = False
    
    return mock_settings


def create_mock_database_session():
    """Create mock database session for unit tests."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = MagicMock()
    mock_session.query = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.scalar = AsyncMock()
    mock_session.close = AsyncMock()
    
    return mock_session


def create_mock_llm_service(service_name: str = "test"):
    """Create mock LLM service for testing."""
    mock_service = AsyncMock()
    mock_service.initialize = AsyncMock(return_value=True)
    mock_service.is_healthy = AsyncMock(return_value=True)
    mock_service.shutdown = AsyncMock()
    
    # Service-specific mock responses
    if service_name == "phi3":
        mock_service.generate_resume = AsyncMock(return_value={
            "content": "Generated resume content",
            "success": True,
            "model_used": "phi3-mini"
        })
        mock_service.generate_cover_letter = AsyncMock(return_value={
            "content": "Generated cover letter content", 
            "success": True,
            "model_used": "phi3-mini"
        })
    elif service_name == "gemma":
        mock_service.analyze_job_match = AsyncMock(return_value={
            "relevance_score": 0.85,
            "matching_skills": ["Python", "FastAPI"],
            "missing_skills": ["Docker"],
            "analysis": "Good match for this position"
        })
    elif service_name == "mistral":
        mock_service.automate_application = AsyncMock(return_value={
            "success": True,
            "fields_filled": 8,
            "application_url": "https://example.com/apply/123"
        })
    
    return mock_service


def create_mock_user_model(**kwargs):
    """Create mock user model for testing."""
    user = MagicMock()
    user.id = kwargs.get("id", 1)
    user.email = kwargs.get("email", SAMPLE_USER_DATA["email"])
    user.full_name = kwargs.get("full_name", SAMPLE_USER_DATA["full_name"])
    user.phone_number = kwargs.get("phone_number", SAMPLE_USER_DATA["phone_number"])
    user.location = kwargs.get("location", SAMPLE_USER_DATA["location"])
    user.skills = kwargs.get("skills", SAMPLE_USER_DATA["skills"])
    user.experience_years = kwargs.get("experience_years", SAMPLE_USER_DATA["experience_years"])
    user.education = kwargs.get("education", SAMPLE_USER_DATA["education"])
    user.is_active = kwargs.get("is_active", True)
    user.is_superuser = kwargs.get("is_superuser", False)
    user.created_at = kwargs.get("created_at", "2024-01-01T00:00:00Z")
    
    return user


def create_mock_job_model(**kwargs):
    """Create mock job model for testing."""
    job = MagicMock()
    job.id = kwargs.get("id", 1)
    job.title = kwargs.get("title", SAMPLE_JOB_DATA["title"])
    job.company = kwargs.get("company", SAMPLE_JOB_DATA["company"])
    job.location = kwargs.get("location", SAMPLE_JOB_DATA["location"])
    job.job_type = kwargs.get("job_type", SAMPLE_JOB_DATA["job_type"])
    job.salary_min = kwargs.get("salary_min", SAMPLE_JOB_DATA["salary_min"])
    job.salary_max = kwargs.get("salary_max", SAMPLE_JOB_DATA["salary_max"])
    job.description = kwargs.get("description", SAMPLE_JOB_DATA["description"])
    job.requirements = kwargs.get("requirements", SAMPLE_JOB_DATA["requirements"])
    job.url = kwargs.get("url", SAMPLE_JOB_DATA["url"])
    job.source = kwargs.get("source", "company_website")
    job.relevance_score = kwargs.get("relevance_score", 0.85)
    job.is_active = kwargs.get("is_active", True)
    job.scraped_at = kwargs.get("scraped_at", "2024-01-15T08:00:00Z")
    
    return job


# Test utilities
def assert_valid_email(email: str):
    """Assert that email format is valid."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    assert re.match(pattern, email), f"Invalid email format: {email}"


def assert_valid_phone(phone: str):
    """Assert that phone number format is valid."""
    import re
    # Simple phone validation - starts with + and has 10-15 digits
    pattern = r'^\+\d{10,15}$'
    assert re.match(pattern, phone), f"Invalid phone format: {phone}"


def assert_valid_url(url: str):
    """Assert that URL format is valid."""
    import re
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    assert re.match(pattern, url), f"Invalid URL format: {url}"


# Export commonly used items
__all__ = [
    "TEST_CONFIG",
    "SAMPLE_USER_DATA",
    "SAMPLE_JOB_DATA", 
    "SAMPLE_APPLICATION_DATA",
    "create_mock_settings",
    "create_mock_database_session",
    "create_mock_llm_service",
    "create_mock_user_model",
    "create_mock_job_model",
    "assert_valid_email",
    "assert_valid_phone",
    "assert_valid_url"
]