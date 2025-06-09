"""
Application History model for tracking all changes and events in application lifecycle.
This model provides comprehensive audit trail and duplicate detection capabilities.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from typing import Optional, Dict, Any, List

# Import Base from parent package - will be set by __init__.py
try:
    from . import Base
except ImportError:
    # Fallback for direct imports during development
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class HistoryEventType(enum.Enum):
    """History event type enumeration."""
    APPLICATION_CREATED = "application_created"
    APPLICATION_SUBMITTED = "application_submitted"
    STATUS_CHANGED = "status_changed"
    DOCUMENT_ATTACHED = "document_attached"
    DOCUMENT_UPDATED = "document_updated"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    FOLLOW_UP_SENT = "follow_up_sent"
    RESPONSE_RECEIVED = "response_received"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    APPLICATION_WITHDRAWN = "application_withdrawn"
    APPLICATION_REJECTED = "application_rejected"
    DUPLICATE_DETECTED = "duplicate_detected"
    NOTE_ADDED = "note_added"
    AUTOMATION_EXECUTED = "automation_executed"
    ERROR_OCCURRED = "error_occurred"
    REMINDER_SET = "reminder_set"
    CONTACT_UPDATED = "contact_updated"


class HistorySource(enum.Enum):
    """Source of the history event."""
    USER = "user"
    SYSTEM = "system"
    AUTOMATION = "automation"
    WEBHOOK = "webhook"
    EMAIL_PARSER = "email_parser"
    SCRAPER = "scraper"
    API = "api"


class ApplicationHistory(Base):
    """
    Application History model for comprehensive tracking of application lifecycle events.
    """
    __tablename__ = "application_history"

    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(Enum(HistoryEventType), nullable=False, index=True)
    source = Column(Enum(HistorySource), nullable=False, index=True)
    
    # Event content
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # State changes
    old_value = Column(JSON, nullable=True)  # Previous state/value
    new_value = Column(JSON, nullable=True)  # New state/value
    field_changed = Column(String(100), nullable=True)  # Which field was changed
    
    # Event metadata
    metadata = Column(JSON, nullable=True)  # Additional event data
    external_id = Column(String(255), nullable=True)  # ID from external system
    
    # Automation details
    automation_rule_id = Column(String(100), nullable=True)  # ID of automation rule
    automation_success = Column(Boolean, nullable=True)
    automation_error = Column(Text, nullable=True)
    
    # Communication tracking
    email_sent = Column(Boolean, default=False)
    email_subject = Column(String(300), nullable=True)
    email_recipient = Column(String(255), nullable=True)
    
    # Duplicate detection
    duplicate_hash = Column(String(64), nullable=True, index=True)  # Hash for duplicate detection
    is_duplicate_event = Column(Boolean, default=False)
    original_event_id = Column(Integer, ForeignKey("application_history.id"), nullable=True)
    
    # Importance and priority
    importance = Column(Integer, default=3)  # 1=critical, 3=normal, 5=low
    is_milestone = Column(Boolean, default=False, index=True)  # Major milestone events
    is_user_visible = Column(Boolean, default=True, index=True)  # Show to user in timeline
    
    # Context information
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Related entities
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    
    # Timestamps
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="history")
    user = relationship("User")
    document = relationship("Document")
    job = relationship("Job")
    original_event = relationship("ApplicationHistory", remote_side=[id])
    
    def __repr__(self):
        return f"<ApplicationHistory(id={self.id}, event='{self.event_type.value}', app_id={self.application_id})>"
    
    @classmethod
    def create_event(
        cls,
        application_id: int,
        user_id: int,
        event_type: HistoryEventType,
        title: str,
        description: Optional[str] = None,
        source: HistorySource = HistorySource.USER,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        field_changed: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: int = 3,
        is_milestone: bool = False,
        document_id: Optional[int] = None,
        job_id: Optional[int] = None
    ) -> 'ApplicationHistory':
        """Factory method to create a new history event."""
        from datetime import datetime
        
        return cls(
            application_id=application_id,
            user_id=user_id,
            event_type=event_type,
            source=source,
            title=title,
            description=description,
            old_value=old_value,
            new_value=new_value,
            field_changed=field_changed,
            metadata=metadata or {},
            importance=importance,
            is_milestone=is_milestone,
            document_id=document_id,
            job_id=job_id,
            event_timestamp=datetime.utcnow(),
            is_user_visible=True
        )
    
    @classmethod
    def create_status_change_event(
        cls,
        application_id: int,
        user_id: int,
        old_status: str,
        new_status: str,
        source: HistorySource = HistorySource.USER,
        notes: Optional[str] = None
    ) -> 'ApplicationHistory':
        """Create a status change event."""
        return cls.create_event(
            application_id=application_id,
            user_id=user_id,
            event_type=HistoryEventType.STATUS_CHANGED,
            title=f"Status changed to {new_status.replace('_', ' ').title()}",
            description=notes,
            source=source,
            old_value={"status": old_status},
            new_value={"status": new_status},
            field_changed="status",
            is_milestone=True
        )
    
    @classmethod
    def create_document_event(
        cls,
        application_id: int,
        user_id: int,
        document_id: int,
        document_name: str,
        event_type: HistoryEventType = HistoryEventType.DOCUMENT_ATTACHED,
        source: HistorySource = HistorySource.USER
    ) -> 'ApplicationHistory':
        """Create a document-related event."""
        action = "attached" if event_type == HistoryEventType.DOCUMENT_ATTACHED else "updated"
        
        return cls.create_event(
            application_id=application_id,
            user_id=user_id,
            event_type=event_type,
            title=f"Document {action}: {document_name}",
            source=source,
            document_id=document_id,
            metadata={"document_name": document_name}
        )
    
    @classmethod
    def create_automation_event(
        cls,
        application_id: int,
        user_id: int,
        automation_rule_id: str,
        success: bool,
        action_taken: str,
        error_message: Optional[str] = None
    ) -> 'ApplicationHistory':
        """Create an automation event."""
        title = f"Automation executed: {action_taken}"
        if not success:
            title += " (Failed)"
        
        return cls.create_event(
            application_id=application_id,
            user_id=user_id,
            event_type=HistoryEventType.AUTOMATION_EXECUTED,
            title=title,
            description=error_message if not success else f"Successfully executed: {action_taken}",
            source=HistorySource.AUTOMATION,
            metadata={
                "automation_rule_id": automation_rule_id,
                "action_taken": action_taken,
                "success": success,
                "error": error_message
            },
            importance=1 if not success else 3
        )
    
    @classmethod
    def create_duplicate_detection_event(
        cls,
        application_id: int,
        user_id: int,
        original_application_id: int,
        similarity_score: float,
        duplicate_fields: List[str]
    ) -> 'ApplicationHistory':
        """Create a duplicate detection event."""
        return cls.create_event(
            application_id=application_id,
            user_id=user_id,
            event_type=HistoryEventType.DUPLICATE_DETECTED,
            title="Duplicate application detected",
            description=f"Similar to application #{original_application_id} (Similarity: {similarity_score:.2%})",
            source=HistorySource.SYSTEM,
            metadata={
                "original_application_id": original_application_id,
                "similarity_score": similarity_score,
                "duplicate_fields": duplicate_fields
            },
            importance=2,
            is_milestone=True
        )
    
    def calculate_event_hash(self) -> str:
        """Calculate hash for duplicate event detection."""
        import hashlib
        
        hash_string = f"{self.application_id}_{self.event_type.value}_{self.title}_{self.event_timestamp}"
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
    
    def mark_as_duplicate(self, original_event_id: int) -> None:
        """Mark this event as a duplicate of another."""
        self.is_duplicate_event = True
        self.original_event_id = original_event_id
        self.is_user_visible = False
    
    @property
    def is_recent(self) -> bool:
        """Check if event happened in the last 24 hours."""
        from datetime import datetime, timedelta
        return self.event_timestamp > (datetime.utcnow() - timedelta(hours=24))
    
    @property
    def formatted_timestamp(self) -> str:
        """Get formatted timestamp for display."""
        from datetime import datetime
        
        now = datetime.utcnow()
        delta = now - self.event_timestamp
        
        if delta.days > 7:
            return self.event_timestamp.strftime("%Y-%m-%d %H:%M")
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    @property
    def importance_label(self) -> str:
        """Get importance label."""
        labels = {1: "Critical", 2: "High", 3: "Normal", 4: "Low", 5: "Very Low"}
        return labels.get(self.importance, "Normal")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history event to dictionary."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "user_id": self.user_id,
            "event_type": self.event_type.value if self.event_type else None,
            "source": self.source.value if self.source else None,
            "title": self.title,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "field_changed": self.field_changed,
            "metadata": self.metadata,
            "external_id": self.external_id,
            "automation_rule_id": self.automation_rule_id,
            "automation_success": self.automation_success,
            "automation_error": self.automation_error,
            "email_sent": self.email_sent,
            "email_subject": self.email_subject,
            "email_recipient": self.email_recipient,
            "duplicate_hash": self.duplicate_hash,
            "is_duplicate_event": self.is_duplicate_event,
            "original_event_id": self.original_event_id,
            "importance": self.importance,
            "importance_label": self.importance_label,
            "is_milestone": self.is_milestone,
            "is_user_visible": self.is_user_visible,
            "document_id": self.document_id,
            "job_id": self.job_id,
            "event_timestamp": self.event_timestamp,
            "created_at": self.created_at,
            "is_recent": self.is_recent,
            "formatted_timestamp": self.formatted_timestamp
        }


class DuplicateApplicationDetector:
    """
    Utility class for detecting duplicate applications and managing history deduplication.
    """
    
    @staticmethod
    def calculate_application_similarity(app1_data: Dict[str, Any], app2_data: Dict[str, Any]) -> float:
        """Calculate similarity score between two applications."""
        score = 0.0
        total_weight = 0.0
        
        # Weight factors for different fields
        weights = {
            "job_url": 0.4,
            "company": 0.2,
            "title": 0.2,
            "location": 0.1,
            "user_id": 0.1
        }
        
        for field, weight in weights.items():
            total_weight += weight
            
            val1 = app1_data.get(field, "").lower() if app1_data.get(field) else ""
            val2 = app2_data.get(field, "").lower() if app2_data.get(field) else ""
            
            if val1 and val2:
                # Simple string similarity (could be enhanced with fuzzy matching)
                if val1 == val2:
                    score += weight
                elif field in ["company", "title", "location"] and val1 in val2 or val2 in val1:
                    score += weight * 0.7  # Partial match
        
        return score / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def detect_duplicate_applications(
        new_application_data: Dict[str, Any],
        existing_applications: List[Dict[str, Any]],
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Detect potential duplicate applications."""
        duplicates = []
        
        for existing_app in existing_applications:
            similarity = DuplicateApplicationDetector.calculate_application_similarity(
                new_application_data, existing_app
            )
            
            if similarity >= similarity_threshold:
                duplicates.append({
                    "application_id": existing_app.get("id"),
                    "similarity_score": similarity,
                    "duplicate_fields": DuplicateApplicationDetector._get_matching_fields(
                        new_application_data, existing_app
                    )
                })
        
        return duplicates
    
    @staticmethod
    def _get_matching_fields(app1_data: Dict[str, Any], app2_data: Dict[str, Any]) -> List[str]:
        """Get list of fields that match between two applications."""
        matching_fields = []
        
        fields_to_check = ["job_url", "company", "title", "location"]
        
        for field in fields_to_check:
            val1 = app1_data.get(field, "").lower() if app1_data.get(field) else ""
            val2 = app2_data.get(field, "").lower() if app2_data.get(field) else ""
            
            if val1 and val2 and (val1 == val2 or val1 in val2 or val2 in val1):
                matching_fields.append(field)
        
        return matching_fields