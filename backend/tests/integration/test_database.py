"""
Database integration tests for the job automation system.

Tests database operations, data integrity, migrations, and performance.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.document import Document
from app.models.application_history import ApplicationHistory


class TestDatabaseOperations:
    """Test suite for database operations and integrity."""

    async def test_database_connection(self, db_session: AsyncSession):
        """Test basic database connectivity."""
        result = await db_session.execute(text("SELECT 1 as test"))
        assert result.scalar() == 1

    async def test_table_existence(self, db_session: AsyncSession):
        """Test that all required tables exist."""
        # Get database inspector
        inspector = inspect(db_session.bind)
        
        # Expected tables based on models
        expected_tables = [
            "users",
            "jobs", 
            "applications",
            "documents",
            "application_history",
            "saved_jobs",
            "job_alerts",
            "notifications"
        ]
        
        existing_tables = await db_session.run_sync(
            lambda sync_session: inspector.get_table_names()
        )
        
        for table in expected_tables:
            assert table in existing_tables, f"Table {table} does not exist"

    async def test_user_crud_operations(self, db_session: AsyncSession):
        """Test CRUD operations for User model."""
        # Create
        user = User(
            email="crud_test@example.com",
            full_name="CRUD Test User",
            hashed_password="hashed_password_123",
            is_active=True,
            skills=["Python", "SQL"],
            experience_years=3
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        created_user_id = user.id
        
        # Read
        retrieved_user = await db_session.get(User, created_user_id)
        assert retrieved_user is not None
        assert retrieved_user.email == "crud_test@example.com"
        assert retrieved_user.skills == ["Python", "SQL"]
        
        # Update
        retrieved_user.full_name = "Updated CRUD User"
        retrieved_user.skills.append("FastAPI")
        await db_session.commit()
        
        updated_user = await db_session.get(User, created_user_id)
        assert updated_user.full_name == "Updated CRUD User"
        assert "FastAPI" in updated_user.skills
        
        # Delete
        await db_session.delete(updated_user)
        await db_session.commit()
        
        deleted_user = await db_session.get(User, created_user_id)
        assert deleted_user is None

    async def test_job_crud_operations(self, db_session: AsyncSession):
        """Test CRUD operations for Job model."""
        # Create
        job = Job(
            title="Database Test Job",
            company="Test Company",
            location="Test City",
            job_type="full-time",
            salary_min=80000,
            salary_max=120000,
            description="Test job description",
            requirements=["Python", "PostgreSQL"],
            url="https://test.com/job/1",
            source="test_source",
            is_active=True
        )
        
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        assert job.id is not None
        assert job.created_at is not None
        
        # Test job search functionality
        search_result = await db_session.execute(
            text("SELECT * FROM jobs WHERE title ILIKE :search_term"),
            {"search_term": "%Database%"}
        )
        found_job = search_result.fetchone()
        assert found_job is not None

    async def test_application_with_relationships(self, db_session: AsyncSession, test_user: User, test_job: Job):
        """Test Application model with foreign key relationships."""
        # Create application
        application = Application(
            user_id=test_user.id,
            job_id=test_job.id,
            status="pending",
            application_method="automated",
            notes="Test application"
        )
        
        db_session.add(application)
        await db_session.commit()
        await db_session.refresh(application)
        
        # Test relationships
        assert application.user_id == test_user.id
        assert application.job_id == test_job.id
        assert application.applied_at is not None
        
        # Test cascade behavior (if implemented)
        application_id = application.id
        
        # Create application history
        history = ApplicationHistory(
            application_id=application_id,
            action_type="status_change",
            old_data={"status": "pending"},
            new_data={"status": "interview_scheduled"},
            changed_at=datetime.now()
        )
        
        db_session.add(history)
        await db_session.commit()
        
        # Verify relationship
        history_count = await db_session.execute(
            text("SELECT COUNT(*) FROM application_history WHERE application_id = :app_id"),
            {"app_id": application_id}
        )
        assert history_count.scalar() == 1

    async def test_data_integrity_constraints(self, db_session: AsyncSession):
        """Test database constraints and data integrity."""
        # Test unique email constraint
        user1 = User(
            email="unique_test@example.com",
            full_name="User 1",
            hashed_password="password1"
        )
        
        user2 = User(
            email="unique_test@example.com",  # Same email
            full_name="User 2", 
            hashed_password="password2"
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        
        # Should raise integrity error for duplicate email
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            await db_session.commit()
        
        await db_session.rollback()

    async def test_foreign_key_constraints(self, db_session: AsyncSession):
        """Test foreign key constraints."""
        # Try to create application with non-existent user_id
        invalid_application = Application(
            user_id=99999,  # Non-existent user
            job_id=1,
            status="pending"
        )
        
        db_session.add(invalid_application)
        
        # Should raise foreign key constraint error
        with pytest.raises(Exception):
            await db_session.commit()
        
        await db_session.rollback()

    async def test_json_field_operations(self, db_session: AsyncSession):
        """Test JSON field operations (skills, job_preferences, etc.)."""
        user = User(
            email="json_test@example.com",
            full_name="JSON Test User",
            hashed_password="password",
            skills=["Python", "JavaScript", "SQL"],
            job_preferences={
                "job_types": ["full-time", "contract"],
                "remote_preference": "hybrid",
                "salary_range": [80000, 120000]
            }
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Test JSON field queries
        result = await db_session.execute(
            text("SELECT skills, job_preferences FROM users WHERE id = :user_id"),
            {"user_id": user.id}
        )
        row = result.fetchone()
        
        assert "Python" in row.skills
        assert row.job_preferences["remote_preference"] == "hybrid"
        
        # Test JSON field updates
        user.skills.append("React")
        user.job_preferences["salary_range"] = [90000, 130000]
        
        await db_session.commit()
        await db_session.refresh(user)
        
        assert "React" in user.skills
        assert user.job_preferences["salary_range"] == [90000, 130000]

    async def test_database_indexing_performance(self, db_session: AsyncSession):
        """Test database index performance."""
        # Create multiple jobs for testing
        jobs = []
        for i in range(100):
            job = Job(
                title=f"Performance Test Job {i}",
                company=f"Company {i % 10}",
                location=["San Francisco", "New York", "Remote"][i % 3],
                job_type="full-time",
                salary_min=80000 + (i * 1000),
                salary_max=120000 + (i * 1000),
                description=f"Job description {i}",
                url=f"https://company{i%10}.com/job/{i}",
                source="test",
                is_active=True
            )
            jobs.append(job)
        
        db_session.add_all(jobs)
        await db_session.commit()
        
        # Test indexed search performance
        import time
        
        # Search by title (should be indexed)
        start_time = time.time()
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM jobs WHERE title ILIKE :search"),
            {"search": "%Performance%"}
        )
        search_time = time.time() - start_time
        
        count = result.scalar()
        assert count == 100
        assert search_time < 1.0  # Should be fast with proper indexing
        
        # Search by location (should also be indexed)
        start_time = time.time()
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM jobs WHERE location = :location"),
            {"location": "San Francisco"}
        )
        location_search_time = time.time() - start_time
        
        assert location_search_time < 1.0

    async def test_transaction_rollback(self, db_session: AsyncSession):
        """Test transaction rollback functionality."""
        # Start with known state
        initial_count = await db_session.execute(text("SELECT COUNT(*) FROM users"))
        initial_count = initial_count.scalar()
        
        try:
            # Create a user
            user = User(
                email="rollback_test@example.com",
                full_name="Rollback Test",
                hashed_password="password"
            )
            db_session.add(user)
            await db_session.flush()  # Execute but don't commit
            
            # Verify user exists in current transaction
            temp_count = await db_session.execute(text("SELECT COUNT(*) FROM users"))
            assert temp_count.scalar() == initial_count + 1
            
            # Force an error to trigger rollback
            raise Exception("Intentional error for rollback test")
            
        except Exception:
            await db_session.rollback()
        
        # Verify rollback worked
        final_count = await db_session.execute(text("SELECT COUNT(*) FROM users"))
        assert final_count.scalar() == initial_count

    async def test_concurrent_access(self, async_engine):
        """Test concurrent database access."""
        async_session_maker = sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def create_user(user_id):
            async with async_session_maker() as session:
                user = User(
                    email=f"concurrent_{user_id}@example.com",
                    full_name=f"Concurrent User {user_id}",
                    hashed_password="password"
                )
                session.add(user)
                await session.commit()
                return user.id
        
        # Create 20 users concurrently
        tasks = [create_user(i) for i in range(20)]
        user_ids = await asyncio.gather(*tasks)
        
        # Verify all users were created
        assert len(user_ids) == 20
        assert all(uid is not None for uid in user_ids)
        
        # Verify uniqueness
        assert len(set(user_ids)) == 20

    async def test_database_migration_compatibility(self, db_session: AsyncSession):
        """Test database schema compatibility."""
        # Check that all model columns exist in database
        models_to_check = [User, Job, Application, Document]
        
        inspector = inspect(db_session.bind)
        
        for model in models_to_check:
            table_name = model.__tablename__
            
            # Get table columns from database
            db_columns = await db_session.run_sync(
                lambda sync_session: inspector.get_columns(table_name)
            )
            db_column_names = {col['name'] for col in db_columns}
            
            # Get model columns
            model_columns = {col.name for col in model.__table__.columns}
            
            # Check that all model columns exist in database
            missing_columns = model_columns - db_column_names
            assert not missing_columns, f"Missing columns in {table_name}: {missing_columns}"

    async def test_data_archival_and_cleanup(self, db_session: AsyncSession):
        """Test data archival and cleanup procedures."""
        # Create old job that should be archived
        old_job = Job(
            title="Old Job",
            company="Old Company",
            location="Old Location",
            job_type="full-time",
            description="Old job description",
            url="https://old.com/job",
            source="old_source",
            is_active=True,
            created_at=datetime.now() - timedelta(days=365)  # 1 year old
        )
        
        db_session.add(old_job)
        await db_session.commit()
        
        # Test archival query
        old_jobs_query = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM jobs 
                WHERE created_at < :cutoff_date AND is_active = true
            """),
            {"cutoff_date": datetime.now() - timedelta(days=90)}
        )
        
        old_jobs_count = old_jobs_query.scalar()
        assert old_jobs_count >= 1
        
        # Test cleanup operation
        await db_session.execute(
            text("""
                UPDATE jobs 
                SET is_active = false 
                WHERE created_at < :cutoff_date
            """),
            {"cutoff_date": datetime.now() - timedelta(days=90)}
        )
        await db_session.commit()
        
        # Verify cleanup
        active_old_jobs = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM jobs 
                WHERE created_at < :cutoff_date AND is_active = true
            """),
            {"cutoff_date": datetime.now() - timedelta(days=90)}
        )
        
        assert active_old_jobs.scalar() == 0

    async def test_database_backup_restore_simulation(self, db_session: AsyncSession):
        """Simulate database backup and restore procedures."""
        # Create test data
        test_user = User(
            email="backup_test@example.com",
            full_name="Backup Test User",
            hashed_password="password"
        )
        
        db_session.add(test_user)
        await db_session.commit()
        
        # Simulate backup by exporting user data
        export_query = await db_session.execute(
            text("SELECT email, full_name, created_at FROM users WHERE email = :email"),
            {"email": "backup_test@example.com"}
        )
        backup_data = export_query.fetchone()
        
        assert backup_data is not None
        assert backup_data.email == "backup_test@example.com"
        
        # Simulate data loss
        await db_session.execute(
            text("DELETE FROM users WHERE email = :email"),
            {"email": "backup_test@example.com"}
        )
        await db_session.commit()
        
        # Verify deletion
        check_query = await db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": "backup_test@example.com"}
        )
        assert check_query.scalar() == 0
        
        # Simulate restore
        restored_user = User(
            email=backup_data.email,
            full_name=backup_data.full_name,
            hashed_password="password",
            created_at=backup_data.created_at
        )
        
        db_session.add(restored_user)
        await db_session.commit()
        
        # Verify restoration
        verify_query = await db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": "backup_test@example.com"}
        )
        assert verify_query.scalar() == 1

    async def test_connection_pooling(self, async_engine):
        """Test database connection pooling behavior."""
        # Test multiple concurrent connections
        async def test_connection(conn_id):
            async_session_maker = sessionmaker(
                async_engine, class_=AsyncSession, expire_on_commit=False
            )
            
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT :conn_id as id"), {"conn_id": conn_id})
                return result.scalar()
        
        # Create 50 concurrent connections
        tasks = [test_connection(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All connections should succeed
        assert len(results) == 50
        assert results == list(range(50))

    async def test_database_constraints_validation(self, db_session: AsyncSession):
        """Test various database constraints."""
        # Test NOT NULL constraints
        invalid_user = User(
            email=None,  # Should not be null
            full_name="Test User",
            hashed_password="password"
        )
        
        db_session.add(invalid_user)
        
        with pytest.raises(Exception):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Test CHECK constraints (if any)
        # Example: salary_min should not be greater than salary_max
        invalid_job = Job(
            title="Invalid Salary Job",
            company="Test Company",
            location="Test City",
            salary_min=150000,
            salary_max=100000,  # Max less than min
            description="Test job",
            url="https://test.com/job"
        )
        
        db_session.add(invalid_job)
        
        # If CHECK constraint exists, this should fail
        try:
            await db_session.commit()
            # If no constraint, manually verify the logic issue
            assert invalid_job.salary_min <= invalid_job.salary_max, "Salary constraint violated"
        except Exception:
            await db_session.rollback()

    async def test_full_text_search(self, db_session: AsyncSession):
        """Test full-text search functionality."""
        # Create jobs with searchable content
        search_jobs = [
            Job(
                title="Senior Python Developer",
                company="TechCorp",
                location="San Francisco",
                description="Python Django FastAPI machine learning",
                requirements=["Python", "Django", "ML"],
                url="https://techcorp.com/python-dev",
                source="test"
            ),
            Job(
                title="Frontend React Developer", 
                company="WebCorp",
                location="New York",
                description="React TypeScript JavaScript frontend",
                requirements=["React", "TypeScript"],
                url="https://webcorp.com/react-dev",
                source="test"
            )
        ]
        
        db_session.add_all(search_jobs)
        await db_session.commit()
        
        # Test text search
        python_search = await db_session.execute(
            text("""
                SELECT title, description FROM jobs 
                WHERE description ILIKE :search_term OR title ILIKE :search_term
            """),
            {"search_term": "%Python%"}
        )
        
        python_results = python_search.fetchall()
        assert len(python_results) == 1
        assert "Python" in python_results[0].title
        
        # Test multi-term search
        tech_search = await db_session.execute(
            text("""
                SELECT title FROM jobs 
                WHERE (description ILIKE :term1 OR title ILIKE :term1)
                AND (description ILIKE :term2 OR title ILIKE :term2)
            """),
            {"term1": "%Developer%", "term2": "%Senior%"}
        )
        
        tech_results = tech_search.fetchall()
        assert len(tech_results) == 1
        assert "Senior" in tech_results[0].title
