"""
Job Pydantic schemas for request/response validation and serialization.

Handles job posting data, job search criteria, and job matching for the automation system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator
import re


class JobTypeEnum(str, Enum):
    """Enumeration for job types."""
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    VOLUNTEER = "volunteer"


class ExperienceLevelEnum(str, Enum):
    """Enumeration for experience levels."""
    ENTRY_LEVEL = "entry-level"
    JUNIOR = "junior"
    MID_LEVEL = "mid-level"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class JobSourceEnum(str, Enum):
    """Enumeration for job sources."""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    COMPANY_WEBSITE = "company_website"
    GLASSDOOR = "glassdoor"
    MONSTER = "monster"
    ZIPRECRUITER = "ziprecruiter"
    CUSTOM_PORTAL = "custom_portal"
    MANUAL = "manual"


class RemoteTypeEnum(str, Enum):
    """Enumeration for remote work types."""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class JobBase(BaseModel):
    """Base job schema with common fields."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Job title")
    company: str = Field(..., min_length=1, max_length=200, description="Company name")
    location: Optional[str] = Field(None, max_length=200, description="Job location")
    job_type: Optional[JobTypeEnum] = Field(JobTypeEnum.FULL_TIME, description="Type of employment")
    remote_type: Optional[RemoteTypeEnum] = Field(None, description="Remote work arrangement")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary")
    salary_currency: Optional[str] = Field("USD", max_length=3, description="Salary currency code")
    description: Optional[str] = Field(None, max_length=10000, description="Job description")
    requirements: Optional[List[str]] = Field(default_factory=list, description="Job requirements")
    responsibilities: Optional[List[str]] = Field(default_factory=list, description="Job responsibilities")
    benefits: Optional[List[str]] = Field(default_factory=list, description="Job benefits")
    skills: Optional[List[str]] = Field(default_factory=list, description="Required skills")
    experience_level: Optional[ExperienceLevelEnum] = Field(None, description="Required experience level")
    experience_years_min: Optional[int] = Field(None, ge=0, le=50, description="Minimum years of experience")
    experience_years_max: Optional[int] = Field(None, ge=0, le=50, description="Maximum years of experience")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")
    department: Optional[str] = Field(None, max_length=100, description="Department or team")
    url: Optional[HttpUrl] = Field(None, description="Original job posting URL")
    application_url: Optional[HttpUrl] = Field(None, description="Direct application URL")
    company_website: Optional[HttpUrl] = Field(None, description="Company website URL")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email for applications")
    contact_person: Optional[str] = Field(None, max_length=100, description="Contact person name")
    source: JobSourceEnum = Field(JobSourceEnum.MANUAL, description="Source where job was found")
    external_id: Optional[str] = Field(None, max_length=100, description="External job ID from source")
    application_deadline: Optional[datetime] = Field(None, description="Application deadline")
    is_active: bool = Field(True, description="Whether the job is active")
    is_featured: bool = Field(False, description="Whether the job is featured")
    tags: Optional[List[str]] = Field(default_factory=list, description="Custom tags for the job")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @validator('salary_max')
    def validate_salary_range(cls, v, values):
        if v and 'salary_min' in values and values['salary_min']:
            if v < values['salary_min']:
                raise ValueError('Maximum salary must be greater than or equal to minimum salary')
        return v

    @validator('experience_years_max')
    def validate_experience_range(cls, v, values):
        if v and 'experience_years_min' in values and values['experience_years_min']:
            if v < values['experience_years_min']:
                raise ValueError('Maximum experience must be greater than or equal to minimum experience')
        return v

    @validator('requirements', 'responsibilities', 'benefits', 'skills', 'tags')
    def validate_lists(cls, v):
        if v and len(v) > 100:
            raise ValueError('List cannot contain more than 100 items')
        return v

    @validator('description')
    def validate_description(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError('Description cannot be empty')
        return v


class JobCreate(JobBase):
    """Schema for creating a new job posting."""
    
    pass


class JobUpdate(BaseModel):
    """Schema for updating a job posting."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = Field(None, min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    job_type: Optional[JobTypeEnum] = None
    remote_type: Optional[RemoteTypeEnum] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    description: Optional[str] = Field(None, max_length=10000)
    requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    experience_level: Optional[ExperienceLevelEnum] = None
    experience_years_min: Optional[int] = Field(None, ge=0, le=50)
    experience_years_max: Optional[int] = Field(None, ge=0, le=50)
    industry: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    url: Optional[HttpUrl] = None
    application_url: Optional[HttpUrl] = None
    company_website: Optional[HttpUrl] = None
    contact_email: Optional[EmailStr] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    application_deadline: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('salary_max')
    def validate_salary_range(cls, v, values):
        if v and 'salary_min' in values and values['salary_min']:
            if v < values['salary_min']:
                raise ValueError('Maximum salary must be greater than or equal to minimum salary')
        return v

    @validator('experience_years_max')
    def validate_experience_range(cls, v, values):
        if v and 'experience_years_min' in values and values['experience_years_min']:
            if v < values['experience_years_min']:
                raise ValueError('Maximum experience must be greater than or equal to minimum experience')
        return v


class JobResponse(JobBase):
    """Schema for job response data."""
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    view_count: int = 0
    application_count: int = 0
    match_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Match score for user")

    class Config:
        from_attributes = True


class JobSummary(BaseModel):
    """Simplified job schema for listings."""
    
    id: int
    title: str
    company: str
    location: Optional[str]
    job_type: Optional[JobTypeEnum]
    salary_min: Optional[int]
    salary_max: Optional[int]
    remote_type: Optional[RemoteTypeEnum]
    source: JobSourceEnum
    created_at: datetime
    is_active: bool
    match_score: Optional[float] = None

    class Config:
        from_attributes = True


class JobSearch(BaseModel):
    """Schema for job search criteria."""
    
    keywords: Optional[str] = Field(None, max_length=200, description="Search keywords")
    title: Optional[str] = Field(None, max_length=200, description="Job title search")
    company: Optional[str] = Field(None, max_length=200, description="Company name search")
    location: Optional[str] = Field(None, max_length=200, description="Location search")
    job_types: Optional[List[JobTypeEnum]] = Field(None, description="Job types to include")
    remote_types: Optional[List[RemoteTypeEnum]] = Field(None, description="Remote work types")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary filter")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary filter")
    experience_levels: Optional[List[ExperienceLevelEnum]] = Field(None, description="Experience levels")
    industries: Optional[List[str]] = Field(None, description="Industry filters")
    skills: Optional[List[str]] = Field(None, description="Required skills")
    sources: Optional[List[JobSourceEnum]] = Field(None, description="Job sources to include")
    posted_since: Optional[datetime] = Field(None, description="Jobs posted since this date")
    application_deadline_before: Optional[datetime] = Field(None, description="Application deadline before")
    is_active: bool = Field(True, description="Only include active jobs")
    tags: Optional[List[str]] = Field(None, description="Job tags to filter by")
    radius: Optional[int] = Field(None, ge=0, le=100, description="Search radius in miles")
    exclude_companies: Optional[List[str]] = Field(None, description="Companies to exclude")
    min_match_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Minimum match score")
    
    # Pagination
    limit: int = Field(20, ge=1, le=100, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    
    # Sorting
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")

    @validator('sort_by')
    def validate_sort_by(cls, v):
        valid_fields = [
            'created_at', 'updated_at', 'title', 'company', 'salary_min', 
            'salary_max', 'match_score', 'view_count', 'application_count'
        ]
        if v and v not in valid_fields:
            raise ValueError(f'Sort field must be one of: {valid_fields}')
        return v


class JobMatch(BaseModel):
    """Schema for job matching results."""
    
    job_id: int
    match_score: float = Field(..., ge=0.0, le=100.0, description="Overall match score")
    skill_match: float = Field(..., ge=0.0, le=100.0, description="Skills match percentage")
    experience_match: float = Field(..., ge=0.0, le=100.0, description="Experience match percentage")
    location_match: float = Field(..., ge=0.0, le=100.0, description="Location match percentage")
    salary_match: float = Field(..., ge=0.0, le=100.0, description="Salary expectations match")
    matching_skills: List[str] = Field(default_factory=list, description="Skills that match")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills not in profile")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improving match")
    match_reasons: List[str] = Field(default_factory=list, description="Reasons for the match score")

    class Config:
        from_attributes = True


class JobAnalytics(BaseModel):
    """Schema for job analytics and statistics."""
    
    total_jobs: int = 0
    active_jobs: int = 0
    jobs_by_type: Dict[str, int] = Field(default_factory=dict)
    jobs_by_source: Dict[str, int] = Field(default_factory=dict)
    jobs_by_location: Dict[str, int] = Field(default_factory=dict)
    average_salary: Optional[float] = None
    salary_range: Optional[Dict[str, int]] = None
    most_common_skills: List[Dict[str, Union[str, int]]] = Field(default_factory=list)
    recent_job_count: int = 0
    trending_companies: List[Dict[str, Union[str, int]]] = Field(default_factory=list)

    class Config:
        from_attributes = True


class JobAlert(BaseModel):
    """Schema for job alert configuration."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Alert name")
    search_criteria: JobSearch = Field(..., description="Search criteria for the alert")
    frequency: str = Field("daily", regex="^(immediate|daily|weekly)$", description="Alert frequency")
    is_active: bool = Field(True, description="Whether the alert is active")
    last_run: Optional[datetime] = Field(None, description="Last time alert was processed")
    created_at: Optional[datetime] = Field(None, description="Alert creation time")

    class Config:
        from_attributes = True


class JobBulkAction(BaseModel):
    """Schema for bulk job operations."""
    
    job_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of job IDs")
    action: str = Field(..., regex="^(activate|deactivate|delete|archive|feature|unfeature)$")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for the action")

    class Config:
        from_attributes = True