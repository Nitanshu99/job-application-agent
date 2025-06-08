"""
Test configuration and shared fixtures for the job automation system.

This module provides pytest fixtures and configuration for testing the FastAPI backend,
including database setup, authentication, and mock services.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.document import Document


# Test database URL - using SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
TEST_SYNC_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings with appropriate test configurations."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key",
        access_token_expire_minutes=30,
        redis_url="redis://localhost:6379/1",  # Use test database
        enable_auto_apply=False,  # Disable for testing
        enable_notifications=False,  # Disable for testing
        phi3_service_url="http://localhost:8001",
        gemma_service_url="http://localhost:8002",
        mistral_service_url="http://localhost:8003",
        env="testing",
        debug=True,
    )


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_SYNC_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="session")
def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="function", autouse=True)
async def setup_database(async_engine):
    """Setup and teardown test database for each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency for testing."""
    async def _override_get_db():
        yield db_session
    
    return _override_get_db


@pytest.fixture
def override_get_settings(test_settings):
    """Override the get_settings dependency for testing."""
    def _override_get_settings():
        return test_settings
    
    return _override_get_settings


@pytest.fixture
def client(override_get_db, override_get_settings):
    """Create test client with dependency overrides."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db, override_get_settings):
    """Create async test client with dependency overrides."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        phone_number="+1234567890",
        location="San Francisco, CA",
        skills=["Python", "FastAPI", "React"],
        experience_years=5,
        education="Bachelor's in Computer Science",
        preferred_salary_min=80000,
        preferred_salary_max=120000,
        preferred_locations=["San Francisco", "Remote"],
        job_preferences={
            "job_types": ["full-time"],
            "industries": ["technology", "software"],
            "remote_preference": "hybrid"
        }
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin_user(db_session) -> User:
    """Create a test admin user."""
    admin_user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        phone_number="+1234567891",
        location="New York, NY",
        skills=["Management", "Strategy"],
        experience_years=10,
    )
    
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)
    return admin_user


@pytest.fixture
def user_token(test_user):
    """Generate access token for test user."""
    return create_access_token(data={"sub": test_user.email})


@pytest.fixture
def admin_token(test_admin_user):
    """Generate access token for admin user."""
    return create_access_token(data={"sub": test_admin_user.email})


@pytest.fixture
def auth_headers(user_token):
    """Create authorization headers for test user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_auth_headers(admin_token):
    """Create authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def test_job(db_session, test_user) -> Job:
    """Create a test job posting."""
    job = Job(
        title="Senior Python Developer",
        company="TechCorp Inc.",
        location="San Francisco, CA",
        job_type="full-time",
        salary_min=100000,
        salary_max=150000,
        description="We are looking for a Senior Python Developer...",
        requirements=["5+ years Python experience", "FastAPI knowledge", "SQL skills"],
        url="https://techcorp.com/jobs/senior-python-dev",
        source="company_website",
        scraped_at=None,
        relevance_score=0.85,
        is_active=True,
    )
    
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def test_document(db_session, test_user, test_job) -> Document:
    """Create a test document."""
    document = Document(
        user_id=test_user.id,
        job_id=test_job.id,
        document_type="resume",
        content="Test resume content for Senior Python Developer position...",
        file_path="/tmp/test_resume.pdf",
        generated_at=None,
        template_used="modern_template",
        is_active=True,
    )
    
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest.fixture
async def test_application(db_session, test_user, test_job, test_document) -> Application:
    """Create a test application."""
    application = Application(
        user_id=test_user.id,
        job_id=test_job.id,
        resume_id=test_document.id,
        status="pending",
        applied_at=None,
        application_method="automated",
        notes="Applied through automation system",
        follow_up_date=None,
    )
    
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    return application


@pytest.fixture
def mock_phi3_service():
    """Mock Phi-3 service for document generation."""
    mock_service = AsyncMock()
    mock_service.generate_resume.return_value = {
        "content": "Generated resume content",
        "success": True,
        "model_used": "phi3-mini"
    }
    mock_service.generate_cover_letter.return_value = {
        "content": "Generated cover letter content",
        "success": True,
        "model_used": "phi3-mini"
    }
    mock_service.is_healthy.return_value = True
    return mock_service


@pytest.fixture
def mock_gemma_service():
    """Mock Gemma service for job matching."""
    mock_service = AsyncMock()
    mock_service.analyze_job.return_value = {
        "relevance_score": 0.85,
        "matching_skills": ["Python", "FastAPI"],
        "missing_skills": ["Kubernetes"],
        "analysis": "Good match for candidate profile",
        "success": True,
        "model_used": "gemma-7b"
    }
    mock_service.is_healthy.return_value = True
    return mock_service


@pytest.fixture
def mock_mistral_service():
    """Mock Mistral service for application automation."""
    mock_service = AsyncMock()
    mock_service.fill_application.return_value = {
        "success": True,
        "form_data": {"name": "Test User", "email": "test@example.com"},
        "application_id": "APP-12345",
        "model_used": "mistral-7b"
    }
    mock_service.is_healthy.return_value = True
    return mock_service


@pytest.fixture
def mock_scraper_service():
    """Mock web scraper service."""
    mock_service = MagicMock()
    mock_service.scrape_jobs.return_value = [
        {
            "title": "Python Developer",
            "company": "Tech Company",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "description": "Python development role...",
            "requirements": ["Python", "Django"],
            "salary_min": 80000,
            "salary_max": 120000,
        }
    ]
    mock_service.scrape_job_details.return_value = {
        "description": "Detailed job description...",
        "requirements": ["Python", "Django", "PostgreSQL"],
        "benefits": ["Health insurance", "Remote work"],
        "application_deadline": "2024-12-31",
    }
    return mock_service


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    mock_service = AsyncMock()
    mock_service.send_email.return_value = {"success": True, "message_id": "12345"}
    mock_service.send_application_confirmation.return_value = {"success": True}
    mock_service.send_status_update.return_value = {"success": True}
    return mock_service


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    return mock_redis


@pytest.fixture
def temp_file():
    """Create a temporary file for testing file operations."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test file content")
        tmp.flush()
        yield tmp.name
    
    # Cleanup
    try:
        os.unlink(tmp.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_job_data():
    """Sample job posting data for testing."""
    return {
        "title": "Senior Software Engineer",
        "company": "Innovation Labs",
        "location": "San Francisco, CA",
        "job_type": "full-time",
        "salary_min": 120000,
        "salary_max": 180000,
        "description": "Join our team as a Senior Software Engineer...",
        "requirements": [
            "5+ years of software development experience",
            "Proficiency in Python and JavaScript",
            "Experience with cloud platforms",
            "Strong problem-solving skills"
        ],
        "url": "https://innovationlabs.com/careers/senior-engineer",
        "source": "company_website",
        "benefits": [
            "Health, dental, and vision insurance",
            "401(k) with company match",
            "Flexible work arrangements",
            "Professional development budget"
        ]
    }


@pytest.fixture
def sample_user_profile():
    """Sample user profile data for testing."""
    return {
        "email": "jane.doe@example.com",
        "full_name": "Jane Doe",
        "phone_number": "+1555123456",
        "location": "San Francisco, CA",
        "skills": [
            "Python", "JavaScript", "React", "FastAPI",
            "PostgreSQL", "Docker", "AWS", "Git"
        ],
        "experience_years": 6,
        "education": "Master's in Computer Science",
        "work_experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Startup",
                "duration": "2021-2024",
                "description": "Developed full-stack applications using Python and React"
            },
            {
                "title": "Junior Developer",
                "company": "Small Agency",
                "duration": "2019-2021",
                "description": "Built websites and web applications"
            }
        ],
        "certifications": [
            "AWS Certified Developer",
            "Google Cloud Professional"
        ],
        "preferred_salary_min": 110000,
        "preferred_salary_max": 160000,
        "preferred_locations": ["San Francisco", "Remote", "New York"],
        "job_preferences": {
            "job_types": ["full-time"],
            "industries": ["technology", "fintech", "healthtech"],
            "remote_preference": "hybrid",
            "company_size": ["startup", "medium"]
        }
    }


# Async test helpers
@pytest_asyncio.fixture
async def cleanup_db(db_session):
    """Cleanup database after test."""
    yield
    # Cleanup logic if needed
    await db_session.rollback()


# Test configuration
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on location."""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration/ directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to tests that might take longer
        if any(keyword in item.name.lower() for keyword in ["scraper", "llm", "generation"]):
            item.add_marker(pytest.mark.slow)