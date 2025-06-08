"""
Test helpers and utilities for the job automation system tests.

Provides common test utilities, fixtures, and helper functions.
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
import faker
import random

from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.document import Document


class TestDataFactory:
    """Factory for creating test data objects."""
    
    def __init__(self):
        self.fake = faker.Faker()
    
    def create_user_data(self, **overrides) -> Dict[str, Any]:
        """Create realistic user test data."""
        base_data = {
            "email": self.fake.email(),
            "full_name": self.fake.name(),
            "phone_number": self.fake.phone_number(),
            "location": f"{self.fake.city()}, {self.fake.state_abbr()}",
            "skills": self.fake.random_elements(
                elements=["Python", "JavaScript", "React", "Django", "FastAPI", 
                         "PostgreSQL", "Docker", "AWS", "Git", "TypeScript"],
                length=random.randint(3, 7),
                unique=True
            ),
            "experience_years": random.randint(1, 15),
            "education": self.fake.random_element([
                "Bachelor's in Computer Science",
                "Master's in Software Engineering",
                "Bachelor's in Information Technology",
                "Self-taught"
            ]),
            "work_experience": [
                {
                    "title": "Software Engineer",
                    "company": self.fake.company(),
                    "duration": "2020-2023",
                    "description": "Developed web applications using modern technologies"
                }
            ],
            "job_preferences": {
                "job_types": ["full-time"],
                "industries": ["technology", "software"],
                "remote_preference": "hybrid",
                "salary_range": [80000, 150000]
            }
        }
        base_data.update(overrides)
        return base_data
    
    def create_job_data(self, **overrides) -> Dict[str, Any]:
        """Create realistic job posting test data."""
        base_data = {
            "title": self.fake.job(),
            "company": self.fake.company(),
            "location": f"{self.fake.city()}, {self.fake.state_abbr()}",
            "job_type": self.fake.random_element(["full-time", "part-time", "contract"]),
            "salary_min": random.randint(60000, 120000),
            "salary_max": random.randint(120000, 200000),
            "description": self.fake.text(max_nb_chars=1000),
            "requirements": self.fake.random_elements(
                elements=["Python", "JavaScript", "React", "SQL", "Communication"],
                length=random.randint(3, 6),
                unique=True
            ),
            "url": self.fake.url(),
            "source": self.fake.random_element(["linkedin", "indeed", "company_website"]),
            "is_active": True
        }
        base_data.update(overrides)
        return base_data
    
    def create_application_data(self, **overrides) -> Dict[str, Any]:
        """Create application test data."""
        base_data = {
            "status": self.fake.random_element([
                "pending", "interview_scheduled", "rejected", "offer_received"
            ]),
            "application_method": self.fake.random_element(["automated", "manual"]),
            "notes": self.fake.text(max_nb_chars=200),
            "applied_at": self.fake.date_time_between(start_date="-30d", end_date="now")
        }
        base_data.update(overrides)
        return base_data
    
    def create_document_data(self, **overrides) -> Dict[str, Any]:
        """Create document test data."""
        base_data = {
            "document_type": self.fake.random_element(["resume", "cover_letter"]),
            "content": self.fake.text(max_nb_chars=2000),
            "template_used": self.fake.random_element(["modern", "classic", "professional"]),
            "title": f"My {self.fake.random_element(['Resume', 'Cover Letter'])}",
            "is_active": True
        }
        base_data.update(overrides)
        return base_data


class MockServiceManager:
    """Manager for creating and configuring mock services."""
    
    @staticmethod
    def create_mock_llm_service(service_type: str) -> AsyncMock:
        """Create mock LLM service (Phi-3, Gemma, Mistral)."""
        mock_service = AsyncMock()
        
        if service_type == "phi3":
            mock_service.generate_resume.return_value = {
                "content": "Mock generated resume content",
                "success": True,
                "model_used": "phi3-mini",
                "generation_time": 1.5
            }
            mock_service.generate_cover_letter.return_value = {
                "content": "Mock generated cover letter content",
                "success": True,
                "model_used": "phi3-mini",
                "generation_time": 1.2
            }
        
        elif service_type == "gemma":
            mock_service.analyze_job_match.return_value = {
                "relevance_score": 0.85,
                "matching_skills": ["Python", "FastAPI"],
                "missing_skills": ["Kubernetes"],
                "analysis": "Good match for candidate profile",
                "success": True,
                "model_used": "gemma-7b"
            }
        
        elif service_type == "mistral":
            mock_service.fill_application_form.return_value = {
                "success": True,
                "application_id": "MOCK-12345",
                "form_data": {"name": "Test User", "email": "test@example.com"},
                "model_used": "mistral-7b"
            }
        
        mock_service.health_check.return_value = True
        mock_service.is_healthy.return_value = True
        
        return mock_service
    
    @staticmethod
    def create_mock_scraper_service() -> MagicMock:
        """Create mock web scraper service."""
        mock_scraper = MagicMock()
        mock_scraper.scrape_jobs.return_value = [
            {
                "title": "Mock Job 1",
                "company": "Mock Company 1",
                "location": "Mock City, MC",
                "url": "https://mock1.com/job",
                "description": "Mock job description 1"
            },
            {
                "title": "Mock Job 2", 
                "company": "Mock Company 2",
                "location": "Remote",
                "url": "https://mock2.com/job",
                "description": "Mock job description 2"
            }
        ]
        return mock_scraper
    
    @staticmethod
    def create_mock_notification_service() -> AsyncMock:
        """Create mock notification service."""
        mock_service = AsyncMock()
        mock_service.send_email.return_value = {"success": True, "message_id": "mock123"}
        mock_service.send_push_notification.return_value = {"success": True, "id": "push123"}
        mock_service.send_welcome_email.return_value = {"success": True}
        mock_service.send_job_alert_email.return_value = {"success": True}
        mock_service.send_application_confirmation.return_value = {"success": True}
        return mock_service


class DatabaseTestHelper:
    """Helper for database testing operations."""
    
    @staticmethod
    async def create_test_user(db_session, **kwargs) -> User:
        """Create a test user in the database."""
        factory = TestDataFactory()
        user_data = factory.create_user_data(**kwargs)
        
        user = User(
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password="hashed_test_password",
            phone_number=user_data.get("phone_number"),
            location=user_data.get("location"),
            skills=user_data.get("skills", []),
            experience_years=user_data.get("experience_years", 3),
            education=user_data.get("education"),
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @staticmethod
    async def create_test_job(db_session, **kwargs) -> Job:
        """Create a test job in the database."""
        factory = TestDataFactory()
        job_data = factory.create_job_data(**kwargs)
        
        job = Job(
            title=job_data["title"],
            company=job_data["company"],
            location=job_data["location"],
            job_type=job_data.get("job_type", "full-time"),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            description=job_data["description"],
            requirements=job_data.get("requirements", []),
            url=job_data["url"],
            source=job_data.get("source", "test"),
            is_active=job_data.get("is_active", True)
        )
        
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        return job
    
    @staticmethod
    async def create_test_application(db_session, user: User, job: Job, **kwargs) -> Application:
        """Create a test application in the database."""
        factory = TestDataFactory()
        app_data = factory.create_application_data(**kwargs)
        
        application = Application(
            user_id=user.id,
            job_id=job.id,
            status=app_data.get("status", "pending"),
            application_method=app_data.get("application_method", "manual"),
            notes=app_data.get("notes"),
            applied_at=app_data.get("applied_at")
        )
        
        db_session.add(application)
        await db_session.commit()
        await db_session.refresh(application)
        return application
    
    @staticmethod
    async def cleanup_test_data(db_session, models: List[Any]):
        """Clean up test data from database."""
        for model_instance in models:
            await db_session.delete(model_instance)
        await db_session.commit()


class APITestHelper:
    """Helper for API testing operations."""
    
    @staticmethod
    async def login_user(async_client, email: str, password: str) -> Dict[str, str]:
        """Login user and return authentication headers."""
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if login_response.status_code == 200:
            tokens = login_response.json()
            return {"Authorization": f"Bearer {tokens['access_token']}"}
        else:
            raise Exception(f"Login failed: {login_response.text}")
    
    @staticmethod
    def assert_response_structure(response_data: Dict, expected_fields: List[str]):
        """Assert that response contains expected fields."""
        for field in expected_fields:
            assert field in response_data, f"Missing field: {field}"
    
    @staticmethod
    def assert_pagination_structure(response_data: Dict):
        """Assert that response contains proper pagination structure."""
        assert "pagination" in response_data
        pagination = response_data["pagination"]
        required_fields = ["limit", "offset", "total_count", "has_next", "has_previous"]
        
        for field in required_fields:
            assert field in pagination, f"Missing pagination field: {field}"
    
    @staticmethod
    async def make_authenticated_request(async_client, method: str, url: str, 
                                       auth_headers: Dict[str, str], **kwargs):
        """Make authenticated API request."""
        if method.upper() == "GET":
            return await async_client.get(url, headers=auth_headers, **kwargs)
        elif method.upper() == "POST":
            return await async_client.post(url, headers=auth_headers, **kwargs)
        elif method.upper() == "PUT":
            return await async_client.put(url, headers=auth_headers, **kwargs)
        elif method.upper() == "DELETE":
            return await async_client.delete(url, headers=auth_headers, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")


class FileTestHelper:
    """Helper for file testing operations."""
    
    @staticmethod
    def create_temp_file(content: bytes = b"test content", suffix: str = ".txt") -> str:
        """Create temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            return tmp.name
    
    @staticmethod
    def create_mock_upload_file(filename: str, content: bytes, content_type: str):
        """Create mock file upload object."""
        return {
            "filename": filename,
            "content": content,
            "content_type": content_type
        }
    
    @staticmethod
    def cleanup_temp_files(file_paths: List[str]):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass


