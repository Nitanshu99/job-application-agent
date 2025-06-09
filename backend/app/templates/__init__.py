"""
Document Templates Package

This package provides template classes for generating professional documents
including resumes and cover letters with various formats and styles.
"""

from .resume_template import (
    # Data structures
    ContactInfo,
    Education,
    Experience,
    Project,
    ResumeData,
    
    # Template classes
    BaseResumeTemplate,
    ProfessionalResumeTemplate,
    AcademicResumeTemplate,
    TechResumeTemplate,
    
    # Factory and utilities
    ResumeTemplateFactory,
    create_sample_resume_data,
    generate_resume
)

from .cover_letter_template import (
    # Enums
    CoverLetterTone,
    IndustryType,
    
    # Data structures
    ApplicantInfo,
    CompanyInfo,
    JobInfo,
    RelevantExperience,
    CoverLetterData,
    
    # Template classes
    BaseCoverLetterTemplate,
    ProfessionalCoverLetterTemplate,
    TechCoverLetterTemplate,
    InternshipCoverLetterTemplate,
    AcademicCoverLetterTemplate,
    
    # Factory and utilities
    CoverLetterTemplateFactory,
    create_sample_cover_letter_data,
    generate_cover_letter,
    auto_select_template
)

# Package metadata
__version__ = "1.0.0"
__author__ = "Job Automation System"

# Available template types
AVAILABLE_RESUME_TEMPLATES = ResumeTemplateFactory.available_templates()
AVAILABLE_COVER_LETTER_TEMPLATES = CoverLetterTemplateFactory.available_templates()

# Quick access functions for common use cases
def create_resume(template_type: str, resume_data: ResumeData) -> str:
    """
    Quick function to create a resume with the specified template.
    
    Args:
        template_type: Type of resume template ('professional', 'academic', 'tech')
        resume_data: ResumeData object containing all resume information
        
    Returns:
        Generated resume content as string
        
    Raises:
        ValueError: If template_type is not supported
        Exception: If resume generation fails
    """
    return generate_resume(template_type, resume_data)


def create_cover_letter(template_type: str, cover_letter_data: CoverLetterData) -> str:
    """
    Quick function to create a cover letter with the specified template.
    
    Args:
        template_type: Type of cover letter template ('professional', 'tech', 'internship', 'academic')
        cover_letter_data: CoverLetterData object containing all cover letter information
        
    Returns:
        Generated cover letter content as string
        
    Raises:
        ValueError: If template_type is not supported
        Exception: If cover letter generation fails
    """
    return generate_cover_letter(template_type, cover_letter_data)


def get_recommended_templates(job_title: str, industry: str = "general") -> dict:
    """
    Get recommended templates for both resume and cover letter based on job and industry.
    
    Args:
        job_title: The job title to apply for
        industry: The industry type (optional, defaults to "general")
        
    Returns:
        Dictionary with recommended template types for resume and cover letter
    """
    # Map job/industry to appropriate resume template
    job_lower = job_title.lower()
    industry_lower = industry.lower()
    
    if 'research' in job_lower or 'academic' in job_lower or industry_lower == 'academia':
        resume_template = 'academic'
    elif any(tech_word in job_lower for tech_word in ['developer', 'engineer', 'data scientist', 'analyst']) or industry_lower == 'technology':
        resume_template = 'tech'
    else:
        resume_template = 'professional'
    
    # Get cover letter recommendation
    cover_letter_template = auto_select_template(job_title, industry)
    
    return {
        'resume': resume_template,
        'cover_letter': cover_letter_template
    }


# Export all main classes and functions
__all__ = [
    # Resume exports
    'ContactInfo',
    'Education', 
    'Experience',
    'Project',
    'ResumeData',
    'BaseResumeTemplate',
    'ProfessionalResumeTemplate',
    'AcademicResumeTemplate',
    'TechResumeTemplate',
    'ResumeTemplateFactory',
    'create_sample_resume_data',
    'generate_resume',
    
    # Cover letter exports
    'CoverLetterTone',
    'IndustryType',
    'ApplicantInfo',
    'CompanyInfo',
    'JobInfo',
    'RelevantExperience',
    'CoverLetterData',
    'BaseCoverLetterTemplate',
    'ProfessionalCoverLetterTemplate',
    'TechCoverLetterTemplate',
    'InternshipCoverLetterTemplate',
    'AcademicCoverLetterTemplate',
    'CoverLetterTemplateFactory',
    'create_sample_cover_letter_data',
    'generate_cover_letter',
    'auto_select_template',
    
    # Utility functions
    'create_resume',
    'create_cover_letter',
    'get_recommended_templates',
    
    # Constants
    'AVAILABLE_RESUME_TEMPLATES',
    'AVAILABLE_COVER_LETTER_TEMPLATES',
]