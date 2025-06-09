"""
Application model for tracking job applications with history and status management.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from typing import Optional, Dict, Any

# Import Base from parent package - will be set by __init__.py
try:
    from . import Base
except ImportError:
    # Fallback for direct imports during development
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class ApplicationStatus(enum.Enum):
    """Application status enumeration."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_INTERVIEW = "technical_interview"
    ONSITE_INTERVIEW = "onsite_interview"
    FINAL_INTERVIEW = "final_interview"
    REFERENCE_CHECK = "reference_check"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"


class ApplicationMethod(enum.Enum):
    """Application method enumeration."""
    AUTOMATED = "automated"
    MANUAL = "manual"
    REFERRAL = "referral"
    RECRUITER = "recruiter"
    DIRECT = "direct"


class Application(Base):
    """
    Application model for tracking job applications with comprehensive history.
    """
    __tablename__ = "applications"

    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # ID from job site
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Application details
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT, index=True)
    method = Column(Enum(ApplicationMethod), default=ApplicationMethod.MANUAL, index=True)
    
    # Application content
    cover_letter_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    resume_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    custom_resume_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # Job-specific resume
    
    # Contact information
    contact_person = Column(String(200), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    recruiter_name = Column(String(200), nullable=True)
    recruiter_email = Column(String(255), nullable=True)
    
    # Application tracking
    application_url = Column(Text, nullable=True)
    confirmation_number = Column(String(100), nullable=True)
    follow_up_date = Column(DateTime(timezone=True), nullable=True)
    
    # Interview scheduling
    interview_scheduled = Column(Boolean, default=False)
    interview_datetime = Column(DateTime(timezone=True), nullable=True)
    interview_type = Column(String(50), nullable=True)  # phone, video, onsite
    interview_location = Column(String(500), nullable=True)
    interview_notes = Column(Text, nullable=True)
    
    # Offer details
    offer_amount = Column(Integer, nullable=True)
    offer_currency = Column(String(10), default="USD")
    offer_benefits = Column(JSON, nullable=True)
    offer_start_date = Column(DateTime(timezone=True), nullable=True)
    offer_deadline = Column(DateTime(timezone=True), nullable=True)
    
    # Response tracking
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime(timezone=True), nullable=True)
    response_type = Column(String(50), nullable=True)  # email, phone, portal
    rejection_reason = Column(Text, nullable=True)
    
    # Automation details
    is_automated = Column(Boolean, default=False)
    automation_log = Column(JSON, nullable=True)  # Log of automated actions
    retry_count = Column(Integer, default=0)
    last_retry = Column(DateTime(timezone=True), nullable=True)
    
    # Notes and feedback
    notes = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 rating of company/process
    
    # Duplicate prevention
    application_hash = Column(String(64), nullable=True, index=True)  # Hash for duplicate detection
    is_duplicate = Column(Boolean, default=False, index=True)
    original_application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    
    # Priority and organization
    priority = Column(Integer, default=3)  # 1=high, 3=medium, 5=low
    tags = Column(JSON, nullable=True)  # User-defined tags
    is_archived = Column(Boolean, default=False, index=True)
    
    # Metrics
    days_to_response = Column(Integer, nullable=True)
    total_interview_rounds = Column(Integer, default=0)
    
    # Timestamps
    applied_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    cover_letter = relationship("Document", foreign_keys=[cover_letter_id])
    resume = relationship("Document", foreign_keys=[resume_id])
    custom_resume = relationship("Document", foreign_keys=[custom_resume_id])
    original_application = relationship("Application", remote_side=[id])
    history = relationship("ApplicationHistory", back_populates="application", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Application(id={self.id}, job_title='{self.job.title if self.job else 'Unknown'}', status='{self.status.value}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if application is in an active state."""
        active_statuses = [
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.PHONE_SCREEN,
            ApplicationStatus.TECHNICAL_INTERVIEW,
            ApplicationStatus.ONSITE_INTERVIEW,
            ApplicationStatus.FINAL_INTERVIEW,
            ApplicationStatus.REFERENCE_CHECK
        ]
        return self.status in active_statuses
    
    @property
    def is_completed(self) -> bool:
        """Check if application process is completed."""
        completed_statuses = [
            ApplicationStatus.OFFER_ACCEPTED,
            ApplicationStatus.OFFER_DECLINED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.GHOSTED
        ]
        return self.status in completed_statuses
    
    @property
    def is_successful(self) -> bool:
        """Check if application was successful."""
        return self.status == ApplicationStatus.OFFER_ACCEPTED
    
    @property
    def days_since_applied(self) -> Optional[int]:
        """Get number of days since application was submitted."""
        if self.applied_at:
            delta = func.now() - self.applied_at
            return delta.days
        return None
    
    @property
    def is_overdue_for_followup(self) -> bool:
        """Check if application is overdue for follow-up."""
        if not self.follow_up_date:
            return False
        return self.follow_up_date < func.now()
    
    def update_status(self, new_status: ApplicationStatus, notes: Optional[str] = None) -> None:
        """Update application status and create history entry."""
        old_status = self.status
        self.status = new_status
        
        # Calculate days to response if this is the first response
        if (old_status == ApplicationStatus.SUBMITTED and 
            new_status != ApplicationStatus.SUBMITTED and 
            self.applied_at and not self.response_received):
            self.response_received = True
            self.response_date = func.now()
            delta = func.now() - self.applied_at
            self.days_to_response = delta.days
        
        # Create history entry (this would be handled by the service layer)
        # The ApplicationHistory model will handle this
    
    def calculate_application_hash(self) -> str:
        """Calculate hash for duplicate detection."""
        import hashlib
        
        # Create hash based on user_id, job_id, and job URL
        hash_string = f"{self.user_id}_{self.job_id}_{self.job.url if self.job else ''}"
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
    
    def mark_as_duplicate(self, original_application_id: int) -> None:
        """Mark this application as a duplicate of another."""
        self.is_duplicate = True
        self.original_application_id = original_application_id
        self.status = ApplicationStatus.WITHDRAWN
    
    def set_follow_up_date(self, days: int = 7) -> None:
        """Set follow-up date based on current date plus specified days."""
        from datetime import datetime, timedelta
        self.follow_up_date = datetime.utcnow() + timedelta(days=days)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert application to dictionary."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "status": self.status.value if self.status else None,
            "method": self.method.value if self.method else None,
            "cover_letter_id": self.cover_letter_id,
            "resume_id": self.resume_id,
            "custom_resume_id": self.custom_resume_id,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "recruiter_name": self.recruiter_name,
            "recruiter_email": self.recruiter_email,
            "confirmation_number": self.confirmation_number,
            "follow_up_date": self.follow_up_date,
            "interview_scheduled": self.interview_scheduled,
            "interview_datetime": self.interview_datetime,
            "interview_type": self.interview_type,
            "interview_location": self.interview_location,
            "offer_amount": self.offer_amount,
            "offer_currency": self.offer_currency,
            "offer_start_date": self.offer_start_date,
            "offer_deadline": self.offer_deadline,
            "response_received": self.response_received,
            "response_date": self.response_date,
            "rejection_reason": self.rejection_reason,
            "is_automated": self.is_automated,
            "notes": self.notes,
            "feedback": self.feedback,
            "rating": self.rating,
            "is_duplicate": self.is_duplicate,
            "original_application_id": self.original_application_id,
            "priority": self.priority,
            "tags": self.tags,
            "is_archived": self.is_archived,
            "days_to_response": self.days_to_response,
            "total_interview_rounds": self.total_interview_rounds,
            "applied_at": self.applied_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "is_completed": self.is_completed,
            "is_successful": self.is_successful,
            "days_since_applied": self.days_since_applied,
            "is_overdue_for_followup": self.is_overdue_for_followup
        }