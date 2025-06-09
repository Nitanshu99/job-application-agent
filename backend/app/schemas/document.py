"""
Document Pydantic schemas for request/response validation and serialization.

Handles resume and cover letter generation, templates, and document management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator


class DocumentTypeEnum(str, Enum):
    """Enumeration for document types."""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"


class TemplateStyleEnum(str, Enum):
    """Enumeration for document template styles."""
    PROFESSIONAL = "professional"
    MODERN = "modern"
    CLASSIC = "classic"
    CREATIVE = "creative"
    EXECUTIVE = "executive"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    MINIMAL = "minimal"


class DocumentStatusEnum(str, Enum):
    """Enumeration for document status."""
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"
    ARCHIVED = "archived"


class FileFormatEnum(str, Enum):
    """Enumeration for document file formats."""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"


class DocumentBase(BaseModel):
    """Base document schema with common fields."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    document_type: DocumentTypeEnum = Field(..., description="Type of document")
    content: Optional[str] = Field(None, description="Document content")
    template_style: Optional[TemplateStyleEnum] = Field(TemplateStyleEnum.PROFESSIONAL, description="Template style used")
    is_active: bool = Field(True, description="Whether the document is active")
    is_default: bool = Field(False, description="Whether this is the default document for its type")
    tags: Optional[List[str]] = Field(default_factory=list, description="Custom tags for the document")
    notes: Optional[str] = Field(None, max_length=1000, description="User notes about the document")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @validator('content')
    def validate_content(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError('Too many tags (maximum 20)')
        return v

    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    
    job_id: Optional[int] = Field(None, description="Optional job ID for job-specific documents")
    generation_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Parameters for AI document generation"
    )
    auto_generate: bool = Field(False, description="Whether to auto-generate content using AI")


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    template_style: Optional[TemplateStyleEnum] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = None

    @validator('content')
    def validate_content(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError('Too many tags (maximum 20)')
        return v

    @validator('title')
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v


class DocumentResponse(DocumentBase):
    """Schema for document response data."""
    
    id: int
    user_id: int
    job_id: Optional[int] = None
    status: DocumentStatusEnum = DocumentStatusEnum.DRAFT
    file_path: Optional[str] = Field(None, description="Path to generated document file")
    file_format: Optional[FileFormatEnum] = Field(None, description="Format of generated file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    word_count: Optional[int] = Field(None, description="Word count of document content")
    character_count: Optional[int] = Field(None, description="Character count of document content")
    generation_time: Optional[float] = Field(None, description="Time taken to generate document (seconds)")
    version: int = Field(1, description="Document version number")
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_generated: Optional[datetime] = Field(None, description="Last time document was generated")
    usage_count: int = Field(0, description="Number of times document was used in applications")

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    """Simplified document schema for listings."""
    
    id: int
    title: str
    document_type: DocumentTypeEnum
    template_style: Optional[TemplateStyleEnum]
    is_active: bool
    is_default: bool
    status: DocumentStatusEnum
    word_count: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    usage_count: int

    class Config:
        from_attributes = True


class DocumentGeneration(BaseModel):
    """Schema for document generation requests."""
    
    document_type: DocumentTypeEnum = Field(..., description="Type of document to generate")
    job_id: Optional[int] = Field(None, description="Job ID for job-specific generation")
    template_style: TemplateStyleEnum = Field(TemplateStyleEnum.PROFESSIONAL, description="Template style")
    title: Optional[str] = Field(None, description="Custom title for the document")
    custom_instructions: Optional[str] = Field(None, max_length=1000, description="Custom generation instructions")
    include_sections: Optional[List[str]] = Field(None, description="Specific sections to include")
    exclude_sections: Optional[List[str]] = Field(None, description="Sections to exclude")
    tone: Optional[str] = Field("professional", description="Writing tone")
    length: Optional[str] = Field("medium", regex="^(short|medium|long)$", description="Document length preference")
    focus_keywords: Optional[List[str]] = Field(None, description="Keywords to emphasize")
    company_research: bool = Field(True, description="Include company-specific customization")
    use_user_profile: bool = Field(True, description="Use user profile data")

    @validator('include_sections', 'exclude_sections')
    def validate_sections(cls, v):
        if v:
            valid_resume_sections = [
                'contact', 'summary', 'experience', 'education', 'skills', 
                'certifications', 'projects', 'awards', 'publications', 'languages'
            ]
            valid_cover_letter_sections = [
                'header', 'salutation', 'opening', 'body', 'closing', 'signature'
            ]
            # Note: This is a simplified validation - in practice you'd check against document_type
            all_valid = valid_resume_sections + valid_cover_letter_sections
            for section in v:
                if section not in all_valid:
                    raise ValueError(f'Invalid section: {section}')
        return v


class DocumentGenerationResponse(BaseModel):
    """Schema for document generation response."""
    
    document_id: int
    status: DocumentStatusEnum
    content: Optional[str] = None
    generation_time: float
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")

    class Config:
        from_attributes = True


class DocumentTemplate(BaseModel):
    """Schema for document templates."""
    
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    document_type: DocumentTypeEnum
    style: TemplateStyleEnum
    template_content: str = Field(..., description="Template content with placeholders")
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = False
    is_active: bool = True
    preview_url: Optional[str] = Field(None, description="URL to template preview")
    tags: Optional[List[str]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentExport(BaseModel):
    """Schema for document export requests."""
    
    document_id: int
    format: FileFormatEnum = Field(FileFormatEnum.PDF, description="Export format")
    include_metadata: bool = Field(False, description="Include metadata in export")
    password_protect: bool = Field(False, description="Password protect the file")
    password: Optional[str] = Field(None, min_length=6, description="Password for protection")
    watermark: Optional[str] = Field(None, description="Watermark text")
    custom_filename: Optional[str] = Field(None, description="Custom filename for export")

    @validator('password')
    def validate_password(cls, v, values):
        if values.get('password_protect') and not v:
            raise ValueError('Password required when password protection is enabled')
        return v


class DocumentComparison(BaseModel):
    """Schema for document comparison results."""
    
    document1_id: int
    document2_id: int
    similarity_score: float = Field(..., ge=0.0, le=100.0, description="Similarity percentage")
    differences: List[Dict[str, Any]] = Field(default_factory=list, description="Detailed differences")
    common_sections: List[str] = Field(default_factory=list, description="Common sections")
    unique_to_doc1: List[str] = Field(default_factory=list, description="Sections unique to document 1")
    unique_to_doc2: List[str] = Field(default_factory=list, description="Sections unique to document 2")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

    class Config:
        from_attributes = True


class DocumentAnalytics(BaseModel):
    """Schema for document analytics and statistics."""
    
    total_documents: int = 0
    documents_by_type: Dict[str, int] = Field(default_factory=dict)
    documents_by_template: Dict[str, int] = Field(default_factory=dict)
    average_word_count: Optional[float] = None
    most_used_templates: List[Dict[str, Union[str, int]]] = Field(default_factory=list)
    recent_generations: int = 0
    success_rate: float = 0.0
    average_generation_time: Optional[float] = None
    popular_keywords: List[Dict[str, Union[str, int]]] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DocumentBulkAction(BaseModel):
    """Schema for bulk document operations."""
    
    document_ids: List[int] = Field(..., min_items=1, max_items=50, description="List of document IDs")
    action: str = Field(..., regex="^(activate|deactivate|delete|archive|export|regenerate)$")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Action-specific parameters")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for the action")

    class Config:
        from_attributes = True


class DocumentVersion(BaseModel):
    """Schema for document version information."""
    
    id: int
    document_id: int
    version_number: int
    content: str
    created_at: datetime
    created_by: int
    change_summary: Optional[str] = Field(None, description="Summary of changes made")
    is_current: bool = False

    class Config:
        from_attributes = True