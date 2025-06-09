"""
Job model for storing scraped job postings and managing job data.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

# Import Base from parent package - will be set by __init__.py  
try:
    from . import Base
except ImportError:
    # Fallback for direct imports during development
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class JobStatus(enum.Enum):
    """Job status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    FILLED = "filled"
    REMOVED = "removed"
    ARCHIVED = "archived"


class JobType(enum.Enum):
    """Job type enumeration."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    REMOTE = "remote"


class ExperienceLevel(enum.Enum):
    """Experience level enumeration."""
    ENTRY_LEVEL = "entry_level"
    MID_LEVEL = "mid_level"
    SENIOR_LEVEL = "senior_level"
    EXECUTIVE = "executive"
    INTERNSHIP = "internship"
    ASSOCIATE = "associate"


class Job(Base):
    """
    Job model for storing scraped job postings and related information.
    """
    __tablename__ = "jobs"

    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # ID from job site
    url = Column(Text, nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)  # linkedin, indeed, etc.
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Basic job information
    title = Column(String(300), nullable=False, index=True)
    company = Column(String(200), nullable=False, index=True)
    company_url = Column(String(500), nullable=True)
    company_logo_url = Column(String(500), nullable=True)
    
    # Location information
    location = Column(String(200), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    is_remote = Column(Boolean, default=False, index=True)
    
    # Job details
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    
    # Job categorization
    job_type = Column(Enum(JobType), nullable=True, index=True)
    experience_level = Column(Enum(ExperienceLevel), nullable=True, index=True)
    department = Column(String(100), nullable=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    
    # Salary information
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), default="USD")
    salary_period = Column(String(20), nullable=True)  # yearly, monthly, hourly
    
    # Skills and keywords
    required_skills = Column(JSON, nullable=True)  # Array of required skills
    preferred_skills = Column(JSON, nullable=True)  # Array of preferred skills
    keywords = Column(JSON, nullable=True)  # Extracted keywords
    
    # Application information
    apply_url = Column(Text, nullable=True)
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    posted_date = Column(DateTime(timezone=True), nullable=True)
    
    # Job status and metadata
    status = Column(Enum(JobStatus), default=JobStatus.ACTIVE, index=True)
    is_featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    
    # Matching and scoring
    match_score = Column(Float, nullable=True, index=True)  # AI-calculated match score
    match_reasons = Column(JSON, nullable=True)  # Reasons for match score
    is_bookmarked = Column(Boolean, default=False, index=True)
    is_hidden = Column(Boolean, default=False, index=True)
    
    # Scraping metadata
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    scraper_version = Column(String(50), nullable=True)
    raw_data = Column(JSON, nullable=True)  # Store original scraped data
    
    # Duplicate detection
    content_hash = Column(String(64), nullable=True, index=True)  # Hash of key content
    duplicate_of = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    
    # Application tracking
    application_count = Column(Integer, default=0)  # How many users applied
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    duplicate_jobs = relationship("Job", remote_side=[id])
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"
    
    @property
    def salary_range(self) -> str:
        """Get formatted salary range."""
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,} - {self.salary_max:,}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,}+"
        elif self.salary_max:
            return f"Up to {self.salary_currency} {self.salary_max:,}"
        else:
            return "Not specified"
    
    @property
    def is_expired(self) -> bool:
        """Check if job application deadline has passed."""
        if self.application_deadline:
            return self.application_deadline < func.now()
        return False
    
    @property
    def days_since_posted(self) -> int:
        """Get number of days since job was posted."""
        if self.posted_date:
            delta = func.now() - self.posted_date
            return delta.days
        return 0
    
    def calculate_match_score(self, user_skills: list, user_preferences: dict) -> float:
        """
        Calculate match score based on user skills and preferences.
        This is a simplified version - would be enhanced with AI/ML in practice.
        """
        score = 0.0
        max_score = 100.0
        
        # Skills matching (40% of total score)
        if self.required_skills and user_skills:
            required_skills_set = set([skill.lower() for skill in self.required_skills])
            user_skills_set = set([skill.lower() for skill in user_skills])
            skills_match = len(required_skills_set.intersection(user_skills_set))
            skills_score = min(40, (skills_match / len(required_skills_set)) * 40)
            score += skills_score
        
        # Location preference (20% of total score)
        if user_preferences.get('preferred_locations') and self.location:
            preferred_locations = [loc.lower() for loc in user_preferences['preferred_locations']]
            if any(loc in self.location.lower() for loc in preferred_locations) or self.is_remote:
                score += 20
        
        # Job type preference (20% of total score)
        if user_preferences.get('preferred_job_types') and self.job_type:
            if self.job_type.value in user_preferences['preferred_job_types']:
                score += 20
        
        # Salary preference (20% of total score)
        if user_preferences.get('preferred_salary_min') and self.salary_min:
            if self.salary_min >= user_preferences['preferred_salary_min']:
                score += 20
        elif not user_preferences.get('preferred_salary_min'):
            score += 10  # Partial score if no salary preference
        
        self.match_score = min(score, max_score)
        return self.match_score
    
    def to_dict(self) -> dict:
        """Convert job to dictionary."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "url": self.url,
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "company_url": self.company_url,
            "location": self.location,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "is_remote": self.is_remote,
            "description": self.description,
            "requirements": self.requirements,
            "job_type": self.job_type.value if self.job_type else None,
            "experience_level": self.experience_level.value if self.experience_level else None,
            "salary_range": self.salary_range,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "apply_url": self.apply_url,
            "application_deadline": self.application_deadline,
            "posted_date": self.posted_date,
            "status": self.status.value if self.status else None,
            "match_score": self.match_score,
            "match_reasons": self.match_reasons,
            "is_bookmarked": self.is_bookmarked,
            "is_hidden": self.is_hidden,
            "days_since_posted": self.days_since_posted,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }