"""
Unit tests for document service functionality.

Tests document generation, management, templates, and file operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from sqlalchemy.ext.asyncio import AsyncSession
import tempfile
import os
from datetime import datetime

from app.models.document import Document
from app.models.job import Job
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.core.exceptions import DocumentNotFoundError, DocumentGenerationError


class TestDocumentService:
    """Test suite for DocumentService class."""

    @pytest.fixture
    def document_service(self):
        """Create DocumentService instance for testing."""
        return DocumentService()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_user_profile(self):
        """Sample user profile for document generation."""
        return {
            "full_name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone_number": "+1555987654",
            "location": "Seattle, WA",
            "skills": ["Python", "React", "PostgreSQL", "AWS"],
            "experience_years": 4,
            "work_experience": [
                {
                    "title": "Software Engineer",
                    "company": "TechStartup",
                    "duration": "2022-2024",
                    "description": "Developed full-stack web applications using Python and React"
                },
                {
                    "title": "Junior Developer", 
                    "company": "WebAgency",
                    "duration": "2020-2022",
                    "description": "Built responsive websites and web applications"
                }
            ],
            "education": "Bachelor of Science in Computer Science",
            "certifications": ["AWS Certified Developer", "React Developer Certification"]
        }

    @pytest.fixture
    def sample_job_posting(self):
        """Sample job posting for document tailoring."""
        return {
            "title": "Senior Full Stack Developer",
            "company": "InnovativeTech",
            "description": "Join our team to build next-generation web applications...",
            "requirements": [
                "4+ years of web development experience",
                "Proficiency in Python and modern JavaScript frameworks",
                "Experience with cloud platforms (AWS/Azure)",
                "Strong problem-solving and communication skills"
            ],
            "location": "San Francisco, CA",
            "salary_range": [110000, 160000]
        }

    @pytest.fixture
    def sample_document_create(self, test_user, test_job):
        """Sample document creation data."""
        return DocumentCreate(
            user_id=test_user.id,
            job_id=test_job.id,
            document_type="resume",
            content="Sample resume content...",
            template_used="modern_template",
            title="My Resume for Senior Developer Position"
        )

    async def test_create_document_success(self, document_service, mock_db_session, sample_document_create):
        """Test successful document creation."""
        # Mock document creation
        mock_document = MagicMock()
        mock_document.id = 1
        
        # Call service method
        created_document = await document_service.create_document(mock_db_session, sample_document_create)
        
        # Assertions
        assert created_document is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called()

    async def test_generate_resume_success(self, document_service, mock_db_session, sample_user_profile, sample_job_posting, mock_phi3_service):
        """Test successful resume generation."""
        # Mock Phi-3 service response
        mock_phi3_service.generate_resume.return_value = {
            "content": "Generated resume content tailored for Senior Full Stack Developer...",
            "success": True,
            "model_used": "phi3-mini",
            "generation_time": 2.1
        }
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            result = await document_service.generate_resume(
                mock_db_session,
                sample_user_profile,
                sample_job_posting,
                template="modern"
            )
        
        # Assertions
        assert result["success"] is True
        assert "Generated resume content" in result["content"]
        assert result["model_used"] == "phi3-mini"
        mock_phi3_service.generate_resume.assert_called_once()

    async def test_generate_cover_letter_success(self, document_service, mock_db_session, sample_user_profile, sample_job_posting, mock_phi3_service):
        """Test successful cover letter generation."""
        # Mock Phi-3 service response
        mock_phi3_service.generate_cover_letter.return_value = {
            "content": "Dear Hiring Manager, I am excited to apply for the Senior Full Stack Developer position...",
            "success": True,
            "model_used": "phi3-mini",
            "generation_time": 1.6
        }
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            result = await document_service.generate_cover_letter(
                mock_db_session,
                sample_user_profile,
                sample_job_posting,
                template="professional",
                tone="enthusiastic"
            )
        
        # Assertions
        assert result["success"] is True
        assert "Dear Hiring Manager" in result["content"]
        mock_phi3_service.generate_cover_letter.assert_called_once()

    async def test_generate_resume_service_error(self, document_service, mock_db_session, sample_user_profile, sample_job_posting, mock_phi3_service):
        """Test resume generation with service error."""
        # Mock service error
        mock_phi3_service.generate_resume.side_effect = Exception("Model service unavailable")
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            with pytest.raises(DocumentGenerationError):
                await document_service.generate_resume(
                    mock_db_session,
                    sample_user_profile,
                    sample_job_posting
                )

    async def test_get_document_by_id_found(self, document_service, mock_db_session, test_document):
        """Test getting document by ID when it exists."""
        # Mock database get
        mock_db_session.get.return_value = test_document
        
        # Call service method
        found_document = await document_service.get_document_by_id(mock_db_session, test_document.id)
        
        # Assertions
        assert found_document == test_document

    async def test_get_document_by_id_not_found(self, document_service, mock_db_session):
        """Test getting document by ID when it doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Call service method
        found_document = await document_service.get_document_by_id(mock_db_session, 999)
        
        # Should return None
        assert found_document is None

    async def test_update_document_success(self, document_service, mock_db_session, test_document):
        """Test successful document update."""
        # Mock database get
        mock_db_session.get.return_value = test_document
        
        update_data = DocumentUpdate(
            content="Updated document content with new information...",
            title="Updated Resume Title"
        )
        
        # Call service method
        updated_document = await document_service.update_document(
            mock_db_session,
            test_document.id,
            update_data
        )
        
        # Assertions
        assert updated_document.content == update_data.content
        assert updated_document.title == update_data.title
        mock_db_session.commit.assert_called_once()

    async def test_update_document_not_found(self, document_service, mock_db_session):
        """Test updating document that doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        update_data = DocumentUpdate(content="New content")
        
        # Should raise exception
        with pytest.raises(DocumentNotFoundError):
            await document_service.update_document(mock_db_session, 999, update_data)

    async def test_delete_document_success(self, document_service, mock_db_session, test_document):
        """Test successful document deletion."""
        # Mock database get
        mock_db_session.get.return_value = test_document
        
        # Call service method
        result = await document_service.delete_document(mock_db_session, test_document.id)
        
        # Assertions
        assert result is True
        mock_db_session.delete.assert_called_once_with(test_document)
        mock_db_session.commit.assert_called_once()

    async def test_get_user_documents(self, document_service, mock_db_session, test_user):
        """Test getting user's documents."""
        # Mock database query results
        mock_documents = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_documents
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        documents = await document_service.get_user_documents(
            mock_db_session,
            test_user.id,
            document_type="resume",
            limit=10,
            offset=0
        )
        
        # Assertions
        assert len(documents) == 3

    async def test_get_documents_by_type(self, document_service, mock_db_session, test_user):
        """Test getting documents filtered by type."""
        # Mock database query results
        mock_documents = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_documents
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        documents = await document_service.get_documents_by_type(
            mock_db_session,
            test_user.id,
            "cover_letter"
        )
        
        # Assertions
        assert len(documents) == 1

    @patch('app.utils.file_handling.save_file')
    async def test_save_document_file(self, mock_save_file, document_service, test_document):
        """Test saving document to file."""
        # Mock file saving
        mock_save_file.return_value = "/tmp/document_123.pdf"
        
        # Call service method
        file_path = await document_service.save_document_file(
            test_document,
            format="pdf",
            directory="/tmp"
        )
        
        # Assertions
        assert file_path == "/tmp/document_123.pdf"
        mock_save_file.assert_called_once()

    @patch('reportlab.pdfgen.canvas.Canvas')
    async def test_generate_pdf(self, mock_canvas, document_service, test_document):
        """Test PDF generation from document."""
        # Mock PDF canvas
        mock_canvas_instance = MagicMock()
        mock_canvas.return_value = mock_canvas_instance
        
        # Call service method
        pdf_content = await document_service.generate_pdf(test_document)
        
        # Assertions
        assert pdf_content is not None
        mock_canvas.assert_called_once()

    @patch('docx.Document')
    async def test_generate_docx(self, mock_docx_doc, document_service, test_document):
        """Test DOCX generation from document."""
        # Mock DOCX document
        mock_doc_instance = MagicMock()
        mock_docx_doc.return_value = mock_doc_instance
        
        # Call service method
        docx_content = await document_service.generate_docx(test_document)
        
        # Assertions
        assert docx_content is not None
        mock_docx_doc.assert_called_once()

    async def test_get_available_templates(self, document_service):
        """Test getting available document templates."""
        templates = await document_service.get_available_templates("resume")
        
        # Should return list of templates
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        # Check template structure
        template = templates[0]
        assert "name" in template
        assert "description" in template
        assert "preview_url" in template

    async def test_apply_template(self, document_service, sample_user_profile):
        """Test applying template to user data."""
        template_name = "modern"
        
        result = await document_service.apply_template(
            template_name,
            sample_user_profile,
            document_type="resume"
        )
        
        # Should return formatted content
        assert isinstance(result, str)
        assert len(result) > 0
        assert sample_user_profile["full_name"] in result

    async def test_optimize_for_ats(self, document_service, test_document):
        """Test ATS optimization of document."""
        keywords = ["Python", "React", "Full Stack", "AWS"]
        
        optimized = await document_service.optimize_for_ats(
            test_document.content,
            keywords,
            industry="technology"
        )
        
        # Should return optimization results
        assert "optimized_content" in optimized
        assert "ats_score" in optimized
        assert "suggestions" in optimized
        assert optimized["ats_score"] >= 0
        assert optimized["ats_score"] <= 100

    async def test_create_document_version(self, document_service, mock_db_session, test_document):
        """Test creating document version."""
        # Mock version creation
        original_content = test_document.content
        new_content = "Updated content for new version"
        
        version = await document_service.create_document_version(
            mock_db_session,
            test_document.id,
            new_content,
            "Updated with new experience"
        )
        
        # Assertions
        assert version is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    async def test_get_document_versions(self, document_service, mock_db_session, test_document):
        """Test getting document version history."""
        # Mock version history
        mock_versions = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_versions
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        versions = await document_service.get_document_versions(
            mock_db_session,
            test_document.id
        )
        
        # Assertions
        assert len(versions) == 2

    async def test_revert_to_version(self, document_service, mock_db_session, test_document):
        """Test reverting document to previous version."""
        # Mock database operations
        mock_db_session.get.return_value = test_document
        
        # Mock version data
        version_content = "Previous version content"
        
        # Call service method
        reverted_document = await document_service.revert_to_version(
            mock_db_session,
            test_document.id,
            version_id=1,
            version_content=version_content
        )
        
        # Assertions
        assert reverted_document.content == version_content
        mock_db_session.commit.assert_called()

    async def test_duplicate_document(self, document_service, mock_db_session, test_document, test_user):
        """Test duplicating existing document."""
        # Mock database operations
        mock_db_session.get.return_value = test_document
        
        # Call service method
        duplicated = await document_service.duplicate_document(
            mock_db_session,
            test_document.id,
            new_title="Copy of Original Document"
        )
        
        # Assertions
        assert duplicated is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    async def test_share_document(self, document_service, mock_db_session, test_document):
        """Test creating shareable link for document."""
        # Mock database operations
        mock_db_session.get.return_value = test_document
        
        # Call service method
        share_data = await document_service.create_share_link(
            mock_db_session,
            test_document.id,
            expiry_days=7,
            password_protected=False
        )
        
        # Assertions
        assert "share_token" in share_data
        assert "share_url" in share_data
        assert "expires_at" in share_data

    async def test_get_shared_document(self, document_service, mock_db_session):
        """Test accessing document via share link."""
        share_token = "test-share-token-123"
        
        # Mock shared document lookup
        mock_share = MagicMock()
        mock_share.document = MagicMock()
        mock_share.is_active = True
        mock_share.expires_at = datetime.now().timestamp() + 3600  # Not expired
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_share
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        document = await document_service.get_shared_document(mock_db_session, share_token)
        
        # Assertions
        assert document is not None

    async def test_get_document_analytics(self, document_service, mock_db_session, test_document):
        """Test getting document usage analytics."""
        # Mock analytics data
        analytics_data = {
            "views": 25,
            "downloads": 8,
            "shares": 3,
            "applications_used": 5,
            "last_viewed": datetime.now().isoformat()
        }
        
        with patch('app.services.document_service.DocumentService.calculate_analytics', return_value=analytics_data):
            analytics = await document_service.get_document_analytics(
                mock_db_session,
                test_document.id
            )
        
        # Assertions
        assert analytics["views"] == 25
        assert analytics["downloads"] == 8
        assert analytics["applications_used"] == 5

    async def test_batch_generate_documents(self, document_service, mock_db_session, test_user, mock_phi3_service):
        """Test batch generating documents for multiple jobs."""
        # Mock job data
        job_ids = [1, 2, 3]
        
        # Mock Phi-3 service responses
        mock_phi3_service.generate_resume.return_value = {
            "content": "Batch generated resume",
            "success": True
        }
        mock_phi3_service.generate_cover_letter.return_value = {
            "content": "Batch generated cover letter", 
            "success": True
        }
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            with patch('app.services.document_service.DocumentService.create_background_task') as mock_task:
                task_id = await document_service.batch_generate_documents(
                    mock_db_session,
                    test_user.id,
                    job_ids,
                    document_types=["resume", "cover_letter"],
                    template="modern"
                )
        
        # Assertions
        assert task_id is not None
        mock_task.assert_called_once()

    async def test_get_batch_generation_status(self, document_service, mock_db_session):
        """Test getting batch generation task status."""
        task_id = "batch-task-123"
        
        # Mock task status
        status_data = {
            "task_id": task_id,
            "status": "completed",
            "total_jobs": 3,
            "completed_jobs": 3,
            "failed_jobs": 0,
            "generated_documents": [1, 2, 3, 4, 5, 6]  # 2 docs per job
        }
        
        with patch('app.services.document_service.DocumentService.get_task_status', return_value=status_data):
            status = await document_service.get_batch_generation_status(task_id)
        
        # Assertions
        assert status["status"] == "completed"
        assert status["total_jobs"] == 3
        assert len(status["generated_documents"]) == 6

    async def test_compare_documents(self, document_service, test_document):
        """Test comparing two documents."""
        document1_content = "First document content with Python and React skills"
        document2_content = "Second document content with JavaScript and Node.js experience"
        
        comparison = await document_service.compare_documents(
            document1_content,
            document2_content,
            comparison_type="content"
        )
        
        # Assertions
        assert "similarity_score" in comparison
        assert "differences" in comparison
        assert "recommendations" in comparison
        assert 0 <= comparison["similarity_score"] <= 1

    async def test_get_document_feedback(self, document_service, test_document, mock_phi3_service):
        """Test getting AI feedback on document."""
        # Mock AI feedback
        mock_phi3_service.analyze_document.return_value = {
            "overall_score": 8.2,
            "strengths": ["Clear structure", "Quantified achievements", "Relevant skills"],
            "improvements": ["Add more keywords", "Include project details"],
            "ats_compatibility": 0.85,
            "readability_score": 7.5
        }
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            feedback = await document_service.get_ai_feedback(test_document.content)
        
        # Assertions
        assert feedback["overall_score"] == 8.2
        assert len(feedback["strengths"]) > 0
        assert len(feedback["improvements"]) > 0
        assert 0 <= feedback["ats_compatibility"] <= 1

    async def test_extract_keywords_from_document(self, document_service):
        """Test extracting keywords from document content."""
        content = """
        Experienced Software Engineer with 5+ years developing web applications.
        Proficient in Python, JavaScript, React, and Node.js.
        Strong background in database design, API development, and cloud deployment.
        """
        
        keywords = await document_service.extract_keywords(content, limit=10)
        
        # Assertions
        assert len(keywords) <= 10
        assert any("python" in kw.lower() for kw in keywords)
        assert any("javascript" in kw.lower() for kw in keywords)

    async def test_calculate_document_metrics(self, document_service):
        """Test calculating document quality metrics."""
        content = """
        Senior Software Engineer with 5+ years of experience developing scalable web applications.
        Led a team of 4 developers and increased application performance by 40%.
        Expertise in Python, React, and AWS with proven track record of delivering projects on time.
        """
        
        metrics = await document_service.calculate_metrics(content)
        
        # Assertions
        assert "word_count" in metrics
        assert "readability_score" in metrics
        assert "keyword_density" in metrics
        assert "quantified_achievements" in metrics
        assert metrics["word_count"] > 0

    async def test_document_spell_check(self, document_service):
        """Test spell checking document content."""
        content_with_errors = "Experinced Sofware Engneer with excelent comunication skils."
        
        with patch('spellchecker.SpellChecker') as mock_spell:
            mock_spell.return_value.unknown.return_value = {"Experinced", "Sofware", "Engneer", "excelent", "comunication", "skils"}
            mock_spell.return_value.correction.side_effect = lambda x: {
                "Experinced": "Experienced",
                "Sofware": "Software", 
                "Engneer": "Engineer",
                "excelent": "excellent",
                "comunication": "communication",
                "skils": "skills"
            }.get(x, x)
            
            spell_check = await document_service.spell_check(content_with_errors)
        
        # Assertions
        assert "errors_found" in spell_check
        assert "corrected_text" in spell_check
        assert "suggestions" in spell_check
        assert len(spell_check["errors_found"]) > 0