class PerformanceTestHelper:
    """Helper for performance testing operations."""
    
    @staticmethod
    async def measure_response_time(coro):
        """Measure response time of async operation."""
        import time
        start_time = time.time()
        result = await coro
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    async def run_concurrent_operations(operations: List, max_concurrent: int = 10):
        """Run operations concurrently with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_operation(op):
            async with semaphore:
                return await op
        
        return await asyncio.gather(*[bounded_operation(op) for op in operations])
    
    @staticmethod
    def analyze_response_times(response_times: List[float]) -> Dict[str, float]:
        """Analyze response time statistics."""
        import statistics
        
        return {
            "min": min(response_times),
            "max": max(response_times),
            "mean": statistics.mean(response_times),
            "median": statistics.median(response_times),
            "p95": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
            "p99": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)
        }


class SecurityTestHelper:
    """Helper for security testing operations."""
    
    @staticmethod
    def get_malicious_payloads(payload_type: str) -> List[str]:
        """Get common malicious payloads for testing."""
        payloads = {
            "xss": [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>"
            ],
            "sql_injection": [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; UPDATE users SET admin=true; --",
                "' UNION SELECT * FROM users --"
            ],
            "path_traversal": [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "....//....//....//etc/passwd"
            ],
            "command_injection": [
                "; ls -la",
                "| cat /etc/passwd",
                "&& rm -rf /",
                "`cat /etc/passwd`"
            ]
        }
        return payloads.get(payload_type, [])
    
    @staticmethod
    def generate_oversized_data(size_mb: int) -> str:
        """Generate oversized data for testing input limits."""
        return "A" * (size_mb * 1024 * 1024)
    
    @staticmethod
    def create_invalid_jwt_tokens() -> List[str]:
        """Create various invalid JWT tokens for testing."""
        return [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "Bearer",
            "malformed_token_without_dots"
        ]


class ValidationTestHelper:
    """Helper for input validation testing."""
    
    @staticmethod
    def get_invalid_email_formats() -> List[str]:
        """Get list of invalid email formats."""
        return [
            "invalid-email",
            "@example.com",
            "user@",
            "user..double.dot@example.com",
            "user@.com",
            "user@com",
            "user name@example.com",
            "user@example..com"
        ]
    
    @staticmethod
    def get_invalid_phone_formats() -> List[str]:
        """Get list of invalid phone number formats."""
        return [
            "123",
            "abc-def-ghij",
            "123-45-67",
            "++1234567890",
            "phone_number",
            "1234567890123456789012345"
        ]
    
    @staticmethod
    def get_boundary_test_values() -> Dict[str, List[Any]]:
        """Get boundary test values for different data types."""
        return {
            "integers": [-1, 0, 1, 2147483647, 2147483648, -2147483648, -2147483649],
            "strings": ["", "a", "a" * 255, "a" * 256, "a" * 1000],
            "floats": [-1.0, 0.0, 1.0, 3.14159, float('inf'), float('-inf')],
            "dates": [
                "2024-01-01",
                "1900-01-01", 
                "2100-12-31",
                "invalid-date",
                "2024-13-01",  # Invalid month
                "2024-02-30"   # Invalid day
            ]
        }


# Test decorators for common test patterns
def skip_if_no_database(func):
    """Skip test if database is not available."""
    return pytest.mark.skipif(
        not os.getenv("DATABASE_URL"),
        reason="Database not available"
    )(func)


def skip_if_no_llm_services(func):
    """Skip test if LLM services are not available."""
    return pytest.mark.skipif(
        not all([
            os.getenv("PHI3_SERVICE_URL"),
            os.getenv("GEMMA_SERVICE_URL"),
            os.getenv("MISTRAL_SERVICE_URL")
        ]),
        reason="LLM services not available"
    )(func)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Retry test on failure."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(delay)
        return wrapper
    return decorator


# Common test data constants
TEST_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Vue.js", "Angular",
    "Django", "FastAPI", "Flask", "Node.js", "Express.js",
    "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "Git", "CI/CD", "Jenkins", "GitHub Actions",
    "Machine Learning", "Data Science", "AI"
]

TEST_JOB_TITLES = [
    "Software Engineer", "Senior Software Engineer", "Full Stack Developer",
    "Frontend Developer", "Backend Developer", "DevOps Engineer",
    "Data Scientist", "Machine Learning Engineer", "Product Manager",
    "QA Engineer", "System Administrator", "Cloud Architect"
]

TEST_COMPANIES = [
    "TechCorp", "InnovateLabs", "DataSystems", "CloudWorks", "StartupXYZ",
    "MegaTech", "SoftwareHouse", "DigitalSolutions", "TechInnovators",
    "FutureTech", "CodeCrafters", "SystemBuilders"
]

TEST_LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Boston, MA", "Los Angeles, CA", "Chicago, IL", "Denver, CO",
    "Remote", "Hybrid", "Portland, OR", "Atlanta, GA"
]
