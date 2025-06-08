"""
Unit tests for user service functionality.

Tests user-related operations including profile management,
authentication, and user preferences.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService
from app.core.exceptions import UserNotFoundError, EmailAlreadyExistsError


class TestUserService:
    """Test suite for UserService class."""

    @pytest.fixture
    def user_service(self):
        """Create UserService instance for testing."""
        return UserService()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_user_create(self):
        """Sample user creation data."""
        return UserCreate(
            email="newuser@example.com",
            password="securepassword123",
            full_name="New User",
            phone_number="+1555987654",
            location="Los Angeles, CA",
            skills=["Python", "Django"],
            experience_years=3,
            education="Bachelor's in Computer Science"
        )

    @pytest.fixture
    def sample_user_update(self):
        """Sample user update data."""
        return UserUpdate(
            full_name="Updated User Name",
            location="Seattle, WA",
            skills=["Python", "FastAPI", "React"],
            experience_years=4,
            preferred_salary_min=90000,
            preferred_salary_max=130000
        )

    async def test_create_user_success(self, user_service, mock_db_session, sample_user_create):
        """Test successful user creation."""
        # Mock database query to check email doesn't exist
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Call service method
        created_user = await user_service.create_user(mock_db_session, sample_user_create)
        
        # Assertions
        assert created_user.email == sample_user_create.email
        assert created_user.full_name == sample_user_create.full_name
        assert created_user.is_active is True
        assert created_user.is_superuser is False
        assert verify_password(sample_user_create.password, created_user.hashed_password)
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    async def test_create_user_email_exists(self, user_service, mock_db_session, sample_user_create):
        """Test user creation with existing email."""
        # Mock existing user
        existing_user = MagicMock()
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user
        
        # Should raise exception
        with pytest.raises(EmailAlreadyExistsError):
            await user_service.create_user(mock_db_session, sample_user_create)
        
        # Should not add to database
        mock_db_session.add.assert_not_called()

    async def test_get_user_by_email_found(self, user_service, mock_db_session, test_user):
        """Test getting user by email when user exists."""
        # Mock database query
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = test_user
        
        # Call service method
        found_user = await user_service.get_user_by_email(mock_db_session, test_user.email)
        
        # Assertions
        assert found_user == test_user
        assert found_user.email == test_user.email

    async def test_get_user_by_email_not_found(self, user_service, mock_db_session):
        """Test getting user by email when user doesn't exist."""
        # Mock database query returning None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Call service method
        found_user = await user_service.get_user_by_email(mock_db_session, "nonexistent@example.com")
        
        # Should return None
        assert found_user is None

    async def test_get_user_by_id_found(self, user_service, mock_db_session, test_user):
        """Test getting user by ID when user exists."""
        # Mock database query
        mock_db_session.get.return_value = test_user
        
        # Call service method
        found_user = await user_service.get_user_by_id(mock_db_session, test_user.id)
        
        # Assertions
        assert found_user == test_user
        mock_db_session.get.assert_called_once_with(User, test_user.id)

    async def test_get_user_by_id_not_found(self, user_service, mock_db_session):
        """Test getting user by ID when user doesn't exist."""
        # Mock database query returning None
        mock_db_session.get.return_value = None
        
        # Call service method
        found_user = await user_service.get_user_by_id(mock_db_session, 999)
        
        # Should return None
        assert found_user is None

    async def test_update_user_success(self, user_service, mock_db_session, test_user, sample_user_update):
        """Test successful user update."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        
        # Call service method
        updated_user = await user_service.update_user(mock_db_session, test_user.id, sample_user_update)
        
        # Assertions
        assert updated_user.full_name == sample_user_update.full_name
        assert updated_user.location == sample_user_update.location
        assert updated_user.skills == sample_user_update.skills
        assert updated_user.experience_years == sample_user_update.experience_years
        assert updated_user.preferred_salary_min == sample_user_update.preferred_salary_min
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    async def test_update_user_not_found(self, user_service, mock_db_session, sample_user_update):
        """Test updating user that doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Should raise exception
        with pytest.raises(UserNotFoundError):
            await user_service.update_user(mock_db_session, 999, sample_user_update)

    async def test_update_user_partial(self, user_service, mock_db_session, test_user):
        """Test partial user update with only some fields."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        
        # Partial update data
        partial_update = UserUpdate(full_name="Partially Updated Name")
        
        # Call service method
        updated_user = await user_service.update_user(mock_db_session, test_user.id, partial_update)
        
        # Only updated field should change
        assert updated_user.full_name == "Partially Updated Name"
        # Other fields should remain unchanged
        assert updated_user.email == test_user.email
        assert updated_user.location == test_user.location

    async def test_delete_user_success(self, user_service, mock_db_session, test_user):
        """Test successful user deletion."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        
        # Call service method
        result = await user_service.delete_user(mock_db_session, test_user.id)
        
        # Assertions
        assert result is True
        mock_db_session.delete.assert_called_once_with(test_user)
        mock_db_session.commit.assert_called_once()

    async def test_delete_user_not_found(self, user_service, mock_db_session):
        """Test deleting user that doesn't exist."""
        # Mock database get returning None
        mock_db_session.get.return_value = None
        
        # Should raise exception
        with pytest.raises(UserNotFoundError):
            await user_service.delete_user(mock_db_session, 999)

    async def test_deactivate_user_success(self, user_service, mock_db_session, test_user):
        """Test successful user deactivation."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        
        # Call service method
        deactivated_user = await user_service.deactivate_user(mock_db_session, test_user.id)
        
        # Assertions
        assert deactivated_user.is_active is False
        mock_db_session.commit.assert_called_once()

    async def test_activate_user_success(self, user_service, mock_db_session, test_user):
        """Test successful user activation."""
        # Set user as inactive
        test_user.is_active = False
        mock_db_session.get.return_value = test_user
        
        # Call service method
        activated_user = await user_service.activate_user(mock_db_session, test_user.id)
        
        # Assertions
        assert activated_user.is_active is True
        mock_db_session.commit.assert_called_once()

    async def test_update_password_success(self, user_service, mock_db_session, test_user):
        """Test successful password update."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        
        new_password = "newpassword123"
        old_hashed_password = test_user.hashed_password
        
        # Call service method
        updated_user = await user_service.update_password(mock_db_session, test_user.id, new_password)
        
        # Assertions
        assert updated_user.hashed_password != old_hashed_password
        assert verify_password(new_password, updated_user.hashed_password)
        mock_db_session.commit.assert_called_once()

    async def test_get_user_statistics(self, user_service, mock_db_session):
        """Test getting user statistics."""
        # Mock database query results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100  # Total users
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        stats = await user_service.get_user_statistics(mock_db_session)
        
        # Assertions
        assert "total_users" in stats
        assert "active_users" in stats
        assert "new_users_this_month" in stats

    async def test_search_users(self, user_service, mock_db_session):
        """Test user search functionality."""
        # Mock database query results
        mock_users = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        results = await user_service.search_users(
            mock_db_session, 
            query="test",
            skills=["Python"],
            location="San Francisco",
            limit=10,
            offset=0
        )
        
        # Assertions
        assert len(results) == 2
        mock_db_session.execute.assert_called()

    async def test_update_user_preferences(self, user_service, mock_db_session, test_user):
        """Test updating user job preferences."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        
        new_preferences = {
            "job_types": ["full-time", "contract"],
            "industries": ["technology", "finance"],
            "remote_preference": "remote",
            "salary_range": [100000, 150000]
        }
        
        # Call service method
        updated_user = await user_service.update_user_preferences(
            mock_db_session, 
            test_user.id, 
            new_preferences
        )
        
        # Assertions
        assert updated_user.job_preferences == new_preferences
        mock_db_session.commit.assert_called_once()

    async def test_add_user_skill(self, user_service, mock_db_session, test_user):
        """Test adding a skill to user."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        original_skills = test_user.skills.copy()
        
        # Call service method
        updated_user = await user_service.add_user_skill(mock_db_session, test_user.id, "Kubernetes")
        
        # Assertions
        assert "Kubernetes" in updated_user.skills
        assert len(updated_user.skills) == len(original_skills) + 1

    async def test_remove_user_skill(self, user_service, mock_db_session, test_user):
        """Test removing a skill from user."""
        # Mock database get
        mock_db_session.get.return_value = test_user
        skill_to_remove = test_user.skills[0]  # Remove first skill
        
        # Call service method
        updated_user = await user_service.remove_user_skill(mock_db_session, test_user.id, skill_to_remove)
        
        # Assertions
        assert skill_to_remove not in updated_user.skills

    @patch('app.services.user_service.send_welcome_email')
    async def test_create_user_sends_welcome_email(self, mock_send_email, user_service, mock_db_session, sample_user_create):
        """Test that creating a user sends a welcome email."""
        # Mock database query to check email doesn't exist
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Call service method
        created_user = await user_service.create_user(mock_db_session, sample_user_create)
        
        # Verify welcome email was sent
        mock_send_email.assert_called_once_with(created_user.email, created_user.full_name)

    async def test_get_users_by_skill(self, user_service, mock_db_session):
        """Test getting users by specific skill."""
        # Mock database query results
        mock_users = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        users = await user_service.get_users_by_skill(mock_db_session, "Python")
        
        # Assertions
        assert len(users) == 2

    async def test_get_users_by_location(self, user_service, mock_db_session):
        """Test getting users by location."""
        # Mock database query results
        mock_users = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db_session.execute.return_value = mock_result
        
        # Call service method
        users = await user_service.get_users_by_location(mock_db_session, "San Francisco")
        
        # Assertions
        assert len(users) == 1
