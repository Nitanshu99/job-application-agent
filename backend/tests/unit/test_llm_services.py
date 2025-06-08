"""
Unit tests for LLM services (Phi-3, Gemma, Mistral).

Tests AI model integrations for document generation, job matching, and application automation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.llm.phi3_service import Phi3Service
from app.services.llm.gemma_service import GemmaService
from app.services.llm.mistral_service import MistralService
from app.services.llm.model_manager import ModelManager
from app.core.exceptions import ModelServiceError, ModelUnavailableError


class TestPhi3Service:
    """Test suite for Phi-3 document generation service."""

    @pytest.fixture
    def phi3_service(self):
        """Create Phi3Service instance for testing."""
        return Phi3Service(base_url="http://localhost:8001")

    @pytest.fixture
    def sample_user_profile(self):
        """Sample user profile for document generation."""
        return {
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1555123456",
            "location": "San Francisco, CA",
            "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
            "experience_years": 5,
            "work_experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "TechCorp",
                    "duration": "2021-2024",
                    "description": "Led development of microservices architecture"
                }
            ],
            "education": "Bachelor's in Computer Science",
            "certifications": ["AWS Certified Developer"]
        }

    @pytest.fixture
    def sample_job_description(self):
        """Sample job description for document tailoring."""
        return {
            "title": "Senior Backend Developer",
            "company": "Innovation Labs",
            "description": "Join our team to build scalable backend systems...",
            "requirements": [
                "5+ years Python experience",
                "FastAPI or Django experience",
                "Cloud platform experience",
                "Strong problem-solving skills"
            ]
        }

    @patch('httpx.AsyncClient.post')
    async def test_generate_resume_success(self, mock_post, phi3_service, sample_user_profile, sample_job_description):
        """Test successful resume generation."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Generated resume content with tailored skills and experience...",
            "success": True,
            "model_used": "phi3-mini",
            "generation_time": 2.5
        }
        mock_post.return_value = mock_response
        
        # Call service method
        result = await phi3_service.generate_resume(sample_user_profile, sample_job_description)
        
        # Assertions
        assert result["success"] is True
        assert "content" in result
        assert result["model_used"] == "phi3-mini"
        mock_post.assert_called_once()

    @patch('httpx.AsyncClient.post')
    async def test_generate_cover_letter_success(self, mock_post, phi3_service, sample_user_profile, sample_job_description):
        """Test successful cover letter generation."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Dear Hiring Manager, I am writing to express my interest...",
            "success": True,
            "model_used": "phi3-mini",
            "generation_time": 1.8
        }
        mock_post.return_value = mock_response
        
        # Call service method
        result = await phi3_service.generate_cover_letter(sample_user_profile, sample_job_description)
        
        # Assertions
        assert result["success"] is True
        assert "Dear Hiring Manager" in result["content"]
        assert result["model_used"] == "phi3-mini"

    @patch('httpx.AsyncClient.post')
    async def test_generate_resume_service_error(self, mock_post, phi3_service, sample_user_profile, sample_job_description):
        """Test resume generation with service error."""
        # Mock error response
        mock_post.side_effect = httpx.RequestError("Connection failed")
        
        # Should raise ModelServiceError
        with pytest.raises(ModelServiceError):
            await phi3_service.generate_resume(sample_user_profile, sample_job_description)

    @patch('httpx.AsyncClient.post')
    async def test_generate_resume_model_error(self, mock_post, phi3_service, sample_user_profile, sample_job_description):
        """Test resume generation with model error response."""
        # Mock error response from model
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "success": False,
            "error": "Model generation failed",
            "model_used": "phi3-mini"
        }
        mock_post.return_value = mock_response
        
        # Should raise ModelServiceError
        with pytest.raises(ModelServiceError):
            await phi3_service.generate_resume(sample_user_profile, sample_job_description)

    @patch('httpx.AsyncClient.get')
    async def test_health_check_healthy(self, mock_get, phi3_service):
        """Test health check when service is healthy."""
        # Mock healthy response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "model": "phi3-mini"}
        mock_get.return_value = mock_response
        
        # Call service method
        is_healthy = await phi3_service.health_check()
        
        # Should be healthy
        assert is_healthy is True

    @patch('httpx.AsyncClient.get')
    async def test_health_check_unhealthy(self, mock_get, phi3_service):
        """Test health check when service is unhealthy."""
        # Mock unhealthy response
        mock_get.side_effect = httpx.RequestError("Connection failed")
        
        # Call service method
        is_healthy = await phi3_service.health_check()
        
        # Should be unhealthy
        assert is_healthy is False


class TestGemmaService:
    """Test suite for Gemma job matching service."""

    @pytest.fixture
    def gemma_service(self):
        """Create GemmaService instance for testing."""
        return GemmaService(base_url="http://localhost:8002")

    @pytest.fixture
    def sample_user_skills(self):
        """Sample user skills for job matching."""
        return ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "React"]

    @pytest.fixture
    def sample_job_posting(self):
        """Sample job posting for analysis."""
        return {
            "title": "Full Stack Developer",
            "company": "TechStartup",
            "description": "We're looking for a full stack developer with Python and React experience...",
            "requirements": [
                "3+ years Python experience",
                "React and JavaScript proficiency",
                "Database design experience",
                "Cloud platform knowledge"
            ],
            "location": "San Francisco, CA",
            "salary_range": [90000, 130000]
        }

    @patch('httpx.AsyncClient.post')
    async def test_analyze_job_match_success(self, mock_post, gemma_service, sample_user_skills, sample_job_posting):
        """Test successful job matching analysis."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "relevance_score": 0.85,
            "matching_skills": ["Python", "React"],
            "missing_skills": ["Kubernetes"],
            "analysis": "Strong match - candidate has most required skills",
            "recommendations": ["Consider learning Kubernetes"],
            "success": True,
            "model_used": "gemma-7b"
        }
        mock_post.return_value = mock_response
        
        # Call service method
        result = await gemma_service.analyze_job_match(sample_user_skills, sample_job_posting)
        
        # Assertions
        assert result["success"] is True
        assert result["relevance_score"] == 0.85
        assert "Python" in result["matching_skills"]
        assert "Kubernetes" in result["missing_skills"]

    @patch('httpx.AsyncClient.post')
    async def test_analyze_multiple_jobs(self, mock_post, gemma_service, sample_user_skills):
        """Test analyzing multiple job postings."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_analyses": [
                {"job_id": 1, "relevance_score": 0.9, "ranking": 1},
                {"job_id": 2, "relevance_score": 0.7, "ranking": 2},
                {"job_id": 3, "relevance_score": 0.6, "ranking": 3}
            ],
            "success": True,
            "model_used": "gemma-7b"
        }
        mock_post.return_value = mock_response
        
        jobs = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        # Call service method
        result = await gemma_service.analyze_multiple_jobs(sample_user_skills, jobs)
        
        # Assertions
        assert result["success"] is True
        assert len(result["job_analyses"]) == 3
        assert result["job_analyses"][0]["ranking"] == 1

    @patch('httpx.AsyncClient.post')
    async def test_extract_job_requirements(self, mock_post, gemma_service, sample_job_posting):
        """Test extracting structured requirements from job description."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "structured_requirements": {
                "technical_skills": ["Python", "React", "PostgreSQL"],
                "soft_skills": ["Communication", "Problem-solving"],
                "experience_level": "Mid-level (3-5 years)",
                "education": "Bachelor's degree preferred",
                "certifications": []
            },
            "success": True,
            "model_used": "gemma-7b"
        }
        mock_post.return_value = mock_response
        
        # Call service method
        result = await gemma_service.extract_requirements(sample_job_posting["description"])
        
        # Assertions
        assert result["success"] is True
        assert "technical_skills" in result["structured_requirements"]
        assert "Python" in result["structured_requirements"]["technical_skills"]


