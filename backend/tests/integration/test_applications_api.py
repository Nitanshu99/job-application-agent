"""
Integration tests for applications API endpoints.

Tests application creation, tracking, duplicate prevention, and history management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from httpx import AsyncClient

from app.models.application import Application
from app.models.job import Job
from app.models.user import User


class TestApplicationsAPI:
    """Integration tests for application endpoints."""

    async def test_create_application_success(self, async_client: AsyncClient, auth_headers, test_job: Job, test_document):
        """Test successful application creation."""
        application_data = {
            "job_id": test_job.id,
            "resume_id": test_document.id,
            "cover_letter_id": test_document.id,
            "application_method": "automated",
            "notes": "Applied through automation system"
        }
        
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            response = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["job_id"] == test_job.id
            assert data["status"] == "pending"
            assert data["application_method"] == "automated"

    async def test_create_application_duplicate_detected(self, async_client: AsyncClient, auth_headers, test_job: Job, test_document):
        """Test application creation with duplicate detection."""
        application_data = {
            "job_id": test_job.id,
            "resume_id": test_document.id,
            "application_method": "manual"
        }
        
        # Mock duplicate detection returning True
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=True):
            response = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            
            assert response.status_code == 409  # Conflict due to duplicate
            data = response.json()
            assert "duplicate" in data["detail"].lower()

    async def test_check_duplicate_before_applying(self, async_client: AsyncClient, auth_headers, test_job: Job):
        """Test checking for duplicates before applying."""
        check_data = {
            "job_url": test_job.url,
            "company": test_job.company,
            "job_title": test_job.title
        }
        
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            response = await async_client.post(
                "/api/v1/applications/check-duplicate",
                json=check_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_duplicate"] is False
            assert "similar_applications" in data

    async def test_get_user_applications(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test getting user's applications."""
        response = await async_client.get(
            "/api/v1/applications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        assert "pagination" in data
        assert len(data["applications"]) >= 1

    async def test_get_user_applications_with_filters(self, async_client: AsyncClient, auth_headers):
        """Test getting applications with status filter."""
        params = {
            "status": "pending",
            "limit": 5,
            "offset": 0,
            "sort_by": "applied_at",
            "sort_order": "desc"
        }
        
        response = await async_client.get(
            "/api/v1/applications",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 5

    async def test_get_application_by_id(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test getting specific application by ID."""
        response = await async_client.get(
            f"/api/v1/applications/{test_application.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_application.id
        assert data["status"] == test_application.status

    async def test_get_application_unauthorized(self, async_client: AsyncClient, test_application: Application):
        """Test getting application without authentication."""
        response = await async_client.get(
            f"/api/v1/applications/{test_application.id}"
        )
        
        assert response.status_code == 401

    async def test_update_application_status(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test updating application status."""
        update_data = {
            "status": "interview_scheduled",
            "notes": "Interview scheduled for next week",
            "follow_up_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = await async_client.put(
            f"/api/v1/applications/{test_application.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "interview_scheduled"
        assert "Interview scheduled" in data["notes"]

    async def test_update_application_not_found(self, async_client: AsyncClient, auth_headers):
        """Test updating non-existent application."""
        update_data = {"status": "rejected"}
        
        response = await async_client.put(
            "/api/v1/applications/99999",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_delete_application(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test deleting an application."""
        response = await async_client.delete(
            f"/api/v1/applications/{test_application.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Application deleted successfully"

    async def test_get_application_history(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test getting application history."""
        response = await async_client.get(
            f"/api/v1/applications/{test_application.id}/history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    async def test_get_application_statistics(self, async_client: AsyncClient, auth_headers):
        """Test getting application statistics."""
        response = await async_client.get(
            "/api/v1/applications/statistics",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_applications" in data
        assert "pending" in data
        assert "interview_scheduled" in data
        assert "rejected" in data
        assert "offer_received" in data
        assert "success_rate" in data

    async def test_bulk_update_application_status(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test bulk updating application status."""
        update_data = {
            "application_ids": [test_application.id],
            "status": "archived",
            "notes": "Bulk archived old applications"
        }
        
        response = await async_client.put(
            "/api/v1/applications/bulk-update",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 1

    async def test_export_applications(self, async_client: AsyncClient, auth_headers):
        """Test exporting application data."""
        export_params = {
            "format": "csv",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "include_job_details": True
        }
        
        with patch('app.services.application_manager.ApplicationManager.export_applications') as mock_export:
            mock_export.return_value = [
                {
                    "job_title": "Software Engineer",
                    "company": "TechCorp",
                    "status": "pending",
                    "applied_at": datetime.now().isoformat()
                }
            ]
            
            response = await async_client.post(
                "/api/v1/applications/export",
                json=export_params,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            # Should return file or download link

    async def test_automated_application_submission(self, async_client: AsyncClient, auth_headers, test_job: Job, test_document, mock_mistral_service):
        """Test automated application submission."""
        # Mock successful automated application
        mock_mistral_service.fill_application_form.return_value = {
            "success": True,
            "application_id": "AUTO-12345",
            "form_data": {"name": "Test User", "email": "test@example.com"}
        }
        
        application_data = {
            "job_id": test_job.id,
            "resume_id": test_document.id,
            "application_method": "automated",
            "auto_submit": True
        }
        
        with patch('app.services.application_service.ApplicationService.submit_automated_application', return_value=mock_mistral_service.fill_application_form.return_value):
            response = await async_client.post(
                "/api/v1/applications/submit-automated",
                json=application_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "submitted"
            assert data["external_application_id"] == "AUTO-12345"

    async def test_mark_application_for_follow_up(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test marking application for follow-up."""
        follow_up_data = {
            "follow_up_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "follow_up_notes": "Follow up on application status"
        }
        
        response = await async_client.post(
            f"/api/v1/applications/{test_application.id}/follow-up",
            json=follow_up_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "follow_up_date" in data
        assert "Follow up on application status" in data["notes"]

    async def test_get_applications_requiring_follow_up(self, async_client: AsyncClient, auth_headers):
        """Test getting applications that require follow-up."""
        response = await async_client.get(
            "/api/v1/applications/follow-ups",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        assert isinstance(data["applications"], list)

    async def test_withdraw_application(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test withdrawing an application."""
        withdraw_data = {
            "reason": "Found better opportunity",
            "notes": "Withdrawing to accept another offer"
        }
        
        response = await async_client.post(
            f"/api/v1/applications/{test_application.id}/withdraw",
            json=withdraw_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "withdrawn"

    async def test_get_application_timeline(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test getting application timeline."""
        response = await async_client.get(
            f"/api/v1/applications/{test_application.id}/timeline",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        assert isinstance(data["timeline"], list)

    async def test_add_application_note(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test adding note to application."""
        note_data = {
            "note": "Had a great phone interview with the hiring manager",
            "note_type": "interview_feedback"
        }
        
        response = await async_client.post(
            f"/api/v1/applications/{test_application.id}/notes",
            json=note_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Note added successfully"

    async def test_get_application_notes(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test getting application notes."""
        response = await async_client.get(
            f"/api/v1/applications/{test_application.id}/notes",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert isinstance(data["notes"], list)

    async def test_get_applications_by_company(self, async_client: AsyncClient, auth_headers):
        """Test getting applications grouped by company."""
        response = await async_client.get(
            "/api/v1/applications/by-company",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "companies" in data
        assert isinstance(data["companies"], list)

    async def test_get_application_success_metrics(self, async_client: AsyncClient, auth_headers):
        """Test getting application success metrics."""
        response = await async_client.get(
            "/api/v1/applications/metrics",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response_rate" in data
        assert "interview_rate" in data
        assert "offer_rate" in data
        assert "average_response_time" in data

    async def test_duplicate_prevention_workflow(self, async_client: AsyncClient, auth_headers, test_job: Job, test_document):
        """Test complete duplicate prevention workflow."""
        # First, create an application
        application_data = {
            "job_id": test_job.id,
            "resume_id": test_document.id,
            "application_method": "manual"
        }
        
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            response1 = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            assert response1.status_code == 201
        
        # Try to apply to the same job again
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=True):
            response2 = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            assert response2.status_code == 409  # Should prevent duplicate

    async def test_application_reminders(self, async_client: AsyncClient, auth_headers):
        """Test getting application reminders."""
        response = await async_client.get(
            "/api/v1/applications/reminders",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        assert isinstance(data["reminders"], list)

    async def test_schedule_interview(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test scheduling an interview for application."""
        interview_data = {
            "interview_date": (datetime.now() + timedelta(days=5)).isoformat(),
            "interview_type": "phone",
            "interviewer": "John Smith",
            "location": "Video call",
            "notes": "Technical interview round 1"
        }
        
        response = await async_client.post(
            f"/api/v1/applications/{test_application.id}/interview",
            json=interview_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "interview_scheduled"

    async def test_update_interview_outcome(self, async_client: AsyncClient, auth_headers, test_application: Application):
        """Test updating interview outcome."""
        outcome_data = {
            "outcome": "passed",
            "feedback": "Strong technical skills, good cultural fit",
            "next_steps": "Awaiting final interview with team lead"
        }
        
        response = await async_client.put(
            f"/api/v1/applications/{test_application.id}/interview/outcome",
            json=outcome_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
