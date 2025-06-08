"""
Unit tests for application manager service.

Tests application tracking, duplicate prevention, and application history management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.application_history import ApplicationHistory
from app.models.job import Job
from app.models.user import User
from app.services.application_manager import ApplicationManager
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.core.exceptions import DuplicateApplicationError, ApplicationNotFoundError


class TestApplicationManager:
    """Test suite for ApplicationManager class."""

    @pytest.fixture
    def application_manager(self):
        """Create ApplicationManager instance for testing."""
        return ApplicationManager()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_application_create(self, test_user, test_job):
        """Sample application creation data."""
        return ApplicationCreate(
            user_id=test_user.id,
            job_id=test_job.id,
            resume_id=1,
            cover_letter_id=2,
            application_method="automated",
            notes="Applied through automation system"
        )

    @pytest.fixture
    def sample_application_update(self):
        """Sample application update data."""
        return ApplicationUpdate(
            status="interview_scheduled",
            notes="Interview scheduled for next week",
            follow_up_date=datetime.now() + timedelta(days=7)
        )

    async def test_create_application_success(self, application_manager, mock_db_session, sample_application_create, test_user, test_job):
        """Test successful application creation."""
        # Mock duplicate check returning False
        application_manager.check_duplicate = AsyncMock(return_value=False)
        
        # Mock database operations
        mock_db_session.get.side_effect = [test_user, test_job]
        mock_application = MagicMock()
        mock_application.id = 1
        
        # Call service method
        created_application = await application_manager.create_application(
            mock_db_session, 
            sample_application_create
        )
        
        # Assertions
        assert created_application is not None
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
        application_manager.check_duplicate.assert_called_once()

    async def test_create_application_duplicate_detected(self, application_manager, mock_db_session, sample_application_create):
        """Test application creation with duplicate detection."""
        # Mock duplicate check returning True
        application_manager.check_duplicate = AsyncMock(return_value=True)
        
        # Should raise duplicate error
        with pytest.raises(DuplicateApplicationError):
            await application_manager.create_application(
                mock_db_session, 
                sample_application_create
            )
        
        # Should not add to database
        mock_db_session.add.assert_not_called()

    async def test_check_duplicate_by_url(self, application_manager, mock_db_session, test_user, test_job):
        """Test duplicate detection by job URL."""
        # Mock existing application with same job URL
        existing_application = MagicMock()
        existing_application.job.url = test_job.url
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_application
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        is_duplicate = await application_manager.check_duplicate(
            mock_db_session, 
            test_user.id, 
            test_job.url
        )
        
        # Should detect duplicate
        assert is_duplicate is True

    async def test_check_duplicate_by_company_and_title(self, application_manager, mock_db_session, test_user, test_job):
        """Test duplicate detection by company and job title."""
        # Mock existing application with same company and title
        existing_application = MagicMock()
        existing_application.job.company = test_job.company
        existing_application.job.title = test_job.title
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_application
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        is_duplicate = await application_manager.check_duplicate_by_company_title(
            mock_db_session,
            test_user.id,
            test_job.company,
            test_job.title
        )
        
        # Should detect duplicate
        assert is_duplicate is True

    async def test_check_duplicate_no_match(self, application_manager, mock_db_session, test_user):
        """Test duplicate detection with no existing applications."""
        # Mock no existing applications
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        is_duplicate = await application_manager.check_duplicate(
            mock_db_session,
            test_user.id,
            "https://newcompany.com/jobs/new-position"
        )
        
        # Should not detect duplicate
        assert is_duplicate is False

    async def test_get_application_by_id_found(self, application_manager, mock_db_session, test_application):
        """Test getting application by ID when it exists."""
        # Mock database get
        mock_db_session.get.return_value = test_application
        
        # Call service method
        found_application = await application_manager.get_application_by_id(
            mock_db_session, 
            test_application.id
        )
        
        # Assertions
        assert found_application == test_application

    async def test_get_application_by_id_not_found(self, application_manager, mock_db_session):
        """Test getting application by ID when it doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Call service method
        found_application = await application_manager.get_application_by_id(mock_db_session, 999)
        
        # Should return None
        assert found_application is None

    async def test_update_application_status_success(self, application_manager, mock_db_session, test_application, sample_application_update):
        """Test successful application status update."""
        # Mock database get
        mock_db_session.get.return_value = test_application
        
        # Call service method
        updated_application = await application_manager.update_application(
            mock_db_session,
            test_application.id,
            sample_application_update
        )
        
        # Assertions
        assert updated_application.status == sample_application_update.status
        assert updated_application.notes == sample_application_update.notes
        mock_db_session.commit.assert_called_once()

    async def test_update_application_not_found(self, application_manager, mock_db_session, sample_application_update):
        """Test updating application that doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Should raise exception
        with pytest.raises(ApplicationNotFoundError):
            await application_manager.update_application(
                mock_db_session,
                999,
                sample_application_update
            )

    async def test_get_user_applications(self, application_manager, mock_db_session, test_user):
        """Test getting all applications for a user."""
        # Mock database query results
        mock_applications = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_applications
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        applications = await application_manager.get_user_applications(
            mock_db_session,
            test_user.id,
            limit=10,
            offset=0
        )
        
        # Assertions
        assert len(applications) == 3

    async def test_get_applications_by_status(self, application_manager, mock_db_session, test_user):
        """Test getting applications filtered by status."""
        # Mock database query results
        mock_applications = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_applications
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        applications = await application_manager.get_applications_by_status(
            mock_db_session,
            test_user.id,
            "pending"
        )
        
        # Assertions
        assert len(applications) == 1

    async def test_get_application_statistics(self, application_manager, mock_db_session, test_user):
        """Test getting application statistics for a user."""
        # Mock database query results for different statistics
        mock_db_session.execute.return_value.scalar.side_effect = [
            10,  # total applications
            3,   # pending applications
            5,   # interview applications
            2,   # rejected applications
            0    # offers
        ]
        
        # Call service method
        stats = await application_manager.get_application_statistics(mock_db_session, test_user.id)
        
        # Assertions
        assert stats["total_applications"] == 10
        assert stats["pending"] == 3
        assert stats["interview_scheduled"] == 5
        assert stats["rejected"] == 2
        assert stats["offer_received"] == 0

    async def test_create_application_history_entry(self, application_manager, mock_db_session, test_application):
        """Test creating application history entry."""
        # Call service method
        await application_manager.create_application_history(
            mock_db_session,
            test_application.id,
            "status_updated",
            {"old_status": "pending", "new_status": "interview_scheduled"}
        )
        
        # Verify database operations
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    async def test_get_application_history(self, application_manager, mock_db_session, test_application):
        """Test getting application history."""
        # Mock database query results
        mock_history = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_history
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        history = await application_manager.get_application_history(
            mock_db_session,
            test_application.id
        )
        
        # Assertions
        assert len(history) == 2

    async def test_delete_application_success(self, application_manager, mock_db_session, test_application):
        """Test successful application deletion."""
        # Mock database get
        mock_db_session.get.return_value = test_application
        
        # Call service method
        result = await application_manager.delete_application(mock_db_session, test_application.id)
        
        # Assertions
        assert result is True
        mock_db_session.delete.assert_called_once_with(test_application)
        mock_db_session.commit.assert_called_once()

    async def test_delete_application_not_found(self, application_manager, mock_db_session):
        """Test deleting application that doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Should raise exception
        with pytest.raises(ApplicationNotFoundError):
            await application_manager.delete_application(mock_db_session, 999)

    async def test_bulk_update_application_status(self, application_manager, mock_db_session, test_user):
        """Test bulk updating application status."""
        # Mock applications
        mock_applications = [MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)]
        for app in mock_applications:
            app.user_id = test_user.id
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_applications
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        updated_count = await application_manager.bulk_update_status(
            mock_db_session,
            [1, 2, 3],
            "archived",
            test_user.id
        )
        
        # Assertions
        assert updated_count == 3
        mock_db_session.commit.assert_called()

    @patch('app.services.application_manager.similarity_score')
    async def test_find_similar_applications(self, mock_similarity, application_manager, mock_db_session, test_user, test_job):
        """Test finding similar applications using content analysis."""
        # Mock existing applications
        existing_apps = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = existing_apps
        mock_db_session.execute.return_value = mock_result
        
        # Mock similarity scores
        mock_similarity.side_effect = [0.9, 0.3]  # First is similar, second is not
        
        # Call service method
        similar_apps = await application_manager.find_similar_applications(
            mock_db_session,
            test_user.id,
            test_job.description,
            threshold=0.8
        )
        
        # Should return only the highly similar application
        assert len(similar_apps) == 1

    async def test_get_applications_requiring_follow_up(self, application_manager, mock_db_session, test_user):
        """Test getting applications that require follow-up."""
        # Mock database query results
        mock_applications = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_applications
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        follow_up_apps = await application_manager.get_applications_requiring_follow_up(
            mock_db_session,
            test_user.id
        )
        
        # Assertions
        assert len(follow_up_apps) == 1

    async def test_mark_application_for_follow_up(self, application_manager, mock_db_session, test_application):
        """Test marking application for follow-up."""
        # Mock database get
        mock_db_session.get.return_value = test_application
        
        follow_up_date = datetime.now() + timedelta(days=3)
        
        # Call service method
        updated_app = await application_manager.mark_for_follow_up(
            mock_db_session,
            test_application.id,
            follow_up_date,
            "Follow up on application status"
        )
        
        # Assertions
        assert updated_app.follow_up_date == follow_up_date
        assert "Follow up on application status" in updated_app.notes

    async def test_get_application_success_rate(self, application_manager, mock_db_session, test_user):
        """Test calculating application success rate."""
        # Mock database query results
        mock_db_session.execute.return_value.scalar.side_effect = [
            20,  # total applications
            5,   # successful applications (interviews + offers)
        ]
        
        # Call service method
        success_rate = await application_manager.get_success_rate(mock_db_session, test_user.id)
        
        # Assertions
        assert success_rate == 0.25  # 5/20 = 25%

    async def test_get_most_applied_companies(self, application_manager, mock_db_session, test_user):
        """Test getting companies user has applied to most."""
        # Mock database query results
        mock_results = [("TechCorp", 5), ("DataCorp", 3), ("StartupXYZ", 2)]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_results
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        companies = await application_manager.get_most_applied_companies(
            mock_db_session,
            test_user.id,
            limit=5
        )
        
        # Assertions
        assert len(companies) == 3
        assert companies[0] == ("TechCorp", 5)

    async def test_export_application_data(self, application_manager, mock_db_session, test_user):
        """Test exporting application data for user."""
        # Mock applications with related data
        mock_applications = [MagicMock(), MagicMock()]
        for app in mock_applications:
            app.job.title = "Test Job"
            app.job.company = "Test Company"
            app.status = "pending"
            app.applied_at = datetime.now()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_applications
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        export_data = await application_manager.export_applications(
            mock_db_session,
            test_user.id,
            format="dict"
        )
        
        # Assertions
        assert len(export_data) == 2
        assert "job_title" in export_data[0]
        assert "company" in export_data[0]
        assert "status" in export_data[0]
