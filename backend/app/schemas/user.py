"""
User Pydantic schemas for request/response validation and serialization.

Handles user profile data, authentication, and user preferences for the job automation system.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    location: Optional[str] = Field(None, max_length=200, description="User's location")
    skills: Optional[List[str]] = Field(default_factory=list, description="List of user skills")
    experience_years: Optional[int] = Field(None, ge=0, le=70, description="Years of experience")
    education: Optional[str] = Field(None, max_length=500, description="Educational background")
    preferred_salary_min: Optional[int] = Field(None, ge=0, description="Minimum preferred salary")
    preferred_salary_max: Optional[int] = Field(None, ge=0, description="Maximum preferred salary")
    preferred_locations: Optional[List[str]] = Field(default_factory=list, description="Preferred work locations")
    job_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Job preferences and settings")
    bio: Optional[str] = Field(None, max_length=1000, description="User bio/summary")
    website_url: Optional[str] = Field(None, description="Personal website or portfolio URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not re.match(r'^\+?[\d\s\-\(\)]{10,}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('preferred_salary_max')
    def validate_salary_range(cls, v, values):
        if v and 'preferred_salary_min' in values and values['preferred_salary_min']:
            if v < values['preferred_salary_min']:
                raise ValueError('Maximum salary must be greater than or equal to minimum salary')
        return v

    @validator('skills')
    def validate_skills(cls, v):
        if v and len(v) > 100:
            raise ValueError('Too many skills listed (maximum 100)')
        return v

    @validator('full_name')
    def validate_full_name(cls, v):
        if not re.match(r'^[a-zA-Z\s\'-\.]+$', v):
            raise ValueError('Full name contains invalid characters')
        return v


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(..., min_length=8, max_length=128, description="User's password")
    confirm_password: Optional[str] = Field(None, description="Password confirmation")

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=70)
    education: Optional[str] = Field(None, max_length=500)
    preferred_salary_min: Optional[int] = Field(None, ge=0)
    preferred_salary_max: Optional[int] = Field(None, ge=0)
    preferred_locations: Optional[List[str]] = None
    job_preferences: Optional[Dict[str, Any]] = None
    bio: Optional[str] = Field(None, max_length=1000)
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not re.match(r'^\+?[\d\s\-\(\)]{10,}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('preferred_salary_max')
    def validate_salary_range(cls, v, values):
        if v and 'preferred_salary_min' in values and values['preferred_salary_min']:
            if v < values['preferred_salary_min']:
                raise ValueError('Maximum salary must be greater than or equal to minimum salary')
        return v

    @validator('skills')
    def validate_skills(cls, v):
        if v and len(v) > 100:
            raise ValueError('Too many skills listed (maximum 100)')
        return v

    @validator('full_name')
    def validate_full_name(cls, v):
        if v and not re.match(r'^[a-zA-Z\s\'-\.]+$', v):
            raise ValueError('Full name contains invalid characters')
        return v


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_new_password: str = Field(..., description="New password confirmation")

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class UserResponse(UserBase):
    """Schema for user response data."""
    
    id: int
    is_active: bool
    is_superuser: bool
    is_verified: bool = False
    profile_completed: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    """Simplified user schema for listings and references."""
    
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserPreferences(BaseModel):
    """Schema for user job preferences and settings."""
    
    job_types: Optional[List[str]] = Field(default_factory=list, description="Preferred job types")
    industries: Optional[List[str]] = Field(default_factory=list, description="Preferred industries")
    remote_preference: Optional[str] = Field("hybrid", description="Remote work preference")
    auto_apply_enabled: bool = Field(False, description="Enable automatic job applications")
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_job_matches": True,
            "email_applications": True,
            "email_interviews": True,
            "push_notifications": False
        },
        description="Notification preferences"
    )
    search_radius: Optional[int] = Field(25, ge=0, le=100, description="Job search radius in miles")
    salary_expectations: Optional[Dict[str, int]] = Field(
        default_factory=dict,
        description="Salary expectations by job type"
    )

    @validator('remote_preference')
    def validate_remote_preference(cls, v):
        valid_options = ['remote', 'hybrid', 'onsite', 'flexible']
        if v and v not in valid_options:
            raise ValueError(f'Remote preference must be one of: {valid_options}')
        return v

    @validator('job_types')
    def validate_job_types(cls, v):
        valid_types = ['full-time', 'part-time', 'contract', 'temporary', 'internship', 'volunteer']
        if v:
            for job_type in v:
                if job_type not in valid_types:
                    raise ValueError(f'Invalid job type: {job_type}. Must be one of: {valid_types}')
        return v


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""
    
    job_types: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    auto_apply_enabled: Optional[bool] = None
    notification_preferences: Optional[Dict[str, bool]] = None
    search_radius: Optional[int] = Field(None, ge=0, le=100)
    salary_expectations: Optional[Dict[str, int]] = None

    @validator('remote_preference')
    def validate_remote_preference(cls, v):
        if v:
            valid_options = ['remote', 'hybrid', 'onsite', 'flexible']
            if v not in valid_options:
                raise ValueError(f'Remote preference must be one of: {valid_options}')
        return v

    @validator('job_types')
    def validate_job_types(cls, v):
        if v:
            valid_types = ['full-time', 'part-time', 'contract', 'temporary', 'internship', 'volunteer']
            for job_type in v:
                if job_type not in valid_types:
                    raise ValueError(f'Invalid job type: {job_type}. Must be one of: {valid_types}')
        return v


class UserStats(BaseModel):
    """Schema for user statistics and analytics."""
    
    total_applications: int = 0
    pending_applications: int = 0
    interview_count: int = 0
    offer_count: int = 0
    rejection_count: int = 0
    response_rate: float = 0.0
    average_application_time: Optional[float] = None
    saved_jobs_count: int = 0
    document_count: int = 0
    profile_completion_percentage: float = 0.0

    class Config:
        from_attributes = True