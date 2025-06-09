"""
Integration Tests Package for Job Automation System

This package contains integration tests that verify component interactions
and test complete workflows with real or realistic external dependencies.

Test Categories:
- API Integration: Full HTTP request/response cycles
- Database Integration: Real database operations and transactions
- Service Integration: Cross-service communication and workflows
- External API Integration: Third-party service interactions
- End-to-End Workflows: Complete user journeys and business processes

Test Organization:
- test_api/: FastAPI endpoint integration tests
- test_database/: Database operation integration tests
- test_services/: Service interaction tests
- test_workflows/: End-to-end workflow tests
- test_external/: Third-party integration tests
- test_performance/: Load and performance tests

Testing Infrastructure:
- Real test database (PostgreSQL or SQLite)
- Redis test instance for caching
- Mock external services where appropriate
- Test data fixtures and factories
- Database migrations and cleanup
- Containerized test environment support

Usage:
    # Run all integration tests
    pytest backend/tests/integration/

    # Run with test database
    pytest backend/tests/integration/ --db-url=postgresql://test:test@localhost/test_db

    # Run specific workflow tests
    pytest backend/tests/integration/test_workflows/test_job_application_flow.py

    # Run performance tests
    pytest backend/tests/integration/test_performance/ -m performance
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import asyncpg
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to Python path
app_dir = Path(__file__).parent.parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Configure integration test logging
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Integration test configuration
INTEGRATION_CONFIG = {
    "database_url": os.getenv(
        "TEST_DATABASE_URL", 
        "postgresql+asyncpg://test:test@localhost:5432/test_jobautomation"
    ),
    "redis_url": os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1"),
    "secret_key": "integration-test-secret-key",
    "access_token_expire_minutes": 60,
    "debug": True,
    "testing": True,
    "log_level": "INFO",
    "enable_auto_apply": False,
    "enable_notifications": False,
    "phi3_service_url": os.getenv("TEST_PHI3_URL", "http://localhost:8001"),
    "gemma_service_url": os.getenv("TEST_GEMMA_URL", "http://localhost:8002"), 
    "mistral_service_url": os.getenv("TEST_MISTRAL_URL", "http://localhost:8003")
}

# Test data for integration tests
INTEGRATION_USER_DATA = {
    "email": "integration@example.com",
    "password": "IntegrationTest123!",
    "full_name": "Integration Test User",
    "phone_number": "+1555123456",
    "location": "San Francisco, CA",
    "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
    "experience_years": 7,
    "education": "Master's in Computer Science",
    "job_preferences": {
        "job_types": ["full-time", "contract"],
        "industries": ["technology", "fintech"],
        "remote_preference": "hybrid",
        "salary_expectation": {"min": 130000, "max": 200000}
    }
}

INTEGRATION_JOB_DATA = {
    "title": "Senior Full Stack Engineer",
    "company": "Integration TestCorp",
    "location": "San Francisco, CA",
    "job_type": "full-time",
    "salary_min": 140000,
    "salary_max": 190000,
    "description": """
    We are seeking a Senior Full Stack Engineer to join our growing team.
    You will work on building scalable web applications using modern technologies.
    
    Key Responsibilities:
    - Develop and maintain web applications using Python and React
    - Design and implement RESTful APIs
    - Work with PostgreSQL databases
    - Collaborate with cross-functional teams
    - Participate in code reviews and technical discussions
    """,
    "requirements": [
        "5+ years of software development experience",
        "Strong proficiency in Python and JavaScript",
        "Experience with FastAPI or similar frameworks",
        "Knowledge of React and modern frontend frameworks", 
        "Database design and optimization skills",
        "Experience with Docker and containerization",
        "Strong problem-solving and communication skills"
    ],
    "benefits": [
        "Competitive salary and equity package",
        "Health, dental, and vision insurance",
        "401(k) with company matching",
        "Flexible work arrangements",
        "Professional development budget",
        "Catered meals and snacks"
    ],
    "url": "https://integrationtestcorp.com/careers/senior-fullstack-engineer",
    "source": "company_website",
    "is_active": True
}


async def setup_test_database():
    """Set up test database for integration tests."""
    try:
        # Create test database if it doesn't exist
        db_url = INTEGRATION_CONFIG["database_url"]
        if "postgresql" in db_url:
            # Extract connection details
            import re
            match = re.search(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if match:
                user, password, host, port, dbname = match.groups()
                
                # Connect to postgres database to create test database
                admin_conn = await asyncpg.connect(
                    user=user, password=password, 
                    host=host, port=port, database='postgres'
                )
                
                try:
                    await admin_conn.execute(f'CREATE DATABASE {dbname}')
                    print(f"✅ Created test database: {dbname}")
                except asyncpg.DuplicateDatabaseError:
                    print(f"📊 Test database already exists: {dbname}")
                finally:
                    await admin_conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup test database: {e}")
        return False


async def cleanup_test_database():
    """Clean up test database after integration tests."""
    try:
        db_url = INTEGRATION_CONFIG["database_url"]
        if "postgresql" in db_url:
            import re
            match = re.search(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if match:
                user, password, host, port, dbname = match.groups()
                
                admin_conn = await asyncpg.connect(
                    user=user, password=password,
                    host=host, port=port, database='postgres'
                )
                
                try:
                    # Terminate active connections
                    await admin_conn.execute(f"""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity 
                        WHERE datname = '{dbname}' AND pid <> pg_backend_pid()
                    """)
                    
                    # Drop test database
                    await admin_conn.execute(f'DROP DATABASE IF EXISTS {dbname}')
                    print(f"🗑️ Cleaned up test database: {dbname}")
                    
                except Exception as e:
                    print(f"⚠️ Database cleanup warning: {e}")
                finally:
                    await admin_conn.close()
        
    except Exception as e:
        print(f"❌ Failed to cleanup test database: {e}")


def create_integration_settings(**overrides):
    """Create settings for integration tests."""
    from app.core.config import Settings
    
    config = INTEGRATION_CONFIG.copy()
    config.update(overrides)
    
    return Settings(**config)


async def create_test_client() -> AsyncClient:
    """Create HTTP client for API integration tests."""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        return client


def create_test_user_payload(**overrides) -> Dict[str, Any]:
    """Create user registration payload for tests."""
    payload = INTEGRATION_USER_DATA.copy()
    payload.update(overrides)
    return payload


def create_test_job_payload(**overrides) -> Dict[str, Any]:
    """Create job posting payload for tests."""
    payload = INTEGRATION_JOB_DATA.copy()
    payload.update(overrides)
    return payload


async def authenticate_test_user(client: AsyncClient, user_data: Dict[str, Any]) -> Dict[str, str]:
    """Authenticate test user and return auth headers."""
    # Register user
    register_response = await client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    # Login to get token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    login_response = await client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    return {"Authorization": f"Bearer {access_token}"}


# Performance test utilities
def measure_response_time(func):
    """Decorator to measure function execution time."""
    import time
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"⏱️ {func.__name__} executed in {execution_time:.3f} seconds")
        
        return result
    
    return wrapper


class IntegrationTestMetrics:
    """Collect and analyze integration test metrics."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_rates: Dict[str, int] = {}
        self.success_rates: Dict[str, int] = {}
    
    def record_response_time(self, endpoint: str, time_ms: float):
        """Record API response time."""
        self.response_times.append(time_ms)
    
    def record_error(self, error_type: str):
        """Record test error."""
        self.error_rates[error_type] = self.error_rates.get(error_type, 0) + 1
    
    def record_success(self, test_type: str):
        """Record test success."""
        self.success_rates[test_type] = self.success_rates.get(test_type, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test metrics summary."""
        return {
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "max_response_time": max(self.response_times) if self.response_times else 0,
            "min_response_time": min(self.response_times) if self.response_times else 0,
            "total_errors": sum(self.error_rates.values()),
            "total_successes": sum(self.success_rates.values()),
            "error_breakdown": self.error_rates,
            "success_breakdown": self.success_rates
        }


# Export commonly used items
__all__ = [
    "INTEGRATION_CONFIG",
    "INTEGRATION_USER_DATA",
    "INTEGRATION_JOB_DATA",
    "setup_test_database",
    "cleanup_test_database", 
    "create_integration_settings",
    "create_test_client",
    "create_test_user_payload",
    "create_test_job_payload",
    "authenticate_test_user",
    "measure_response_time",
    "IntegrationTestMetrics"
]