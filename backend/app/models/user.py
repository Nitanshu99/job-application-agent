"""
User model for the job automation system.
Handles user authentication, profiles, and preferences.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from passlib.context import CryptContext

# Import Base from parent package - will be set by __init__.py
try:
    from . import Base
except ImportError:
    # Fallback for direct imports during development
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """
    User model with authentication and profile information.
    """
    __tablename__ = "users"

    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    
    # Profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Professional information
    current_title = Column(String(200), nullable=True)
    current_company = Column(String(200), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    
    # Resume/CV information
    summary = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True)  # Store as JSON array
    experience = Column(JSON, nullable=True)  # Store structured experience data
    education = Column(JSON, nullable=True)  # Store education history
    certifications = Column(JSON, nullable=True)  # Store certifications
    
    # Job search preferences
    preferred_locations = Column(JSON, nullable=True)  # Array of locations
    preferred_job_types = Column(JSON, nullable=True)  # Array of job types
    preferred_salary_min = Column(Integer, nullable=True)
    preferred_salary_max = Column(Integer, nullable=True)
    preferred_companies = Column(JSON, nullable=True)  # Array of company names
    blacklisted_companies = Column(JSON, nullable=True)  # Companies to avoid
    
    # Application preferences
    auto_apply_enabled = Column(Boolean, default=False)
    daily_application_limit = Column(Integer, default=10)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Email verification
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"
    
    def verify_password(self, plain_password: str) -> bool:
        """Verify a password against the hashed password."""
        return pwd_context.verify(plain_password, self.hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)
    
    def set_password(self, password: str):
        """Set a new password for the user."""
        self.hashed_password = self.hash_password(password)
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding sensitive data)."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "current_title": self.current_title,
            "current_company": self.current_company,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "portfolio_url": self.portfolio_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "preferred_locations": self.preferred_locations,
            "preferred_job_types": self.preferred_job_types,
            "auto_apply_enabled": self.auto_apply_enabled,
            "daily_application_limit": self.daily_application_limit,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login
        }