class TestMistralService:
    """Test suite for Mistral application automation service."""

    @pytest.fixture
    def mistral_service(self):
        """Create MistralService instance for testing."""
        return MistralService(base_url="http://localhost:8003")

    @pytest.fixture
    def sample_application_form(self):
        """Sample application form data."""
        return {
            "form_url": "https://company.com/apply/123",
            "form_fields": {
                "name": {"type": "text", "required": True},
                "email": {"type": "email", "required": True},
                "phone": {"type": "tel", "required": True},
                "cover_letter": {"type": "textarea", "required": False},
                "resume": {"type": "file", "required": True}
            }
        }

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for form filling."""
        return {
            "full_name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+1555987654",
            "resume_path": "/path/to/resume.pdf",
            "cover_letter_content": "Dear Hiring Manager..."
        }

    @patch('httpx.AsyncClient.post')
    async def test_fill_application_form_success(self, mock_post, mistral_service, sample_application_form, sample_user_data):
        """Test successful application form filling."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "form_data": {
                "name": "Jane Smith",
                "email": "jane.smith@example.com",
                "phone": "+1555987654"
            },
            "application_id": "APP-12345",
            "submission_status": "submitted",
            "model_used": "mistral-7b"
        }
        mock_post.return_value = mock_response
        
        # Call service method
        result = await mistral_service.fill_application_form(sample_application_form, sample_user_data)
        
        # Assertions
        assert result["success"] is True
        assert result["application_id"] == "APP-12345"
        assert result["form_data"]["name"] == "Jane Smith"

    @patch('httpx.AsyncClient.post')
    async def test_generate_application_answers(self, mock_post, mistral_service, sample_user_data):
        """Test generating answers for application questions."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "answers": {
                "why_interested": "I am excited about this opportunity because...",
                "experience_relevant": "My 5 years of experience in Python development...",
                "salary_expectations": "Based on my experience and market research..."
            },
            "success": True,
            "model_used": "mistral-7b"
        }
        mock_post.return_value = mock_response
        
        questions = [
            "Why are you interested in this position?",
            "How is your experience relevant to this role?",
            "What are your salary expectations?"
        ]
        
        # Call service method
        result = await mistral_service.generate_application_answers(questions, sample_user_data)
        
        # Assertions
        assert result["success"] is True
        assert len(result["answers"]) == 3
        assert "excited about this opportunity" in result["answers"]["why_interested"]

    @patch('httpx.AsyncClient.post')
    async def test_validate_application_data(self, mock_post, mistral_service, sample_application_form, sample_user_data):
        """Test validating application data before submission."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "is_valid": True,
            "validation_results": {
                "required_fields_complete": True,
                "email_format_valid": True,
                "phone_format_valid": True,
                "missing_fields": []
            },
            "confidence_score": 0.95,
            "success": True,
            "model_used": "mistral-7b"
        }
        mock_post.return_value = mock_response
        
        # Call service method
        result = await mistral_service.validate_application_data(sample_application_form, sample_user_data)
        
        # Assertions
        assert result["success"] is True
        assert result["is_valid"] is True
        assert result["validation_results"]["required_fields_complete"] is True

    @patch('httpx.AsyncClient.post')
    async def test_application_submission_error(self, mock_post, mistral_service, sample_application_form, sample_user_data):
        """Test handling application submission errors."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Required field missing: phone number",
            "error_code": "MISSING_REQUIRED_FIELD",
            "model_used": "mistral-7b"
        }
        mock_post.return_value = mock_response
        
        # Should raise ModelServiceError
        with pytest.raises(ModelServiceError):
            await mistral_service.fill_application_form(sample_application_form, sample_user_data)


class TestModelManager:
    """Test suite for ModelManager service coordination."""

    @pytest.fixture
    def model_manager(self):
        """Create ModelManager instance for testing."""
        return ModelManager()

    @pytest.fixture
    def mock_services(self, mock_phi3_service, mock_gemma_service, mock_mistral_service):
        """Mock all LLM services."""
        return {
            "phi3": mock_phi3_service,
            "gemma": mock_gemma_service,
            "mistral": mock_mistral_service
        }

    async def test_health_check_all_services(self, model_manager, mock_services):
        """Test health check for all services."""
        # Mock all services as healthy
        for service in mock_services.values():
            service.health_check.return_value = True
        
        # Patch the services in model manager
        with patch.object(model_manager, 'services', mock_services):
            health_status = await model_manager.check_all_services_health()
        
        # All services should be healthy
        assert health_status["phi3"] is True
        assert health_status["gemma"] is True
        assert health_status["mistral"] is True
        assert health_status["all_healthy"] is True

    async def test_health_check_one_service_down(self, model_manager, mock_services):
        """Test health check with one service down."""
        # Mock one service as unhealthy
        mock_services["phi3"].health_check.return_value = False
        mock_services["gemma"].health_check.return_value = True
        mock_services["mistral"].health_check.return_value = True
        
        # Patch the services in model manager
        with patch.object(model_manager, 'services', mock_services):
            health_status = await model_manager.check_all_services_health()
        
        # One service should be down
        assert health_status["phi3"] is False
        assert health_status["gemma"] is True
        assert health_status["mistral"] is True
        assert health_status["all_healthy"] is False

    async def test_get_available_models(self, model_manager, mock_services):
        """Test getting list of available models."""
        # Mock all services as healthy
        for service in mock_services.values():
            service.health_check.return_value = True
        
        # Patch the services in model manager
        with patch.object(model_manager, 'services', mock_services):
            available_models = await model_manager.get_available_models()
        
        # Should return all models
        assert "phi3-mini" in available_models
        assert "gemma-7b" in available_models
        assert "mistral-7b" in available_models

    async def test_sequential_model_usage(self, model_manager, mock_services):
        """Test sequential usage of models for complete workflow."""
        # Mock successful responses from all services
        mock_services["gemma"].analyze_job_match.return_value = {
            "relevance_score": 0.85,
            "success": True
        }
        mock_services["phi3"].generate_resume.return_value = {
            "content": "Generated resume",
            "success": True
        }
        mock_services["mistral"].fill_application_form.return_value = {
            "application_id": "APP-123",
            "success": True
        }
        
        # Patch the services in model manager
        with patch.object(model_manager, 'services', mock_services):
            # Test complete workflow
            job_analysis = await model_manager.analyze_job({}, {})
            resume = await model_manager.generate_resume({}, {})
            application = await model_manager.submit_application({}, {})
        
        # All steps should succeed
        assert job_analysis["success"] is True
        assert resume["success"] is True
        assert application["success"] is True

    async def test_service_failover(self, model_manager, mock_services):
        """Test failover when primary service is unavailable."""
        # Mock primary service as unavailable
        mock_services["phi3"].health_check.return_value = False
        mock_services["phi3"].generate_resume.side_effect = ModelUnavailableError("Service down")
        
        # Mock backup service
        backup_service = AsyncMock()
        backup_service.generate_resume.return_value = {
            "content": "Backup generated resume",
            "success": True,
            "model_used": "backup-model"
        }
        
        # Test failover mechanism
        with patch.object(model_manager, 'get_backup_service', return_value=backup_service):
            result = await model_manager.generate_resume_with_failover({}, {})
        
        # Should use backup service
        assert result["success"] is True
        assert result["model_used"] == "backup-model"

    async def test_model_load_balancing(self, model_manager):
        """Test load balancing between multiple model instances."""
        # Mock multiple instances of the same model
        instance1 = AsyncMock()
        instance2 = AsyncMock()
        
        instance1.health_check.return_value = True
        instance2.health_check.return_value = True
        
        instances = [instance1, instance2]
        
        with patch.object(model_manager, 'get_model_instances', return_value=instances):
            # Make multiple requests
            for i in range(10):
                await model_manager.generate_with_load_balancing("phi3", {}, {})
        
        # Both instances should have been used
        assert instance1.generate_resume.call_count > 0
        assert instance2.generate_resume.call_count > 0
