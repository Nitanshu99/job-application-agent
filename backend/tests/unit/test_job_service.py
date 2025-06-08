"""
Unit tests for job service functionality.

Tests job search, matching, scraping coordination, and job data management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.job import Job
from app.models.user import User
from app.services.job_service import JobService
from app.schemas.job import JobCreate, JobUpdate, JobSearch
from app.core.exceptions import JobNotFoundError, ScrapingError


class TestJobService:
    """Test suite for JobService class."""

    @pytest.fixture
    def job_service(self):
        """Create JobService instance for testing."""
        return JobService()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_job_create(self):
        """Sample job creation data."""
        return JobCreate(
            title="Senior Backend Developer",
            company="CloudTech Solutions",
            location="Austin, TX",
            job_type="full-time",
            salary_min=120000,
            salary_max=160000,
            description="Join our team to build scalable cloud-native applications...",
            requirements=[
                "5+ years backend development experience",
                "Proficiency in Python and Go",
                "Experience with microservices architecture",
                "Knowledge of cloud platforms (AWS/GCP/Azure)"
            ],
            url="https://cloudtech.com/careers/senior-backend-dev",
            source="company_website"
        )

    @pytest.fixture
    def sample_job_search(self):
        """Sample job search criteria."""
        return JobSearch(
            keywords="python developer",
            location="San Francisco",
            job_type="full-time",
            salary_min=80000,
            salary_max=150000,
            remote_only=False,
            experience_level="senior",
            limit=20,
            offset=0
        )

    async def test_create_job_success(self, job_service, mock_db_session, sample_job_create):
        """Test successful job creation."""
        # Mock job creation
        mock_job = MagicMock()
        mock_job.id = 1
        
        # Call service method
        created_job = await job_service.create_job(mock_db_session, sample_job_create)
        
        # Assertions
        assert created_job is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
        mock_db_session.refresh.assert_called()

    async def test_get_job_by_id_found(self, job_service, mock_db_session, test_job):
        """Test getting job by ID when it exists."""
        # Mock database get
        mock_db_session.get.return_value = test_job
        
        # Call service method
        found_job = await job_service.get_job_by_id(mock_db_session, test_job.id)
        
        # Assertions
        assert found_job == test_job

    async def test_get_job_by_id_not_found(self, job_service, mock_db_session):
        """Test getting job by ID when it doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Call service method
        found_job = await job_service.get_job_by_id(mock_db_session, 999)
        
        # Should return None
        assert found_job is None

    async def test_search_jobs_basic(self, job_service, mock_db_session, sample_job_search):
        """Test basic job search functionality."""
        # Mock database query results
        mock_jobs = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        search_results = await job_service.search_jobs(mock_db_session, sample_job_search)
        
        # Assertions
        assert len(search_results["jobs"]) == 3
        assert "total_count" in search_results
        assert "pagination" in search_results

    async def test_search_jobs_with_keywords(self, job_service, mock_db_session):
        """Test job search with keyword filtering."""
        search_criteria = JobSearch(keywords="machine learning python")
        
        # Mock database query
        mock_jobs = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        results = await job_service.search_jobs(mock_db_session, search_criteria)
        
        # Should call database with keyword filters
        mock_db_session.execute.assert_called()
        assert len(results["jobs"]) == 1

    async def test_search_jobs_with_location_filter(self, job_service, mock_db_session):
        """Test job search with location filtering."""
        search_criteria = JobSearch(location="Remote", remote_only=True)
        
        # Mock database query
        mock_jobs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        results = await job_service.search_jobs(mock_db_session, search_criteria)
        
        # Assertions
        assert len(results["jobs"]) == 2
        mock_db_session.execute.assert_called()

    async def test_search_jobs_with_salary_range(self, job_service, mock_db_session):
        """Test job search with salary range filtering."""
        search_criteria = JobSearch(salary_min=100000, salary_max=180000)
        
        # Mock database query
        mock_jobs = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        results = await job_service.search_jobs(mock_db_session, search_criteria)
        
        # Should filter by salary range
        assert len(results["jobs"]) == 1

    async def test_analyze_job_compatibility(self, job_service, test_job, test_user, mock_gemma_service):
        """Test job compatibility analysis using Gemma service."""
        # Mock Gemma service response
        mock_gemma_service.analyze_job_match.return_value = {
            "relevance_score": 0.88,
            "matching_skills": ["Python", "FastAPI"],
            "missing_skills": ["Kubernetes", "Docker"],
            "analysis": "Strong match based on technical skills and experience level",
            "recommendations": ["Consider learning containerization technologies"],
            "success": True
        }
        
        with patch('app.services.job_service.JobService.get_gemma_service', return_value=mock_gemma_service):
            compatibility = await job_service.analyze_job_compatibility(
                test_job,
                test_user.skills,
                test_user.experience_years
            )
        
        # Assertions
        assert compatibility["relevance_score"] == 0.88
        assert "Python" in compatibility["matching_skills"]
        assert "Kubernetes" in compatibility["missing_skills"]
        mock_gemma_service.analyze_job_match.assert_called_once()

    async def test_get_job_recommendations(self, job_service, mock_db_session, test_user, mock_gemma_service):
        """Test getting personalized job recommendations."""
        # Mock available jobs
        mock_jobs = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Mock Gemma service for each job
        mock_gemma_service.analyze_job_match.side_effect = [
            {"relevance_score": 0.9, "success": True},
            {"relevance_score": 0.7, "success": True},
            {"relevance_score": 0.6, "success": True}
        ]
        
        with patch('app.services.job_service.JobService.get_gemma_service', return_value=mock_gemma_service):
            recommendations = await job_service.get_job_recommendations(
                mock_db_session,
                test_user,
                limit=3
            )
        
        # Should return jobs sorted by relevance score
        assert len(recommendations) == 3
        assert recommendations[0]["relevance_score"] >= recommendations[1]["relevance_score"]

    async def test_scrape_jobs_from_platform(self, job_service, mock_db_session, mock_scraper_service):
        """Test job scraping from external platforms."""
        # Mock scraper response
        mock_scraper_service.scrape_jobs.return_value = [
            {
                "title": "Python Developer",
                "company": "TechCorp",
                "location": "San Francisco, CA",
                "url": "https://techcorp.com/jobs/python-dev",
                "description": "Python development role...",
                "requirements": ["Python", "Django"],
                "salary_min": 90000,
                "salary_max": 130000
            },
            {
                "title": "Full Stack Engineer",
                "company": "StartupXYZ",
                "location": "Remote",
                "url": "https://startupxyz.com/jobs/fullstack",
                "description": "Full stack development...",
                "requirements": ["React", "Node.js"]
            }
        ]
        
        with patch('app.services.scrapers.scraper_factory.ScraperFactory.get_scraper', return_value=mock_scraper_service):
            scraped_jobs = await job_service.scrape_jobs_from_platform(
                mock_db_session,
                platform="linkedin",
                search_terms="python developer",
                location="San Francisco",
                max_jobs=10
            )
        
        # Assertions
        assert len(scraped_jobs) == 2
        assert scraped_jobs[0]["title"] == "Python Developer"
        mock_scraper_service.scrape_jobs.assert_called_once()

    async def test_import_scraped_jobs(self, job_service, mock_db_session):
        """Test importing scraped job data into database."""
        scraped_data = [
            {
                "title": "Data Scientist",
                "company": "DataCorp",
                "location": "New York, NY",
                "url": "https://datacorp.com/jobs/data-scientist",
                "description": "Data science position...",
                "source": "indeed"
            },
            {
                "title": "ML Engineer",
                "company": "AIStartup",
                "location": "Boston, MA", 
                "url": "https://aistartup.com/jobs/ml-engineer",
                "description": "Machine learning role...",
                "source": "linkedin"
            }
        ]
        
        # Call service method
        import_result = await job_service.import_scraped_jobs(mock_db_session, scraped_data)
        
        # Assertions
        assert import_result["imported_count"] == 2
        assert import_result["skipped_count"] == 0
        assert mock_db_session.add.call_count == 2
        mock_db_session.commit.assert_called()

    async def test_import_scraped_jobs_with_duplicates(self, job_service, mock_db_session):
        """Test importing scraped jobs with duplicate handling."""
        # Mock existing job check
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [None, MagicMock()]  # First new, second duplicate
        mock_db_session.execute.return_value = mock_result
        
        scraped_data = [
            {"title": "New Job", "company": "NewCorp", "url": "https://new.com/job1"},
            {"title": "Existing Job", "company": "ExistingCorp", "url": "https://existing.com/job1"}
        ]
        
        # Call service method
        import_result = await job_service.import_scraped_jobs(mock_db_session, scraped_data)
        
        # Should import only new job
        assert import_result["imported_count"] == 1
        assert import_result["skipped_count"] == 1

    async def test_update_job_success(self, job_service, mock_db_session, test_job):
        """Test successful job update."""
        # Mock database get
        mock_db_session.get.return_value = test_job
        
        update_data = JobUpdate(
            title="Updated Job Title",
            salary_max=180000,
            description="Updated job description..."
        )
        
        # Call service method
        updated_job = await job_service.update_job(mock_db_session, test_job.id, update_data)
        
        # Assertions
        assert updated_job.title == update_data.title
        assert updated_job.salary_max == update_data.salary_max
        mock_db_session.commit.assert_called_once()

    async def test_update_job_not_found(self, job_service, mock_db_session):
        """Test updating job that doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        update_data = JobUpdate(title="Updated Title")
        
        # Should raise exception
        with pytest.raises(JobNotFoundError):
            await job_service.update_job(mock_db_session, 999, update_data)

    async def test_delete_job_success(self, job_service, mock_db_session, test_job):
        """Test successful job deletion."""
        # Mock database get
        mock_db_session.get.return_value = test_job
        
        # Call service method
        result = await job_service.delete_job(mock_db_session, test_job.id)
        
        # Assertions
        assert result is True
        mock_db_session.delete.assert_called_once_with(test_job)
        mock_db_session.commit.assert_called_once()

    async def test_get_trending_jobs(self, job_service, mock_db_session):
        """Test getting trending job titles and skills."""
        # Mock trending data query
        mock_trending_data = [
            ("AI Engineer", 95, 150, 145000),
            ("DevOps Engineer", 88, 120, 135000),
            ("Data Scientist", 82, 200, 130000)
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_trending_data
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        trending = await job_service.get_trending_jobs(mock_db_session, days=30, limit=10)
        
        # Assertions
        assert len(trending) == 3
        assert trending[0]["title"] == "AI Engineer"
        assert trending[0]["trend_score"] == 95

    async def test_get_job_statistics(self, job_service, mock_db_session):
        """Test getting job market statistics."""
        # Mock various statistics queries
        mock_db_session.execute.return_value.scalar.side_effect = [
            1500,  # total_jobs
            800,   # active_jobs
            150,   # new_jobs_this_week
            250    # remote_jobs
        ]
        
        # Mock location and company stats
        mock_location_stats = [("San Francisco", 200), ("New York", 180), ("Remote", 250)]
        mock_company_stats = [("TechCorp", 25), ("StartupXYZ", 20), ("BigTech", 30)]
        
        with patch.object(job_service, 'get_jobs_by_location', return_value=mock_location_stats):
            with patch.object(job_service, 'get_jobs_by_company', return_value=mock_company_stats):
                stats = await job_service.get_job_statistics(mock_db_session)
        
        # Assertions
        assert stats["total_jobs"] == 1500
        assert stats["active_jobs"] == 800
        assert stats["new_jobs_this_week"] == 150
        assert "jobs_by_location" in stats
        assert "jobs_by_company" in stats

    async def test_expire_old_jobs(self, job_service, mock_db_session):
        """Test expiring old job postings."""
        # Mock old jobs query
        old_jobs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = old_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        expired_count = await job_service.expire_old_jobs(mock_db_session, days_old=90)
        
        # Should mark jobs as inactive
        assert expired_count == 2
        for job in old_jobs:
            assert job.is_active is False
        mock_db_session.commit.assert_called()

    async def test_search_jobs_with_ai_ranking(self, job_service, mock_db_session, test_user, mock_gemma_service):
        """Test job search with AI-powered relevance ranking."""
        # Mock basic search results
        mock_jobs = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Mock AI relevance scoring
        mock_gemma_service.analyze_job_match.side_effect = [
            {"relevance_score": 0.95},
            {"relevance_score": 0.75},
            {"relevance_score": 0.85}
        ]
        
        search_criteria = JobSearch(keywords="python", use_ai_ranking=True)
        
        with patch('app.services.job_service.JobService.get_gemma_service', return_value=mock_gemma_service):
            results = await job_service.search_jobs_with_ai_ranking(
                mock_db_session,
                search_criteria,
                test_user
            )
        
        # Should return jobs sorted by AI relevance score
        assert len(results["jobs"]) == 3
        # First job should have highest score (0.95)
        assert results["jobs"][0]["relevance_score"] >= results["jobs"][1]["relevance_score"]

    async def test_save_job_for_user(self, job_service, mock_db_session, test_user, test_job):
        """Test saving job to user's saved list."""
        # Call service method
        result = await job_service.save_job_for_user(mock_db_session, test_user.id, test_job.id)
        
        # Assertions
        assert result is True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    async def test_unsave_job_for_user(self, job_service, mock_db_session, test_user, test_job):
        """Test removing job from user's saved list."""
        # Mock existing saved job
        mock_saved_job = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_saved_job
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        result = await job_service.unsave_job_for_user(mock_db_session, test_user.id, test_job.id)
        
        # Assertions
        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_saved_job)
        mock_db_session.commit.assert_called()

    async def test_get_saved_jobs_for_user(self, job_service, mock_db_session, test_user):
        """Test getting user's saved jobs."""
        # Mock saved jobs
        mock_saved_jobs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_saved_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        saved_jobs = await job_service.get_saved_jobs_for_user(mock_db_session, test_user.id)
        
        # Assertions
        assert len(saved_jobs) == 2

    async def test_report_job_posting(self, job_service, mock_db_session, test_user, test_job):
        """Test reporting a problematic job posting."""
        report_data = {
            "reason": "misleading_description",
            "details": "Job description doesn't match actual requirements",
            "reporter_id": test_user.id
        }
        
        # Call service method
        result = await job_service.report_job_posting(
            mock_db_session,
            test_job.id,
            report_data
        )
        
        # Assertions
        assert result is True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    async def test_get_job_alerts_for_user(self, job_service, mock_db_session, test_user):
        """Test getting user's job alerts."""
        # Mock job alerts
        mock_alerts = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_alerts
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        alerts = await job_service.get_job_alerts_for_user(mock_db_session, test_user.id)
        
        # Assertions
        assert len(alerts) == 2

    async def test_create_job_alert(self, job_service, mock_db_session, test_user):
        """Test creating a new job alert."""
        alert_data = {
            "name": "Python Developer Alert",
            "keywords": "python developer",
            "location": "San Francisco",
            "salary_min": 100000,
            "email_frequency": "daily",
            "is_active": True
        }
        
        # Call service method
        alert = await job_service.create_job_alert(mock_db_session, test_user.id, alert_data)
        
        # Assertions
        assert alert is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    async def test_check_job_alerts(self, job_service, mock_db_session):
        """Test checking job alerts for new matches."""
        # Mock active alerts
        mock_alerts = [MagicMock()]
        mock_alerts[0].keywords = "python developer"
        mock_alerts[0].location = "San Francisco"
        mock_alerts[0].user_id = 1
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_alerts
        mock_db_session.execute.return_value = mock_result
        
        # Mock new matching jobs
        mock_jobs = [MagicMock()]
        
        with patch.object(job_service, 'search_jobs', return_value={"jobs": mock_jobs}):
            alert_results = await job_service.check_job_alerts(mock_db_session)
        
        # Should return alerts with matching jobs
        assert len(alert_results) == 1
        assert "matching_jobs" in alert_results[0]

    async def test_export_job_search_results(self, job_service, mock_db_session, sample_job_search):
        """Test exporting job search results to file."""
        # Mock search results
        mock_jobs = [
            MagicMock(title="Job 1", company="Company 1"),
            MagicMock(title="Job 2", company="Company 2")
        ]
        
        with patch.object(job_service, 'search_jobs', return_value={"jobs": mock_jobs}):
            with patch('app.utils.file_handling.save_file') as mock_save:
                mock_save.return_value = "/tmp/job_export.csv"
                
                export_path = await job_service.export_search_results(
                    mock_db_session,
                    sample_job_search,
                    format="csv"
                )
        
        # Assertions
        assert export_path == "/tmp/job_export.csv"
        mock_save.assert_called_once()

    async def test_get_job_application_success_rate(self, job_service, mock_db_session, test_job):
        """Test getting application success rate for a job."""
        # Mock application statistics
        mock_db_session.execute.return_value.scalar.side_effect = [
            20,  # total applications
            5,   # successful applications
        ]
        
        # Call service method
        success_rate = await job_service.get_job_application_success_rate(
            mock_db_session,
            test_job.id
        )
        
        # Assertions
        assert success_rate == 0.25  # 5/20 = 25%

    async def test_get_similar_jobs(self, job_service, mock_db_session, test_job, mock_gemma_service):
        """Test finding similar jobs based on content analysis."""
        # Mock database query for candidate jobs
        mock_similar_jobs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_similar_jobs
        mock_db_session.execute.return_value = mock_result
        
        # Mock similarity analysis
        mock_gemma_service.analyze_similarity.side_effect = [
            {"similarity_score": 0.85},
            {"similarity_score": 0.92}
        ]
        
        with patch('app.services.job_service.JobService.get_gemma_service', return_value=mock_gemma_service):
            similar_jobs = await job_service.get_similar_jobs(
                mock_db_session,
                test_job.id,
                limit=5,
                min_similarity=0.8
            )
        
        # Should return jobs with high similarity scores
        assert len(similar_jobs) == 2
        assert all(job["similarity_score"] >= 0.8 for job in similar_jobs)
