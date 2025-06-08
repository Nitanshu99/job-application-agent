"""
Integration tests for users API endpoints.

Tests user profile management, preferences, and user-related operations.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime

from app.models.user import User


class TestUsersAPI:
    """Integration tests for user endpoints."""

    async def test_get_current_user_profile(self, async_client: AsyncClient, auth_headers, test_user: User):
        """Test getting current user profile."""
        response = await async_client.get(
            "/api/v1/users/profile",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert "hashed_password" not in data  # Should not expose password

    async def test_get_user_profile_unauthorized(self, async_client: AsyncClient):
        """Test getting user profile without authentication."""
        response = await async_client.get("/api/v1/users/profile")
        
        assert response.status_code == 401

    async def test_update_user_profile_success(self, async_client: AsyncClient, auth_headers, test_user: User):
        """Test successful user profile update."""
        update_data = {
            "full_name": "Updated Full Name",
            "location": "Updated Location",
            "skills": ["Python", "FastAPI", "React", "TypeScript"],
            "experience_years": 6,
            "preferred_salary_min": 110000,
            "preferred_salary_max": 160000
        }
        
        response = await async_client.put(
            "/api/v1/users/profile",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["location"] == update_data["location"]
        assert data["skills"] == update_data["skills"]
        assert data["experience_years"] == update_data["experience_years"]

    async def test_update_user_profile_partial(self, async_client: AsyncClient, auth_headers):
        """Test partial user profile update."""
        update_data = {
            "location": "New York, NY",
            "experience_years": 7
        }
        
        response = await async_client.put(
            "/api/v1/users/profile",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"] == update_data["location"]
        assert data["experience_years"] == update_data["experience_years"]
        # Other fields should remain unchanged

    async def test_update_user_profile_invalid_data(self, async_client: AsyncClient, auth_headers):
        """Test user profile update with invalid data."""
        update_data = {
            "experience_years": -1,  # Invalid negative experience
            "preferred_salary_min": 200000,  # Min > Max
            "preferred_salary_max": 100000
        }
        
        response = await async_client.put(
            "/api/v1/users/profile",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_get_user_preferences(self, async_client: AsyncClient, auth_headers):
        """Test getting user job preferences."""
        response = await async_client.get(
            "/api/v1/users/preferences",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_preferences" in data
        assert isinstance(data["job_preferences"], dict)

    async def test_update_user_preferences(self, async_client: AsyncClient, auth_headers):
        """Test updating user job preferences."""
        preferences_data = {
            "job_preferences": {
                "job_types": ["full-time", "contract"],
                "industries": ["technology", "fintech", "healthtech"],
                "remote_preference": "hybrid",
                "company_size": ["startup", "medium"],
                "work_schedule": "flexible"
            }
        }
        
        response = await async_client.put(
            "/api/v1/users/preferences",
            json=preferences_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_preferences"]["job_types"] == preferences_data["job_preferences"]["job_types"]
        assert data["job_preferences"]["remote_preference"] == "hybrid"

    async def test_add_user_skill(self, async_client: AsyncClient, auth_headers):
        """Test adding a skill to user profile."""
        skill_data = {"skill": "Kubernetes"}
        
        response = await async_client.post(
            "/api/v1/users/skills",
            json=skill_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "Kubernetes" in data["skills"]

    async def test_add_duplicate_skill(self, async_client: AsyncClient, auth_headers, test_user: User):
        """Test adding a skill that already exists."""
        existing_skill = test_user.skills[0] if test_user.skills else "Python"
        skill_data = {"skill": existing_skill}
        
        response = await async_client.post(
            "/api/v1/users/skills",
            json=skill_data,
            headers=auth_headers
        )
        
        assert response.status_code == 409  # Conflict - skill already exists

    async def test_remove_user_skill(self, async_client: AsyncClient, auth_headers, test_user: User):
        """Test removing a skill from user profile."""
        if test_user.skills:
            skill_to_remove = test_user.skills[0]
            
            response = await async_client.delete(
                f"/api/v1/users/skills/{skill_to_remove}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert skill_to_remove not in data["skills"]

    async def test_remove_nonexistent_skill(self, async_client: AsyncClient, auth_headers):
        """Test removing a skill that doesn't exist."""
        response = await async_client.delete(
            "/api/v1/users/skills/NonExistentSkill",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_upload_profile_picture(self, async_client: AsyncClient, auth_headers, temp_file):
        """Test uploading user profile picture."""
        with open(temp_file, "rb") as f:
            files = {"profile_picture": ("avatar.jpg", f, "image/jpeg")}
            
            response = await async_client.post(
                "/api/v1/users/profile-picture",
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "profile_picture_url" in data

    async def test_upload_invalid_profile_picture(self, async_client: AsyncClient, auth_headers, temp_file):
        """Test uploading invalid profile picture format."""
        with open(temp_file, "rb") as f:
            files = {"profile_picture": ("document.txt", f, "text/plain")}
            
            response = await async_client.post(
                "/api/v1/users/profile-picture",
                files=files,
                headers=auth_headers
            )
            
            assert response.status_code == 400  # Invalid file type

    async def test_delete_profile_picture(self, async_client: AsyncClient, auth_headers):
        """Test deleting user profile picture."""
        response = await async_client.delete(
            "/api/v1/users/profile-picture",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_get_user_statistics(self, async_client: AsyncClient, auth_headers):
        """Test getting user activity statistics."""
        response = await async_client.get(
            "/api/v1/users/statistics",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "applications_count" in data
        assert "documents_count" in data
        assert "saved_jobs_count" in data
        assert "profile_completion" in data

    async def test_get_user_activity_timeline(self, async_client: AsyncClient, auth_headers):
        """Test getting user activity timeline."""
        response = await async_client.get(
            "/api/v1/users/activity",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert isinstance(data["activities"], list)

    async def test_update_user_privacy_settings(self, async_client: AsyncClient, auth_headers):
        """Test updating user privacy settings."""
        privacy_data = {
            "profile_visibility": "private",
            "email_notifications": False,
            "data_sharing": False,
            "search_visibility": True
        }
        
        response = await async_client.put(
            "/api/v1/users/privacy",
            json=privacy_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["profile_visibility"] == "private"
        assert data["email_notifications"] is False

    async def test_get_user_privacy_settings(self, async_client: AsyncClient, auth_headers):
        """Test getting user privacy settings."""
        response = await async_client.get(
            "/api/v1/users/privacy",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "profile_visibility" in data
        assert "email_notifications" in data
        assert "data_sharing" in data

    async def test_export_user_data(self, async_client: AsyncClient, auth_headers):
        """Test exporting user data (GDPR compliance)."""
        response = await async_client.post(
            "/api/v1/users/export-data",
            headers=auth_headers
        )
        
        assert response.status_code == 202  # Accepted for background processing
        data = response.json()
        assert "export_id" in data
        assert "status" in data

    async def test_get_export_status(self, async_client: AsyncClient, auth_headers):
        """Test getting data export status."""
        export_id = "export-123"
        
        response = await async_client.get(
            f"/api/v1/users/export-data/{export_id}/status",
            headers=auth_headers
        )
        
        # May return 404 if export doesn't exist, which is fine for test
        assert response.status_code in [200, 404]

    async def test_delete_user_account(self, async_client: AsyncClient, auth_headers):
        """Test deleting user account."""
        delete_data = {
            "confirmation": "DELETE",
            "reason": "No longer needed"
        }
        
        response = await async_client.delete(
            "/api/v1/users/account",
            json=delete_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Account deletion initiated"

    async def test_deactivate_user_account(self, async_client: AsyncClient, auth_headers):
        """Test deactivating user account."""
        response = await async_client.post(
            "/api/v1/users/deactivate",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Account deactivated successfully"

    async def test_reactivate_user_account(self, async_client: AsyncClient):
        """Test reactivating user account."""
        reactivation_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        response = await async_client.post(
            "/api/v1/users/reactivate",
            json=reactivation_data
        )
        
        # May return 404 if user not found or not deactivated
        assert response.status_code in [200, 404, 400]

    async def test_update_notification_preferences(self, async_client: AsyncClient, auth_headers):
        """Test updating notification preferences."""
        notification_data = {
            "email_notifications": {
                "job_alerts": True,
                "application_updates": True,
                "newsletter": False,
                "marketing": False
            },
            "push_notifications": {
                "new_matches": True,
                "application_deadlines": True
            },
            "frequency": "daily"
        }
        
        response = await async_client.put(
            "/api/v1/users/notifications",
            json=notification_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email_notifications"]["job_alerts"] is True
        assert data["email_notifications"]["marketing"] is False

    async def test_get_notification_preferences(self, async_client: AsyncClient, auth_headers):
        """Test getting notification preferences."""
        response = await async_client.get(
            "/api/v1/users/notifications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "email_notifications" in data
        assert "push_notifications" in data

    async def test_update_user_location(self, async_client: AsyncClient, auth_headers):
        """Test updating user location with geocoding."""
        location_data = {
            "address": "123 Main St, San Francisco, CA 94105",
            "city": "San Francisco",
            "state": "CA",
            "country": "USA",
            "timezone": "America/Los_Angeles"
        }
        
        response = await async_client.put(
            "/api/v1/users/location",
            json=location_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "San Francisco"
        assert data["state"] == "CA"

    async def test_get_user_recommendations(self, async_client: AsyncClient, auth_headers):
        """Test getting personalized recommendations for user."""
        response = await async_client.get(
            "/api/v1/users/recommendations",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_recommendations" in data
        assert "skill_recommendations" in data
        assert "career_recommendations" in data

    async def test_update_work_experience(self, async_client: AsyncClient, auth_headers):
        """Test updating user work experience."""
        experience_data = {
            "work_experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "TechCorp Inc.",
                    "start_date": "2022-01-01",
                    "end_date": "2024-01-01",
                    "description": "Led development of microservices architecture",
                    "skills_used": ["Python", "Docker", "Kubernetes"],
                    "achievements": ["Improved system performance by 40%"]
                },
                {
                    "title": "Software Engineer",
                    "company": "StartupXYZ",
                    "start_date": "2020-06-01",
                    "end_date": "2021-12-31",
                    "description": "Developed full-stack web applications",
                    "skills_used": ["React", "Node.js", "MongoDB"]
                }
            ]
        }
        
        response = await async_client.put(
            "/api/v1/users/work-experience",
            json=experience_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["work_experience"]) == 2
        assert data["work_experience"][0]["title"] == "Senior Software Engineer"

    async def test_update_education(self, async_client: AsyncClient, auth_headers):
        """Test updating user education information."""
        education_data = {
            "education": [
                {
                    "degree": "Master of Science",
                    "field": "Computer Science",
                    "institution": "Stanford University",
                    "graduation_year": 2020,
                    "gpa": 3.8
                },
                {
                    "degree": "Bachelor of Science",
                    "field": "Computer Engineering",
                    "institution": "UC Berkeley",
                    "graduation_year": 2018,
                    "gpa": 3.6
                }
            ]
        }
        
        response = await async_client.put(
            "/api/v1/users/education",
            json=education_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["education"]) == 2
        assert data["education"][0]["institution"] == "Stanford University"

    async def test_update_certifications(self, async_client: AsyncClient, auth_headers):
        """Test updating user certifications."""
        certification_data = {
            "certifications": [
                {
                    "name": "AWS Certified Solutions Architect",
                    "issuer": "Amazon Web Services",
                    "issue_date": "2023-06-15",
                    "expiry_date": "2026-06-15",
                    "credential_id": "AWS-CSA-12345"
                },
                {
                    "name": "Certified Kubernetes Administrator",
                    "issuer": "Cloud Native Computing Foundation",
                    "issue_date": "2023-03-10",
                    "expiry_date": "2026-03-10"
                }
            ]
        }
        
        response = await async_client.put(
            "/api/v1/users/certifications",
            json=certification_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["certifications"]) == 2
        assert data["certifications"][0]["name"] == "AWS Certified Solutions Architect"

    async def test_get_profile_completion_status(self, async_client: AsyncClient, auth_headers):
        """Test getting profile completion status."""
        response = await async_client.get(
            "/api/v1/users/profile-completion",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "completion_percentage" in data
        assert "missing_sections" in data
        assert "recommendations" in data
        assert 0 <= data["completion_percentage"] <= 100

    async def test_search_users_admin(self, async_client: AsyncClient, admin_auth_headers):
        """Test searching users as admin."""
        search_params = {
            "query": "software engineer",
            "skills": "Python",
            "location": "San Francisco",
            "limit": 10
        }
        
        response = await async_client.get(
            "/api/v1/users/search",
            params=search_params,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "pagination" in data

    async def test_search_users_forbidden(self, async_client: AsyncClient, auth_headers):
        """Test searching users as regular user (should be forbidden)."""
        response = await async_client.get(
            "/api/v1/users/search",
            headers=auth_headers
        )
        
        assert response.status_code == 403

    async def test_get_user_insights(self, async_client: AsyncClient, auth_headers):
        """Test getting user career insights and analytics."""
        response = await async_client.get(
            "/api/v1/users/insights",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "career_progression" in data
        assert "skill_gap_analysis" in data
        assert "market_position" in data
        assert "improvement_suggestions" in data

    async def test_user_onboarding_status(self, async_client: AsyncClient, auth_headers):
        """Test getting user onboarding status."""
        response = await async_client.get(
            "/api/v1/users/onboarding",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "completed_steps" in data
        assert "remaining_steps" in data
        assert "progress_percentage" in data

    async def test_complete_onboarding_step(self, async_client: AsyncClient, auth_headers):
        """Test completing an onboarding step."""
        step_data = {
            "step": "profile_completion",
            "completed": True
        }
        
        response = await async_client.post(
            "/api/v1/users/onboarding/complete",
            json=step_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["step"] == "profile_completion"
        assert data["completed"] is True
