"""
Integration tests for documents API endpoints.

Tests resume and cover letter generation, document management, and templates.
"""

import pytest
from unittest.mock import patch, mock_open
from httpx import AsyncClient
import tempfile
import os

from app.models.document import Document
from app.models.job import Job
from app.models.user import User


class TestDocumentsAPI:
    """Integration tests for document endpoints."""

    async def test_generate_resume_success(self, async_client: AsyncClient, auth_headers, test_job: Job, mock_phi3_service):
        """Test successful resume generation."""
        # Mock Phi-3 service response
        mock_phi3_service.generate_resume.return_value = {
            "content": "Generated resume content tailored for Software Engineer position...",
            "success": True,
            "model_used": "phi3-mini",
            "generation_time": 2.3
        }
        
        generate_data = {
            "job_id": test_job.id,
            "template": "modern",
            "include_cover_letter": False,
            "customizations": {
                "highlight_skills": ["Python", "FastAPI"],
                "emphasis": "technical_skills"
            }
        }
        
        with patch('app.services.document_service.DocumentService.generate_resume', return_value=mock_phi3_service.generate_resume.return_value):
            response = await async_client.post(
                "/api/v1/documents/resume/generate",
                json=generate_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["document_type"] == "resume"
            assert data["job_id"] == test_job.id
            assert "content" in data
            assert data["template_used"] == "modern"

    async def test_generate_cover_letter_success(self, async_client: AsyncClient, auth_headers, test_job: Job, mock_phi3_service):
        """Test successful cover letter generation."""
        # Mock Phi-3 service response
        mock_phi3_service.generate_cover_letter.return_value = {
            "content": "Dear Hiring Manager, I am writing to express my strong interest...",
            "success": True,
            "model_used": "phi3-mini",
            "generation_time": 1.8
        }
        
        generate_data = {
            "job_id": test_job.id,
            "template": "professional",
            "tone": "enthusiastic",
            "key_points": [
                "5 years of Python experience",
                "Strong problem-solving skills",
                "Team leadership experience"
            ]
        }
        
        with patch('app.services.document_service.DocumentService.generate_cover_letter', return_value=mock_phi3_service.generate_cover_letter.return_value):
            response = await async_client.post(
                "/api/v1/documents/cover-letter/generate",
                json=generate_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["document_type"] == "cover_letter"
            assert "Dear Hiring Manager" in data["content"]

    async def test_generate_both_documents(self, async_client: AsyncClient, auth_headers, test_job: Job, mock_phi3_service):
        """Test generating both resume and cover letter together."""
        # Mock both service responses
        mock_phi3_service.generate_resume.return_value = {
            "content": "Resume content...",
            "success": True
        }
        mock_phi3_service.generate_cover_letter.return_value = {
            "content": "Cover letter content...",
            "success": True
        }
        
        generate_data = {
            "job_id": test_job.id,
            "include_resume": True,
            "include_cover_letter": True,
            "template": "modern"
        }
        
        with patch('app.services.document_service.DocumentService.generate_documents_package') as mock_generate:
            mock_generate.return_value = {
                "resume": {"id": 1, "content": "Resume content...", "document_type": "resume"},
                "cover_letter": {"id": 2, "content": "Cover letter content...", "document_type": "cover_letter"}
            }
            
            response = await async_client.post(
                "/api/v1/documents/generate-package",
                json=generate_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "resume" in data
            assert "cover_letter" in data

    async def test_get_user_documents(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test getting user's documents."""
        response = await async_client.get(
            "/api/v1/documents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) >= 1

    async def test_get_documents_with_filters(self, async_client: AsyncClient, auth_headers):
        """Test getting documents with type filter."""
        params = {
            "document_type": "resume",
            "is_active": True,
            "limit": 10,
            "offset": 0
        }
        
        response = await async_client.get(
            "/api/v1/documents",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data

    async def test_get_document_by_id(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test getting specific document by ID."""
        response = await async_client.get(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id
        assert data["document_type"] == test_document.document_type

    async def test_get_document_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting non-existent document."""
        response = await async_client.get(
            "/api/v1/documents/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_update_document_content(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test updating document content."""
        update_data = {
            "content": "Updated resume content with new experience section...",
            "notes": "Added recent project experience"
        }
        
        response = await async_client.put(
            f"/api/v1/documents/{test_document.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Updated resume content" in data["content"]

    async def test_delete_document(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test deleting a document."""
        response = await async_client.delete(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"

    async def test_download_document_pdf(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test downloading document as PDF."""
        with patch('app.services.document_service.DocumentService.generate_pdf') as mock_pdf:
            mock_pdf.return_value = b"PDF content"
            
            response = await async_client.get(
                f"/api/v1/documents/{test_document.id}/download",
                params={"format": "pdf"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"

    async def test_download_document_docx(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test downloading document as DOCX."""
        with patch('app.services.document_service.DocumentService.generate_docx') as mock_docx:
            mock_docx.return_value = b"DOCX content"
            
            response = await async_client.get(
                f"/api/v1/documents/{test_document.id}/download",
                params={"format": "docx"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    async def test_upload_document(self, async_client: AsyncClient, auth_headers, temp_file):
        """Test uploading existing document."""
        with open(temp_file, "rb") as f:
            files = {"file": ("resume.pdf", f, "application/pdf")}
            data = {
                "document_type": "resume",
                "title": "My Existing Resume"
            }
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                files=files,
                data=data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["document_type"] == "resume"
            assert response_data["title"] == "My Existing Resume"

    async def test_upload_invalid_file_type(self, async_client: AsyncClient, auth_headers):
        """Test uploading invalid file type."""
        # Create a fake file with invalid extension
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"Invalid file content")
            tmp.flush()
            
            try:
                with open(tmp.name, "rb") as f:
                    files = {"file": ("document.txt", f, "text/plain")}
                    data = {"document_type": "resume"}
                    
                    response = await async_client.post(
                        "/api/v1/documents/upload",
                        files=files,
                        data=data,
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 400
            finally:
                os.unlink(tmp.name)

    async def test_get_available_templates(self, async_client: AsyncClient, auth_headers):
        """Test getting available document templates."""
        response = await async_client.get(
            "/api/v1/documents/templates",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0
        
        # Check template structure
        template = data["templates"][0]
        assert "name" in template
        assert "description" in template
        assert "preview_url" in template

    async def test_preview_template(self, async_client: AsyncClient, auth_headers):
        """Test previewing a template with sample data."""
        preview_data = {
            "template_name": "modern",
            "document_type": "resume",
            "sample_data": {
                "name": "John Doe",
                "email": "john@example.com",
                "skills": ["Python", "JavaScript"]
            }
        }
        
        response = await async_client.post(
            "/api/v1/documents/templates/preview",
            json=preview_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "preview_html" in data

    async def test_duplicate_document(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test duplicating an existing document."""
        duplicate_data = {
            "new_title": "Copy of Resume",
            "modify_for_job": None
        }
        
        response = await async_client.post(
            f"/api/v1/documents/{test_document.id}/duplicate",
            json=duplicate_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Copy of Resume"
        assert data["id"] != test_document.id

    async def test_get_document_versions(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test getting document version history."""
        response = await async_client.get(
            f"/api/v1/documents/{test_document.id}/versions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert isinstance(data["versions"], list)

    async def test_revert_document_version(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test reverting document to previous version."""
        # First, update the document to create a new version
        update_data = {"content": "New version content"}
        await async_client.put(
            f"/api/v1/documents/{test_document.id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Then revert to previous version
        revert_data = {"version_id": 1}
        
        response = await async_client.post(
            f"/api/v1/documents/{test_document.id}/revert",
            json=revert_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_share_document(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test creating shareable link for document."""
        share_data = {
            "expiry_days": 7,
            "password_protected": False,
            "allow_download": True
        }
        
        response = await async_client.post(
            f"/api/v1/documents/{test_document.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "share_url" in data
        assert "expires_at" in data

    async def test_access_shared_document(self, async_client: AsyncClient):
        """Test accessing document via share link."""
        share_token = "test-share-token-123"
        
        with patch('app.services.document_service.DocumentService.get_shared_document') as mock_shared:
            mock_shared.return_value = {
                "id": 1,
                "content": "Shared document content",
                "document_type": "resume"
            }
            
            response = await async_client.get(
                f"/api/v1/documents/shared/{share_token}"
            )
            
            assert response.status_code == 200

    async def test_get_document_analytics(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test getting document usage analytics."""
        response = await async_client.get(
            f"/api/v1/documents/{test_document.id}/analytics",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "downloads" in data
        assert "applications_used" in data

    async def test_batch_generate_documents(self, async_client: AsyncClient, auth_headers, test_job: Job, mock_phi3_service):
        """Test batch generating documents for multiple jobs."""
        # Mock service responses
        mock_phi3_service.generate_resume.return_value = {"content": "Resume", "success": True}
        mock_phi3_service.generate_cover_letter.return_value = {"content": "Cover letter", "success": True}
        
        batch_data = {
            "job_ids": [test_job.id],
            "document_types": ["resume", "cover_letter"],
            "template": "modern"
        }
        
        with patch('app.services.document_service.DocumentService.batch_generate') as mock_batch:
            mock_batch.return_value = {
                "task_id": "batch-123",
                "status": "processing",
                "jobs_count": 1
            }
            
            response = await async_client.post(
                "/api/v1/documents/batch-generate",
                json=batch_data,
                headers=auth_headers
            )
            
            assert response.status_code == 202  # Accepted for background processing
            data = response.json()
            assert "task_id" in data

    async def test_get_batch_generation_status(self, async_client: AsyncClient, auth_headers):
        """Test getting batch generation task status."""
        task_id = "batch-123"
        
        with patch('app.services.document_service.DocumentService.get_batch_status') as mock_status:
            mock_status.return_value = {
                "task_id": task_id,
                "status": "completed",
                "total_jobs": 5,
                "completed_jobs": 5,
                "failed_jobs": 0,
                "generated_documents": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            }
            
            response = await async_client.get(
                f"/api/v1/documents/batch-generate/{task_id}/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["total_jobs"] == 5

    async def test_optimize_document_for_ats(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test optimizing document for ATS (Applicant Tracking System)."""
        optimization_data = {
            "target_keywords": ["Python", "FastAPI", "microservices"],
            "industry": "technology",
            "job_title": "Senior Software Engineer"
        }
        
        with patch('app.services.document_service.DocumentService.optimize_for_ats') as mock_optimize:
            mock_optimize.return_value = {
                "optimized_content": "ATS-optimized content...",
                "ats_score": 85,
                "suggestions": ["Add more technical keywords", "Use standard section headers"]
            }
            
            response = await async_client.post(
                f"/api/v1/documents/{test_document.id}/optimize-ats",
                json=optimization_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "ats_score" in data
            assert "suggestions" in data

    async def test_compare_documents(self, async_client: AsyncClient, auth_headers, test_document: Document):
        """Test comparing two documents."""
        # Create another document for comparison
        with patch('app.services.document_service.DocumentService.create_document') as mock_create:
            mock_create.return_value = {"id": 2, "content": "Second document content"}
            
            compare_data = {
                "document_id_1": test_document.id,
                "document_id_2": 2,
                "comparison_type": "content"
            }
            
            with patch('app.services.document_service.DocumentService.compare_documents') as mock_compare:
                mock_compare.return_value = {
                    "similarity_score": 0.75,
                    "differences": ["Section order", "Skill emphasis"],
                    "recommendations": ["Consider merging skill sections"]
                }
                
                response = await async_client.post(
                    "/api/v1/documents/compare",
                    json=compare_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "similarity_score" in data
                assert "differences" in data

    async def test_document_ai_feedback(self, async_client: AsyncClient, auth_headers, test_document: Document, mock_phi3_service):
        """Test getting AI feedback on document."""
        # Mock AI feedback
        mock_phi3_service.analyze_document.return_value = {
            "overall_score": 8.5,
            "strengths": ["Clear structure", "Quantified achievements"],
            "improvements": ["Add more technical details", "Include project outcomes"],
            "ats_compatibility": 0.9
        }
        
        with patch('app.services.document_service.DocumentService.get_ai_feedback', return_value=mock_phi3_service.analyze_document.return_value):
            response = await async_client.get(
                f"/api/v1/documents/{test_document.id}/feedback",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "overall_score" in data
            assert "strengths" in data
            assert "improvements" in data
