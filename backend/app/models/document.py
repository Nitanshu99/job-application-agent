"""
Document model for managing resumes, cover letters, and other application documents.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Enum, LargeBinary
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


class DocumentType(enum.Enum):
    """Document type enumeration."""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    TRANSCRIPT = "transcript"
    CERTIFICATE = "certificate"
    REFERENCE = "reference"
    OTHER = "other"


class DocumentFormat(enum.Enum):
    """Document format enumeration."""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    HTML = "html"
    RTF = "rtf"


class DocumentStatus(enum.Enum):
    """Document status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    TEMPLATE = "template"


class Document(Base):
    """
    Document model for storing and managing application documents.
    """
    __tablename__ = "documents"

    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Document metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(Enum(DocumentType), nullable=False, index=True)
    format = Column(Enum(DocumentFormat), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT, index=True)
    
    # File information
    filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    file_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash
    mime_type = Column(String(100), nullable=True)
    
    # Content storage
    content = Column(Text, nullable=True)  # Text content for searchability
    binary_content = Column(LargeBinary, nullable=True)  # Binary file content
    
    # Template information
    is_template = Column(Boolean, default=False, index=True)
    template_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    template_variables = Column(JSON, nullable=True)  # Variables for template substitution
    
    # Generation metadata (for AI-generated documents)
    is_generated = Column(Boolean, default=False, index=True)
    generation_prompt = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)  # LLM model used for generation
    generation_settings = Column(JSON, nullable=True)  # Model settings used
    
    # Job-specific customization
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    customizations = Column(JSON, nullable=True)  # Job-specific customizations applied
    base_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # Original document this was customized from
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    success_rate = Column(Integer, nullable=True)  # Percentage of successful applications
    
    # Version control
    version = Column(String(20), default="1.0")
    parent_version_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    is_latest_version = Column(Boolean, default=True, index=True)
    
    # Organization
    tags = Column(JSON, nullable=True)  # User-defined tags
    category = Column(String(100), nullable=True)  # User-defined category
    is_favorite = Column(Boolean, default=False, index=True)
    
    # Sharing and permissions
    is_public = Column(Boolean, default=False)
    share_token = Column(String(64), nullable=True, unique=True)
    
    # Validation and quality
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSON, nullable=True)  # List of validation errors
    quality_score = Column(Integer, nullable=True)  # 1-100 quality score
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="documents")
    job = relationship("Job")  # For job-specific documents
    template = relationship("Document", remote_side=[id], foreign_keys=[template_id])
    base_document = relationship("Document", remote_side=[id], foreign_keys=[base_document_id])
    parent_version = relationship("Document", remote_side=[id], foreign_keys=[parent_version_id])
    
    # Documents that use this as a template
    template_instances = relationship("Document", foreign_keys=[template_id], remote_side=[template_id])
    
    # Customized versions of this document
    customized_versions = relationship("Document", foreign_keys=[base_document_id], remote_side=[base_document_id])
    
    # Version history
    version_history = relationship("Document", foreign_keys=[parent_version_id], remote_side=[parent_version_id])
    
    def __repr__(self):
        return f"<Document(id={self.id}, name='{self.name}', type='{self.document_type.value}')>"
    
    @property
    def file_size_formatted(self) -> str:
        """Get formatted file size."""
        if not self.file_size:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    @property
    def is_customized(self) -> bool:
        """Check if document is a customized version of another document."""
        return self.base_document_id is not None
    
    @property
    def is_outdated(self) -> bool:
        """Check if document version is outdated."""
        return not self.is_latest_version
    
    def create_customized_version(self, job_id: int, customizations: Dict[str, Any]) -> 'Document':
        """Create a customized version of this document for a specific job."""
        customized = Document(
            user_id=self.user_id,
            name=f"{self.name} - {job_id}",
            description=f"Customized version for job {job_id}",
            document_type=self.document_type,
            format=self.format,
            status=DocumentStatus.ACTIVE,
            filename=f"customized_{job_id}_{self.filename}" if self.filename else None,
            content=self.content,
            binary_content=self.binary_content,
            is_generated=True,
            job_id=job_id,
            customizations=customizations,
            base_document_id=self.id,
            template_variables=self.template_variables,
            tags=self.tags,
            category=self.category
        )
        return customized
    
    def create_new_version(self, content: Optional[str] = None, binary_content: Optional[bytes] = None) -> 'Document':
        """Create a new version of this document."""
        # Mark current version as not latest
        self.is_latest_version = False
        
        # Parse version number and increment
        try:
            major, minor = map(int, self.version.split('.'))
            new_version = f"{major}.{minor + 1}"
        except:
            new_version = "1.1"
        
        new_doc = Document(
            user_id=self.user_id,
            name=self.name,
            description=self.description,
            document_type=self.document_type,
            format=self.format,
            status=self.status,
            filename=self.filename,
            content=content or self.content,
            binary_content=binary_content or self.binary_content,
            is_template=self.is_template,
            template_id=self.template_id,
            template_variables=self.template_variables,
            is_generated=self.is_generated,
            tags=self.tags,
            category=self.category,
            version=new_version,
            parent_version_id=self.id,
            is_latest_version=True
        )
        return new_doc
    
    def calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of file content."""
        import hashlib
        return hashlib.sha256(content).hexdigest()
    
    def validate_document(self) -> List[str]:
        """Validate document and return list of errors."""
        errors = []
        
        # Check required fields
        if not self.name or not self.name.strip():
            errors.append("Document name is required")
        
        if not self.document_type:
            errors.append("Document type is required")
        
        if not self.content and not self.binary_content:
            errors.append("Document content is required")
        
        # Type-specific validations
        if self.document_type == DocumentType.RESUME:
            if not self.content or len(self.content.strip()) < 100:
                errors.append("Resume content seems too short")
        
        elif self.document_type == DocumentType.COVER_LETTER:
            if not self.content or len(self.content.strip()) < 50:
                errors.append("Cover letter content seems too short")
        
        # File size validation
        if self.file_size and self.file_size > 10 * 1024 * 1024:  # 10MB limit
            errors.append("File size exceeds 10MB limit")
        
        self.validation_errors = errors if errors else None
        self.is_validated = len(errors) == 0
        
        return errors
    
    def calculate_quality_score(self) -> int:
        """Calculate document quality score (1-100)."""
        score = 100
        
        # Validate first
        errors = self.validate_document()
        if errors:
            score -= len(errors) * 10
        
        # Content length scoring
        if self.content:
            content_length = len(self.content.strip())
            if self.document_type == DocumentType.RESUME:
                if content_length < 500:
                    score -= 20
                elif content_length < 1000:
                    score -= 10
            elif self.document_type == DocumentType.COVER_LETTER:
                if content_length < 200:
                    score -= 20
                elif content_length < 400:
                    score -= 10
        
        # Usage and success rate
        if self.usage_count > 0 and self.success_rate is not None:
            if self.success_rate > 80:
                score += 5
            elif self.success_rate < 20:
                score -= 10
        
        self.quality_score = max(0, min(100, score))
        return self.quality_score
    
    def increment_usage(self) -> None:
        """Increment usage counter and update last used timestamp."""
        self.usage_count += 1
        self.last_used = func.now()
    
    def update_success_rate(self, successful_applications: int, total_applications: int) -> None:
        """Update success rate based on application outcomes."""
        if total_applications > 0:
            self.success_rate = int((successful_applications / total_applications) * 100)
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert document to dictionary."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "document_type": self.document_type.value if self.document_type else None,
            "format": self.format.value if self.format else None,
            "status": self.status.value if self.status else None,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_size_formatted": self.file_size_formatted,
            "mime_type": self.mime_type,
            "is_template": self.is_template,
            "template_id": self.template_id,
            "is_generated": self.is_generated,
            "model_used": self.model_used,
            "job_id": self.job_id,
            "is_customized": self.is_customized,
            "base_document_id": self.base_document_id,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "success_rate": self.success_rate,
            "version": self.version,
            "parent_version_id": self.parent_version_id,
            "is_latest_version": self.is_latest_version,
            "is_outdated": self.is_outdated,
            "tags": self.tags,
            "category": self.category,
            "is_favorite": self.is_favorite,
            "is_public": self.is_public,
            "is_validated": self.is_validated,
            "validation_errors": self.validation_errors,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        if include_content:
            data["content"] = self.content
            data["template_variables"] = self.template_variables
            data["customizations"] = self.customizations
            data["generation_settings"] = self.generation_settings
        
        return data