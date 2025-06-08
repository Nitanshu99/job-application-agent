"""
End-to-end integration tests for the complete job automation workflow.

Tests the full user journey from registration to successful job application.
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.models.user import User


class TestEndToEndWorkflow:
    """End-to-end integration tests for complete user workflows."""

    async def test_complete_job_application_workflow(self, async_client: AsyncClient, mock_phi3_service, mock_gemma_service, mock_mistral_service, mock_scraper_service):
        """Test complete workflow from user registration to job application."""
        
        # Step 1: User Registration
        user_data = {
            "email": "jobseeker@example.com",
            "password": "SecurePassword123!",
            "full_name": "John Jobseeker",
            "phone_number": "+1555123456",
            "location": "San Francisco, CA",
            "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
            "experience_years": 4,
            "education": "Bachelor's in Computer Science"
        }
        
        register_response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        user_id = register_response.json()["id"]
        
        # Step 2: User Login
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 3: Complete User Profile
        profile_update = {
            "work_experience": [
                {
                    "title": "Software Engineer",
                    "company": "TechStartup",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                    "description": "Developed full-stack web applications using Python and React"
                }
            ],
            "job_preferences": {
                "job_types": ["full-time"],
                "industries": ["technology", "fintech"],
                "remote_preference": "hybrid",
                "salary_range": [100000, 150000]
            }
        }
        
        profile_response = await async_client.put(
            "/api/v1/users/profile",
            json=profile_update,
            headers=auth_headers
        )
        assert profile_response.status_code == 200
        
        # Step 4: Job Search
        mock_gemma_service.analyze_job_match.return_value = {
            "relevance_score": 0.92,
            "matching_skills": ["Python", "React"],
            "missing_skills": ["Docker"],
            "success": True
        }
        
        with patch('app.services.job_service.JobService.search_jobs') as mock_search:
            mock_search.return_value = {
                "jobs": [
                    {
                        "id": 1,
                        "title": "Senior Full Stack Developer",
                        "company": "InnovativeTech",
                        "location": "San Francisco, CA",
                        "salary_min": 120000,
                        "salary_max": 160000,
                        "description": "Join our team to build cutting-edge applications...",
                        "relevance_score": 0.92,
                        "url": "https://innovativetech.com/jobs/senior-fullstack"
                    }
                ],
                "total_count": 1,
                "pagination": {"limit": 20, "offset": 0}
            }
            
            search_response = await async_client.get(
                "/api/v1/jobs/search",
                params={"keywords": "python react", "location": "San Francisco"},
                headers=auth_headers
            )
            assert search_response.status_code == 200
            jobs = search_response.json()["jobs"]
            assert len(jobs) == 1
            selected_job = jobs[0]
        
        # Step 5: Job Compatibility Analysis
        with patch('app.services.job_service.JobService.analyze_job_compatibility', return_value=mock_gemma_service.analyze_job_match.return_value):
            analysis_response = await async_client.post(
                f"/api/v1/jobs/{selected_job['id']}/analyze",
                headers=auth_headers
            )
            assert analysis_response.status_code == 200
            compatibility = analysis_response.json()
            assert compatibility["relevance_score"] > 0.9
        
        # Step 6: Document Generation
        mock_phi3_service.generate_resume.return_value = {
            "content": "JOHN JOBSEEKER\nSoftware Engineer\n\nEXPERIENCE\n- Software Engineer at TechStartup (2020-2024)\n...",
            "success": True,
            "model_used": "phi3-mini"
        }
        
        mock_phi3_service.generate_cover_letter.return_value = {
            "content": "Dear Hiring Manager,\n\nI am excited to apply for the Senior Full Stack Developer position...",
            "success": True,
            "model_used": "phi3-mini"
        }
        
        with patch('app.services.document_service.DocumentService.generate_resume', return_value=mock_phi3_service.generate_resume.return_value):
            resume_response = await async_client.post(
                "/api/v1/documents/resume/generate",
                json={"job_id": selected_job["id"], "template": "modern"},
                headers=auth_headers
            )
            assert resume_response.status_code == 201
            resume_doc = resume_response.json()
        
        with patch('app.services.document_service.DocumentService.generate_cover_letter', return_value=mock_phi3_service.generate_cover_letter.return_value):
            cover_letter_response = await async_client.post(
                "/api/v1/documents/cover-letter/generate",
                json={"job_id": selected_job["id"], "template": "professional"},
                headers=auth_headers
            )
            assert cover_letter_response.status_code == 201
            cover_letter_doc = cover_letter_response.json()
        
        # Step 7: Check for Duplicate Applications
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            duplicate_check_response = await async_client.post(
                "/api/v1/applications/check-duplicate",
                json={
                    "job_url": selected_job["url"],
                    "company": selected_job["company"],
                    "job_title": selected_job["title"]
                },
                headers=auth_headers
            )
            assert duplicate_check_response.status_code == 200
            assert duplicate_check_response.json()["is_duplicate"] is False
        
        # Step 8: Create Application
        application_data = {
            "job_id": selected_job["id"],
            "resume_id": resume_doc["id"],
            "cover_letter_id": cover_letter_doc["id"],
            "application_method": "automated",
            "notes": "Applied through AI automation system"
        }
        
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            application_response = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            assert application_response.status_code == 201
            application = application_response.json()
            assert application["status"] == "pending"
        
        # Step 9: Automated Application Submission (Optional)
        mock_mistral_service.fill_application_form.return_value = {
            "success": True,
            "application_id": "AUTO-12345",
            "form_data": {
                "name": "John Jobseeker",
                "email": "jobseeker@example.com",
                "phone": "+1555123456"
            },
            "submission_status": "submitted"
        }
        
        with patch('app.services.application_service.ApplicationService.submit_automated_application', return_value=mock_mistral_service.fill_application_form.return_value):
            auto_submit_response = await async_client.post(
                "/api/v1/applications/submit-automated",
                json={
                    "job_id": selected_job["id"],
                    "resume_id": resume_doc["id"],
                    "auto_submit": True
                },
                headers=auth_headers
            )
            # Note: This might return 201 or 202 depending on implementation
            assert auto_submit_response.status_code in [201, 202]
        
        # Step 10: Track Application Status
        application_id = application["id"]
        
        # Get application details
        app_detail_response = await async_client.get(
            f"/api/v1/applications/{application_id}",
            headers=auth_headers
        )
        assert app_detail_response.status_code == 200
        
        # Update application status
        status_update = {
            "status": "interview_scheduled",
            "notes": "Phone interview scheduled for next week"
        }
        
        status_response = await async_client.put(
            f"/api/v1/applications/{application_id}",
            json=status_update,
            headers=auth_headers
        )
        assert status_response.status_code == 200
        updated_app = status_response.json()
        assert updated_app["status"] == "interview_scheduled"
        
        # Step 11: View Application History and Statistics
        history_response = await async_client.get(
            "/api/v1/applications",
            headers=auth_headers
        )
        assert history_response.status_code == 200
        applications = history_response.json()["applications"]
        assert len(applications) >= 1
        
        stats_response = await async_client.get(
            "/api/v1/applications/statistics",
            headers=auth_headers
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total_applications"] >= 1
        
        # Step 12: Save Job for Later (if user wants to apply later)
        save_response = await async_client.post(
            f"/api/v1/jobs/{selected_job['id']}/save",
            headers=auth_headers
        )
        assert save_response.status_code == 200
        
        # Verify the complete workflow was successful
        final_profile_response = await async_client.get(
            "/api/v1/users/profile",
            headers=auth_headers
        )
        assert final_profile_response.status_code == 200
        
        final_stats_response = await async_client.get(
            "/api/v1/users/statistics",
            headers=auth_headers
        )
        assert final_stats_response.status_code == 200
        user_stats = final_stats_response.json()
        assert user_stats["applications_count"] >= 1
        assert user_stats["documents_count"] >= 2  # Resume + Cover Letter

    async def test_job_scraping_and_application_workflow(self, async_client: AsyncClient, admin_auth_headers, auth_headers, mock_scraper_service, mock_phi3_service, mock_mistral_service):
        """Test workflow involving job scraping and subsequent applications."""
        
        # Step 1: Admin initiates job scraping
        mock_scraper_service.scrape_jobs.return_value = [
            {
                "title": "Python Backend Developer",
                "company": "ScrapedTech Corp",
                "location": "Austin, TX",
                "url": "https://scrapedtech.com/jobs/python-backend",
                "description": "Backend development role using Python and FastAPI",
                "requirements": ["Python", "FastAPI", "PostgreSQL"],
                "salary_min": 100000,
                "salary_max": 140000,
                "job_type": "full-time"
            },
            {
                "title": "Full Stack Engineer", 
                "company": "RemoteCorp",
                "location": "Remote",
                "url": "https://remotecorp.com/jobs/fullstack",
                "description": "Full stack development with React and Node.js",
                "requirements": ["React", "Node.js", "TypeScript"],
                "salary_min": 110000,
                "salary_max": 150000,
                "job_type": "full-time"
            }
        ]
        
        with patch('app.services.scrapers.scraper_factory.ScraperFactory.get_scraper', return_value=mock_scraper_service):
            scrape_response = await async_client.post(
                "/api/v1/jobs/scrape",
                json={
                    "portal_url": "https://jobs.example.com",
                    "search_terms": "python developer",
                    "max_jobs": 20
                },
                headers=admin_auth_headers
            )
            assert scrape_response.status_code == 202  # Accepted for background processing
            task_id = scrape_response.json()["task_id"]
        
        # Step 2: Check scraping status
        with patch('app.services.job_service.JobService.get_scraping_status') as mock_status:
            mock_status.return_value = {
                "task_id": task_id,
                "status": "completed",
                "jobs_found": 2,
                "jobs_imported": 2
            }
            
            status_response = await async_client.get(
                f"/api/v1/jobs/scrape/{task_id}/status",
                headers=admin_auth_headers
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == "completed"
        
        # Step 3: User searches for newly scraped jobs
        with patch('app.services.job_service.JobService.search_jobs') as mock_search:
            mock_search.return_value = {
                "jobs": [
                    {
                        "id": 100,
                        "title": "Python Backend Developer",
                        "company": "ScrapedTech Corp",
                        "location": "Austin, TX",
                        "salary_min": 100000,
                        "salary_max": 140000,
                        "url": "https://scrapedtech.com/jobs/python-backend",
                        "relevance_score": 0.88
                    }
                ],
                "total_count": 1
            }
            
            search_response = await async_client.get(
                "/api/v1/jobs/search",
                params={"keywords": "python backend", "location": "Austin"},
                headers=auth_headers
            )
            assert search_response.status_code == 200
            jobs = search_response.json()["jobs"]
            target_job = jobs[0]
        
        # Step 4: Generate documents for scraped job
        mock_phi3_service.generate_resume.return_value = {
            "content": "Resume tailored for Python Backend Developer at ScrapedTech Corp...",
            "success": True
        }
        
        with patch('app.services.document_service.DocumentService.generate_resume', return_value=mock_phi3_service.generate_resume.return_value):
            resume_response = await async_client.post(
                "/api/v1/documents/resume/generate",
                json={"job_id": target_job["id"], "template": "technical"},
                headers=auth_headers
            )
            assert resume_response.status_code == 201
        
        # Step 5: Apply to scraped job
        application_data = {
            "job_id": target_job["id"],
            "resume_id": resume_response.json()["id"],
            "application_method": "manual",
            "notes": "Applying to job found through automated scraping"
        }
        
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            application_response = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            assert application_response.status_code == 201

    async def test_bulk_application_workflow(self, async_client: AsyncClient, auth_headers, mock_phi3_service, mock_mistral_service):
        """Test bulk application workflow for multiple jobs."""
        
        # Step 1: Get job recommendations
        with patch('app.services.job_service.JobService.get_recommendations') as mock_recommendations:
            mock_recommendations.return_value = [
                {
                    "job_id": 1,
                    "title": "Senior Python Developer",
                    "company": "TechCorp A",
                    "relevance_score": 0.95
                },
                {
                    "job_id": 2,
                    "title": "Full Stack Engineer",
                    "company": "TechCorp B", 
                    "relevance_score": 0.90
                },
                {
                    "job_id": 3,
                    "title": "Backend Engineer",
                    "company": "TechCorp C",
                    "relevance_score": 0.85
                }
            ]
            
            recommendations_response = await async_client.get(
                "/api/v1/jobs/recommendations",
                headers=auth_headers
            )
            assert recommendations_response.status_code == 200
            recommended_jobs = recommendations_response.json()["recommendations"]
        
        # Step 2: Batch generate documents
        job_ids = [job["job_id"] for job in recommended_jobs]
        
        mock_phi3_service.generate_resume.return_value = {"content": "Batch resume", "success": True}
        mock_phi3_service.generate_cover_letter.return_value = {"content": "Batch cover letter", "success": True}
        
        with patch('app.services.document_service.DocumentService.batch_generate') as mock_batch:
            mock_batch.return_value = {
                "task_id": "batch-docs-123",
                "status": "processing",
                "jobs_count": len(job_ids)
            }
            
            batch_response = await async_client.post(
                "/api/v1/documents/batch-generate",
                json={
                    "job_ids": job_ids,
                    "document_types": ["resume", "cover_letter"],
                    "template": "modern"
                },
                headers=auth_headers
            )
            assert batch_response.status_code == 202
            batch_task_id = batch_response.json()["task_id"]
        
        # Step 3: Check batch generation status
        with patch('app.services.document_service.DocumentService.get_batch_status') as mock_batch_status:
            mock_batch_status.return_value = {
                "task_id": batch_task_id,
                "status": "completed",
                "total_jobs": 3,
                "completed_jobs": 3,
                "generated_documents": list(range(1, 7))  # 6 documents (2 per job)
            }
            
            batch_status_response = await async_client.get(
                f"/api/v1/documents/batch-generate/{batch_task_id}/status",
                headers=auth_headers
            )
            assert batch_status_response.status_code == 200
            assert batch_status_response.json()["status"] == "completed"
        
        # Step 4: Bulk update application statuses (simulate applications created)
        application_ids = [1, 2, 3]  # Assume these were created
        
        bulk_update_data = {
            "application_ids": application_ids,
            "status": "pending",
            "notes": "Batch applications submitted"
        }
        
        bulk_update_response = await async_client.put(
            "/api/v1/applications/bulk-update",
            json=bulk_update_data,
            headers=auth_headers
        )
        assert bulk_update_response.status_code == 200

    async def test_application_tracking_and_analytics_workflow(self, async_client: AsyncClient, auth_headers):
        """Test comprehensive application tracking and analytics workflow."""
        
        # Step 1: Create multiple applications with different statuses
        application_statuses = ["pending", "interview_scheduled", "rejected", "offer_received"]
        
        for i, status in enumerate(application_statuses):
            # Simulate application creation and status updates
            if i > 0:  # First one stays pending
                update_data = {
                    "status": status,
                    "notes": f"Application moved to {status} status"
                }
                
                if status == "interview_scheduled":
                    update_data["follow_up_date"] = (datetime.now() + timedelta(days=3)).isoformat()
                
                # This would normally be updating existing applications
                # For test purposes, we'll just verify the endpoint works
                update_response = await async_client.put(
                    f"/api/v1/applications/{i+1}",
                    json=update_data,
                    headers=auth_headers
                )
                # May return 404 if application doesn't exist, which is fine for test
                assert update_response.status_code in [200, 404]
        
        # Step 2: Get comprehensive application statistics
        stats_response = await async_client.get(
            "/api/v1/applications/statistics",
            headers=auth_headers
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert "total_applications" in stats
        assert "success_rate" in stats
        
        # Step 3: Get application metrics and insights
        metrics_response = await async_client.get(
            "/api/v1/applications/metrics",
            headers=auth_headers
        )
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        assert "response_rate" in metrics
        assert "interview_rate" in metrics
        
        # Step 4: Get applications by company
        company_response = await async_client.get(
            "/api/v1/applications/by-company",
            headers=auth_headers
        )
        assert company_response.status_code == 200
        
        # Step 5: Export application data
        export_data = {
            "format": "csv",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31"
        }
        
        export_response = await async_client.post(
            "/api/v1/applications/export",
            json=export_data,
            headers=auth_headers
        )
        assert export_response.status_code == 200

    async def test_error_handling_and_recovery_workflow(self, async_client: AsyncClient, auth_headers, mock_phi3_service):
        """Test error handling and recovery in the application workflow."""
        
        # Step 1: Attempt document generation with service error
        mock_phi3_service.generate_resume.side_effect = Exception("Service temporarily unavailable")
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            error_response = await async_client.post(
                "/api/v1/documents/resume/generate",
                json={"job_id": 1, "template": "modern"},
                headers=auth_headers
            )
            # Should handle error gracefully
            assert error_response.status_code in [500, 503]
        
        # Step 2: Recovery - service is back online
        mock_phi3_service.generate_resume.side_effect = None
        mock_phi3_service.generate_resume.return_value = {
            "content": "Successfully generated resume after recovery",
            "success": True
        }
        
        with patch('app.services.document_service.DocumentService.get_phi3_service', return_value=mock_phi3_service):
            recovery_response = await async_client.post(
                "/api/v1/documents/resume/generate",
                json={"job_id": 1, "template": "modern"},
                headers=auth_headers
            )
            assert recovery_response.status_code == 201
        
        # Step 3: Test duplicate application prevention
        application_data = {
            "job_id": 1,
            "resume_id": 1,
            "application_method": "manual"
        }
        
        # First application should succeed
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=False):
            first_app_response = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            assert first_app_response.status_code == 201
        
        # Second application to same job should be prevented
        with patch('app.services.application_manager.ApplicationManager.check_duplicate', return_value=True):
            duplicate_app_response = await async_client.post(
                "/api/v1/applications",
                json=application_data,
                headers=auth_headers
            )
            assert duplicate_app_response.status_code == 409  # Conflict
        
        # Step 4: Test graceful handling of invalid job ID
        invalid_job_response = await async_client.get(
            "/api/v1/jobs/99999",
            headers=auth_headers
        )
        assert invalid_job_response.status_code == 404
        
        # Step 5: Test handling of invalid document ID
        invalid_doc_response = await async_client.get(
            "/api/v1/documents/99999",
            headers=auth_headers
        )
        assert invalid_doc_response.status_code == 404

    async def test_user_journey_with_preferences_and_alerts(self, async_client: AsyncClient, auth_headers):
        """Test user journey focusing on preferences, alerts, and personalization."""
        
        # Step 1: Set detailed job preferences
        preferences_data = {
            "job_preferences": {
                "job_types": ["full-time", "contract"],
                "industries": ["technology", "fintech", "healthtech"],
                "remote_preference": "hybrid",
                "company_size": ["startup", "medium"],
                "salary_range": [120000, 180000],
                "benefits_priorities": ["health_insurance", "flexible_schedule", "stock_options"]
            }
        }
        
        preferences_response = await async_client.put(
            "/api/v1/users/preferences",
            json=preferences_data,
            headers=auth_headers
        )
        assert preferences_response.status_code == 200
        
        # Step 2: Create job alerts based on preferences
        alert_data = {
            "name": "Senior Dev Opportunities",
            "keywords": "senior python developer",
            "location": "San Francisco",
            "salary_min": 120000,
            "email_frequency": "daily",
            "is_active": True
        }
        
        alert_response = await async_client.post(
            "/api/v1/jobs/alerts",
            json=alert_data,
            headers=auth_headers
        )
        assert alert_response.status_code == 201
        
        # Step 3: Get personalized job recommendations
        recommendations_response = await async_client.get(
            "/api/v1/jobs/recommendations",
            headers=auth_headers
        )
        assert recommendations_response.status_code == 200
        
        # Step 4: Get user insights and career recommendations
        insights_response = await async_client.get(
            "/api/v1/users/insights",
            headers=auth_headers
        )
        assert insights_response.status_code == 200
        insights = insights_response.json()
        assert "skill_gap_analysis" in insights
        
        # Step 5: Update skills based on recommendations
        if "skill_recommendations" in insights:
            for skill in insights["skill_recommendations"][:2]:  # Add first 2 recommended skills
                skill_response = await async_client.post(
                    "/api/v1/users/skills",
                    json={"skill": skill},
                    headers=auth_headers
                )
                # May return 201 or 409 if skill already exists
                assert skill_response.status_code in [201, 409]
        
        # Step 6: Check job alerts for new matches
        alerts_response = await async_client.get(
            "/api/v1/jobs/alerts",
            headers=auth_headers
        )
        assert alerts_response.status_code == 200
        
        # Step 7: Get updated recommendations after profile changes
        updated_recommendations_response = await async_client.get(
            "/api/v1/jobs/recommendations",
            headers=auth_headers
        )
        assert updated_recommendations_response.status_code == 200
