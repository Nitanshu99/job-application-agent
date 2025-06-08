"""
Integration tests for jobs API endpoints.

Tests job search, creation, analysis, and job-related operations.
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient

from app.models.job import Job
from app.models.user import User


class TestJobsAPI:
    """Integration tests for job endpoints."""

    async def test_search_jobs_success(self, async_client: AsyncClient, auth_headers, mock_gemma_service):
        """Test successful job search."""
        # Mock job search results
        with patch('app.services.job_service.JobService.search_jobs') as mock_search:
            mock_search.return_value = [
                {
                    "id": 1,
                    "title": "Python Developer",
                    "company": "TechCorp",
                    "location": "San Francisco, CA",
                    "relevance_score": 0.9
                },
                {
                    "id": 2,
                    "title": "Backend Engineer",
                    "company": "StartupXYZ",
                    "location": "Remote",
                    "relevance_score": 0.8
                }
            ]
            
            search_params = {
                "keywords": "python developer",
                "location": "San Francisco",
                "job_type": "full-time",
                "salary_min": 80000,
                "salary_max": 150000,
                "limit": 10
            }
            
            response = await async_client.get(
                "/api/v1/jobs/search",
                params=search_params,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["jobs"]) == 2
            assert data["jobs"][0]["title"] == "Python Developer"
            assert data["jobs"][0]["relevance_score"] == 0.9

    async def test_search_jobs_without_auth(self, async_client: AsyncClient):
        """Test job search without authentication."""
        response = await async_client.get("/api/v1/jobs/search")
        
        assert response.status_code == 401

    async def test_search_jobs_with_filters(self, async_client: AsyncClient, auth_headers):
        """Test job search with various filters."""
        with patch('app.services.job_service.JobService.search_jobs') as mock_search:
            mock_search.return_value = []
            
            search_params = {
                "keywords": "machine learning",
                "location": "New York",
                "job_type": "contract",
                "remote_only": True,
                "company_size": "startup",
                "experience_level": "senior"
            }
            
            response = await async_client.get(
                "/api/v1/jobs/search",
                params=search_params,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            mock_search.assert_called_once()

    async def test_get_job_by_id_success(self, async_client: AsyncClient, auth_headers, test_job: Job):
        """Test getting specific job by ID."""
        response = await async_client.get(
            f"/api/v1/jobs/{test_job.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_job.id
        assert data["title"] == test_job.title
        assert data["company"] == test_job.company

    async def test_get_job_by_id_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting non-existent job."""
        response = await async_client.get(
            "/api/v1/jobs/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_analyze_job_compatibility(self, async_client: AsyncClient, auth_headers, test_job: Job, mock_gemma_service):
        """Test job compatibility analysis."""
        # Mock Gemma service response
        mock_gemma_service.analyze_job_match.return_value = {
            "relevance_score": 0.85,
            "matching_skills": ["Python", "FastAPI"],
            "missing_skills": ["Kubernetes"],
            "analysis": "Good match for your profile",
            "success": True
        }
        
        with patch('app.services.job_service.JobService.analyze_job_compatibility', return_value=mock_gemma_service.analyze_job_match.return_value):
            response = await async_client.post(
                f"/api/v1/jobs/{test_job.id}/analyze",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["relevance_score"] == 0.85
            assert "Python" in data["matching_skills"]
            assert "Kubernetes" in data["missing_skills"]

    async def test_save_job_for_later(self, async_client: AsyncClient, auth_headers, test_job: Job):
        """Test saving job for later application."""
        response = await async_client.post(
            f"/api/v1/jobs/{test_job.id}/save",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job saved successfully"

    async def test_unsave_job(self, async_client: AsyncClient, auth_headers, test_job: Job):
        """Test removing job from saved list."""
        # First save the job
        await async_client.post(
            f"/api/v1/jobs/{test_job.id}/save",
            headers=auth_headers
        )
        
        # Then unsave it
        response = await async_client.delete(
            f"/api/v1/jobs/{test_job.id}/save",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_get_saved_jobs(self, async_client: AsyncClient, auth_headers):
        """Test getting user's saved jobs."""
        response = await async_client.get(
            "/api/v1/jobs/saved",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["jobs"], list)

    async def test_create_job_posting_admin(self, async_client: AsyncClient, admin_auth_headers):
        """Test creating job posting as admin."""
        job_data = {
            "title": "Senior Data Scientist",
            "company": "AI Innovations",
            "location": "Boston, MA",
            "job_type": "full-time",
            "salary_min": 120000,
            "salary_max": 180000,
            "description": "Join our AI team to build cutting-edge ML models...",
            "requirements": [
                "PhD in Computer Science or related field",
                "5+ years ML experience",
                "Python and TensorFlow expertise"
            ],
            "url": "https://aiinnovations.com/careers/senior-data-scientist"
        }
        
        response = await async_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == job_data["title"]
        assert data["company"] == job_data["company"]

    async def test_create_job_posting_user_forbidden(self, async_client: AsyncClient, auth_headers):
        """Test creating job posting as regular user (should be forbidden)."""
        job_data = {
            "title": "Test Job",
            "company": "Test Company",
            "location": "Test Location"
        }
        
        response = await async_client.post(
            "/api/v1/jobs",
            json=job_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403

    async def test_update_job_posting_admin(self, async_client: AsyncClient, admin_auth_headers, test_job: Job):
        """Test updating job posting as admin."""
        update_data = {
            "title": "Updated Job Title",
            "salary_max": 160000,
            "description": "Updated job description..."
        }
        
        response = await async_client.put(
            f"/api/v1/jobs/{test_job.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["salary_max"] == update_data["salary_max"]

    async def test_delete_job_posting_admin(self, async_client: AsyncClient, admin_auth_headers, test_job: Job):
        """Test deleting job posting as admin."""
        response = await async_client.delete(
            f"/api/v1/jobs/{test_job.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200

    async def test_bulk_job_import_admin(self, async_client: AsyncClient, admin_auth_headers):
        """Test bulk importing jobs as admin."""
        jobs_data = {
            "jobs": [
                {
                    "title": "Frontend Developer",
                    "company": "WebCorp",
                    "location": "Seattle, WA",
                    "url": "https://webcorp.com/jobs/frontend"
                },
                {
                    "title": "DevOps Engineer",
                    "company": "CloudTech",
                    "location": "Austin, TX",
                    "url": "https://cloudtech.com/jobs/devops"
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/jobs/bulk-import",
            json=jobs_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["imported_count"] == 2

    async def test_scrape_jobs_from_portal(self, async_client: AsyncClient, auth_headers, mock_scraper_service):
        """Test scraping jobs from a job portal."""
        # Mock scraper service
        with patch('app.services.scrapers.scraper_factory.ScraperFactory.get_scraper') as mock_get_scraper:
            mock_scraper = mock_scraper_service
            mock_get_scraper.return_value = mock_scraper
            
            scrape_request = {
                "portal_url": "https://jobs.example.com",
                "search_terms": "python developer",
                "max_jobs": 20
            }
            
            response = await async_client.post(
                "/api/v1/jobs/scrape",
                json=scrape_request,
                headers=auth_headers
            )
            
            assert response.status_code == 202  # Accepted for background processing
            data = response.json()
            assert "task_id" in data

    async def test_get_job_scraping_status(self, async_client: AsyncClient, auth_headers):
        """Test getting job scraping task status."""
        task_id = "test-task-123"
        
        with patch('app.services.job_service.JobService.get_scraping_status') as mock_status:
            mock_status.return_value = {
                "task_id": task_id,
                "status": "completed",
                "jobs_found": 15,
                "jobs_imported": 12
            }
            
            response = await async_client.get(
                f"/api/v1/jobs/scrape/{task_id}/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["jobs_found"] == 15

    async def test_get_job_recommendations(self, async_client: AsyncClient, auth_headers, mock_gemma_service):
        """Test getting personalized job recommendations."""
        # Mock recommendation service
        with patch('app.services.job_service.JobService.get_recommendations') as mock_recommendations:
            mock_recommendations.return_value = [
                {
                    "job_id": 1,
                    "title": "Python Developer",
                    "company": "TechCorp",
                    "relevance_score": 0.95,
                    "match_reasons": ["Python expertise", "Location match"]
                },
                {
                    "job_id": 2,
                    "title": "Backend Engineer",
                    "company": "StartupXYZ",
                    "relevance_score": 0.88,
                    "match_reasons": ["FastAPI experience", "Startup preference"]
                }
            ]
            
            response = await async_client.get(
                "/api/v1/jobs/recommendations",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["recommendations"]) == 2
            assert data["recommendations"][0]["relevance_score"] == 0.95

    async def test_report_job_posting(self, async_client: AsyncClient, auth_headers, test_job: Job):
        """Test reporting a job posting for issues."""
        report_data = {
            "reason": "misleading_description",
            "details": "The job description doesn't match the actual requirements"
        }
        
        response = await async_client.post(
            f"/api/v1/jobs/{test_job.id}/report",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job reported successfully"

    async def test_get_job_statistics_admin(self, async_client: AsyncClient, admin_auth_headers):
        """Test getting job statistics as admin."""
        response = await async_client.get(
            "/api/v1/jobs/statistics",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "active_jobs" in data
        assert "jobs_by_location" in data
        assert "jobs_by_company" in data

    async def test_search_jobs_with_pagination(self, async_client: AsyncClient, auth_headers):
        """Test job search with pagination parameters."""
        with patch('app.services.job_service.JobService.search_jobs') as mock_search:
            mock_search.return_value = []
            
            search_params = {
                "keywords": "developer",
                "limit": 5,
                "offset": 10,
                "sort_by": "relevance_score",
                "sort_order": "desc"
            }
            
            response = await async_client.get(
                "/api/v1/jobs/search",
                params=search_params,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "pagination" in data
            assert data["pagination"]["limit"] == 5
            assert data["pagination"]["offset"] == 10

    async def test_export_job_search_results(self, async_client: AsyncClient, auth_headers):
        """Test exporting job search results."""
        with patch('app.services.job_service.JobService.export_search_results') as mock_export:
            mock_export.return_value = "job_export_123.csv"
            
            export_params = {
                "keywords": "python",
                "format": "csv",
                "include_applied": False
            }
            
            response = await async_client.post(
                "/api/v1/jobs/export",
                json=export_params,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "download_url" in data

    async def test_get_trending_jobs(self, async_client: AsyncClient, auth_headers):
        """Test getting trending jobs."""
        with patch('app.services.job_service.JobService.get_trending_jobs') as mock_trending:
            mock_trending.return_value = [
                {
                    "title": "AI Engineer",
                    "trend_score": 95,
                    "job_count": 150,
                    "avg_salary": 140000
                }
            ]
            
            response = await async_client.get(
                "/api/v1/jobs/trending",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["trending_jobs"]) == 1
            assert data["trending_jobs"][0]["title"] == "AI Engineer"

    async def test_job_alert_creation(self, async_client: AsyncClient, auth_headers):
        """Test creating job alert."""
        alert_data = {
            "name": "Python Developer Alert",
            "keywords": "python developer",
            "location": "San Francisco",
            "salary_min": 100000,
            "email_frequency": "daily",
            "is_active": True
        }
        
        response = await async_client.post(
            "/api/v1/jobs/alerts",
            json=alert_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == alert_data["name"]
        assert data["is_active"] is True

    async def test_get_job_alerts(self, async_client: AsyncClient, auth_headers):
        """Test getting user's job alerts."""
        response = await async_client.get(
            "/api/v1/jobs/alerts",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["alerts"], list)

    async def test_update_job_alert(self, async_client: AsyncClient, auth_headers):
        """Test updating job alert."""
        # First create an alert
        alert_data = {
            "name": "Test Alert",
            "keywords": "test",
            "location": "anywhere"
        }
        
        create_response = await async_client.post(
            "/api/v1/jobs/alerts",
            json=alert_data,
            headers=auth_headers
        )
        
        alert_id = create_response.json()["id"]
        
        # Update the alert
        update_data = {
            "keywords": "updated test",
            "is_active": False
        }
        
        response = await async_client.put(
            f"/api/v1/jobs/alerts/{alert_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["keywords"] == "updated test"
        assert data["is_active"] is False

    async def test_delete_job_alert(self, async_client: AsyncClient, auth_headers):
        """Test deleting job alert."""
        # First create an alert
        alert_data = {
            "name": "Test Alert to Delete",
            "keywords": "test",
            "location": "anywhere"
        }
        
        create_response = await async_client.post(
            "/api/v1/jobs/alerts",
            json=alert_data,
            headers=auth_headers
        )
        
        alert_id = create_response.json()["id"]
        
        # Delete the alert
        response = await async_client.delete(
            f"/api/v1/jobs/alerts/{alert_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
