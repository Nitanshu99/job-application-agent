"""
Application service for AI-powered job automation system.

This service handles automated job application submission using Mistral 7B Instruct.
It provides intelligent form filling, application validation, and submission automation
while maintaining high-quality application standards.

Features:
- Automated form filling using Mistral 7B Instruct
- Application validation and quality checks
- Multi-platform application support
- Application tracking and status management
- Integration with application manager for duplicate prevention
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.document import Document
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.services.llm.mistral_service import MistralService
from app.services.application_manager import ApplicationManager
from app.utils.text_processing import clean_text, extract_keywords
from app.utils.validation import validate_job_data, sanitize_input

logger = logging.getLogger(__name__)


class ApplicationService:
    """Service for automated job application submission using Mistral 7B."""
    
    def __init__(self):
        self.mistral_service = None
        self.application_manager = ApplicationManager()
        
    async def get_mistral_service(self) -> MistralService:
        """Get or initialize Mistral service."""
        if not self.mistral_service:
            self.mistral_service = MistralService()
            await self.mistral_service.initialize()
        return self.mistral_service
    
    async def submit_application(
        self,
        user_id: int,
        job_id: int,
        resume_id: Optional[int] = None,
        cover_letter_id: Optional[int] = None,
        application_method: str = "automated",
        custom_answers: Optional[Dict[str, str]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Submit a job application with automated form filling.
        
        Args:
            user_id: ID of the user applying
            job_id: ID of the job to apply for
            resume_id: Optional resume document ID
            cover_letter_id: Optional cover letter document ID
            application_method: Method of application (automated, manual, etc.)
            custom_answers: Custom answers for specific questions
            db: Database session
            
        Returns:
            Dictionary containing application submission result
        """
        try:
            if not db:
                db = next(get_db())
            
            # Get user, job, and documents
            user = db.query(User).filter(User.id == user_id).first()
            job = db.query(Job).filter(Job.id == job_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Check for duplicate applications
            is_duplicate = await self.application_manager.check_duplicate(
                user_id=user_id,
                job_url=job.url,
                company=job.company,
                job_title=job.title,
                db=db
            )
            
            if is_duplicate:
                raise HTTPException(
                    status_code=409,
                    detail="Application already exists for this job"
                )
            
            logger.info(f"Submitting application for user {user_id} to job {job_id}")
            
            # Get documents if specified
            resume = None
            cover_letter = None
            
            if resume_id:
                resume = db.query(Document).filter(
                    Document.id == resume_id,
                    Document.user_id == user_id,
                    Document.type == "resume"
                ).first()
            
            if cover_letter_id:
                cover_letter = db.query(Document).filter(
                    Document.id == cover_letter_id,
                    Document.user_id == user_id,
                    Document.type == "cover_letter"
                ).first()
            
            # Prepare application context
            application_context = await self._prepare_application_context(
                user, job, resume, cover_letter, custom_answers
            )
            
            # Get Mistral service for application automation
            mistral_service = await self.get_mistral_service()
            
            # Determine application strategy based on job URL and platform
            platform_info = await self._analyze_application_platform(job.url)
            
            submission_result = None
            
            if application_method == "automated" and platform_info.get("supports_automation"):
                # Automated application submission
                submission_result = await self._submit_automated_application(
                    mistral_service, application_context, platform_info
                )
            else:
                # Manual application with form pre-filling
                submission_result = await self._prepare_manual_application(
                    mistral_service, application_context, platform_info
                )
            
            if not submission_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Application submission failed: {submission_result.get('error')}"
                )
            
            # Create application record
            application_data = {
                "user_id": user_id,
                "job_id": job_id,
                "resume_id": resume_id,
                "cover_letter_id": cover_letter_id,
                "application_method": application_method,
                "status": submission_result.get("status", "submitted"),
                "submitted_at": datetime.utcnow(),
                "platform": platform_info.get("platform", "unknown"),
                "submission_metadata": {
                    "model_used": "mistral-7b-instruct",
                    "platform_info": platform_info,
                    "automation_level": submission_result.get("automation_level"),
                    "form_fields_filled": submission_result.get("fields_filled", 0),
                    "success_confidence": submission_result.get("confidence", 0.0)
                },
                "tracking_url": submission_result.get("tracking_url"),
                "reference_number": submission_result.get("reference_number")
            }
            
            application = Application(**application_data)
            db.add(application)
            db.commit()
            db.refresh(application)
            
            # Record in application manager
            await self.application_manager.record_application(
                user_id=user_id,
                job_id=job_id,
                application_id=application.id,
                job_url=job.url,
                company=job.company,
                job_title=job.title,
                db=db
            )
            
            logger.info(f"Application submitted successfully with ID {application.id}")
            
            return {
                "application_id": application.id,
                "status": application.status,
                "submission_method": application_method,
                "platform": platform_info.get("platform"),
                "tracking_url": application.tracking_url,
                "reference_number": application.reference_number,
                "success": True,
                "metadata": submission_result
            }
            
        except Exception as e:
            logger.error(f"Application submission failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Application submission failed: {str(e)}")
    
    async def fill_application_form(
        self,
        user_id: int,
        job_id: int,
        form_fields: List[Dict[str, Any]],
        resume_id: Optional[int] = None,
        cover_letter_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Fill application form fields using AI assistance.
        
        Args:
            user_id: ID of the user
            job_id: ID of the job
            form_fields: List of form field definitions
            resume_id: Optional resume document ID
            cover_letter_id: Optional cover letter document ID
            db: Database session
            
        Returns:
            Dictionary containing filled form data
        """
        try:
            if not db:
                db = next(get_db())
            
            # Get user and job data
            user = db.query(User).filter(User.id == user_id).first()
            job = db.query(Job).filter(Job.id == job_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Get documents if specified
            resume = None
            cover_letter = None
            
            if resume_id:
                resume = db.query(Document).filter(
                    Document.id == resume_id,
                    Document.user_id == user_id
                ).first()
            
            if cover_letter_id:
                cover_letter = db.query(Document).filter(
                    Document.id == cover_letter_id,
                    Document.user_id == user_id
                ).first()
            
            logger.info(f"Filling application form for user {user_id} and job {job_id}")
            
            # Prepare context for form filling
            form_context = await self._prepare_form_filling_context(
                user, job, resume, cover_letter, form_fields
            )
            
            # Get Mistral service
            mistral_service = await self.get_mistral_service()
            
            # Fill form fields using Mistral 7B
            filling_result = await mistral_service.fill_application_form(
                user_profile=form_context["user_profile"],
                job_data=form_context["job_data"],
                form_fields=form_fields,
                resume_content=form_context.get("resume_content"),
                cover_letter_content=form_context.get("cover_letter_content")
            )
            
            if not filling_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Form filling failed: {filling_result.get('error')}"
                )
            
            filled_fields = filling_result.get("filled_fields", {})
            
            # Validate and sanitize filled data
            validated_fields = await self._validate_form_data(filled_fields, form_fields)
            
            logger.info(f"Form filled successfully with {len(validated_fields)} fields")
            
            return {
                "filled_fields": validated_fields,
                "field_count": len(validated_fields),
                "confidence_scores": filling_result.get("confidence_scores", {}),
                "suggestions": filling_result.get("suggestions", []),
                "warnings": filling_result.get("warnings", []),
                "success": True,
                "metadata": {
                    "model_used": "mistral-7b-instruct",
                    "filling_time": filling_result.get("processing_time"),
                    "field_types_handled": list(set([field.get("type") for field in form_fields]))
                }
            }
            
        except Exception as e:
            logger.error(f"Form filling failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Form filling failed: {str(e)}")
    
    async def analyze_application_requirements(
        self,
        job_id: int,
        application_url: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Analyze application requirements and form fields for a job.
        
        Args:
            job_id: ID of the job
            application_url: Optional specific application URL
            db: Database session
            
        Returns:
            Dictionary containing application requirements analysis
        """
        try:
            if not db:
                db = next(get_db())
            
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            url_to_analyze = application_url or job.url
            
            logger.info(f"Analyzing application requirements for job {job_id}")
            
            # Get Mistral service
            mistral_service = await self.get_mistral_service()
            
            # Analyze application requirements
            analysis_result = await mistral_service.analyze_application_requirements(
                job_url=url_to_analyze,
                job_description=job.description,
                company=job.company
            )
            
            if not analysis_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail="Application requirements analysis failed"
                )
            
            requirements = {
                "platform": analysis_result.get("platform", "unknown"),
                "application_method": analysis_result.get("application_method", "external"),
                "required_fields": analysis_result.get("required_fields", []),
                "optional_fields": analysis_result.get("optional_fields", []),
                "document_requirements": analysis_result.get("document_requirements", {}),
                "automation_feasibility": analysis_result.get("automation_feasibility", "low"),
                "estimated_time": analysis_result.get("estimated_time_minutes", 15),
                "special_requirements": analysis_result.get("special_requirements", []),
                "tips": analysis_result.get("application_tips", []),
                "common_questions": analysis_result.get("common_questions", [])
            }
            
            logger.info("Application requirements analysis completed")
            
            return {
                "requirements": requirements,
                "analysis_metadata": {
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "model_used": "mistral-7b-instruct",
                    "url_analyzed": url_to_analyze,
                    "confidence": analysis_result.get("confidence", 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Application requirements analysis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    async def get_application_status(
        self,
        application_id: int,
        user_id: int,
        db: Session = None
    ) -> Optional[Application]:
        """Get application status and details."""
        if not db:
            db = next(get_db())
        
        return db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == user_id
        ).first()
    
    async def update_application_status(
        self,
        application_id: int,
        user_id: int,
        status: str,
        notes: Optional[str] = None,
        db: Session = None
    ) -> Optional[Application]:
        """Update application status."""
        try:
            if not db:
                db = next(get_db())
            
            application = await self.get_application_status(application_id, user_id, db)
            if not application:
                return None
            
            application.status = status
            application.updated_at = datetime.utcnow()
            
            if notes:
                if not application.notes:
                    application.notes = []
                application.notes.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "note": notes,
                    "status": status
                })
            
            db.commit()
            db.refresh(application)
            
            logger.info(f"Application {application_id} status updated to {status}")
            return application
            
        except Exception as e:
            logger.error(f"Application status update failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Status update failed: {str(e)}")
    
    async def get_user_applications(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        db: Session = None
    ) -> List[Application]:
        """Get applications for a user with optional filtering."""
        if not db:
            db = next(get_db())
        
        query = db.query(Application).filter(Application.user_id == user_id)
        
        if status:
            query = query.filter(Application.status == status)
        
        return query.order_by(Application.submitted_at.desc()).offset(offset).limit(limit).all()
    
    # Private helper methods
    
    async def _prepare_application_context(
        self,
        user: User,
        job: Job,
        resume: Optional[Document],
        cover_letter: Optional[Document],
        custom_answers: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Prepare context data for application submission."""
        context = {
            "user_profile": {
                "personal_info": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "address": user.address,
                    "city": user.city,
                    "state": user.state,
                    "country": user.country,
                    "postal_code": user.postal_code
                },
                "professional_info": {
                    "summary": user.professional_summary,
                    "experience": user.work_experience,
                    "education": user.education,
                    "skills": user.skills,
                    "certifications": user.certifications,
                    "languages": user.languages
                },
                "preferences": {
                    "salary_expectation": user.salary_expectation,
                    "availability": user.availability,
                    "work_authorization": user.work_authorization,
                    "willing_to_relocate": user.willing_to_relocate,
                    "remote_preference": user.remote_preference
                }
            },
            "job_data": {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "description": job.description,
                "requirements": job.requirements,
                "url": job.url
            },
            "documents": {},
            "custom_answers": custom_answers or {}
        }
        
        if resume:
            context["documents"]["resume"] = {
                "id": resume.id,
                "content": resume.content,
                "template": resume.template
            }
        
        if cover_letter:
            context["documents"]["cover_letter"] = {
                "id": cover_letter.id,
                "content": cover_letter.content,
                "template": cover_letter.template
            }
        
        return context
    
    async def _prepare_form_filling_context(
        self,
        user: User,
        job: Job,
        resume: Optional[Document],
        cover_letter: Optional[Document],
        form_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare context for form filling."""
        context = {
            "user_profile": {
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "phone": user.phone,
                "address": user.address,
                "experience": user.work_experience,
                "education": user.education,
                "skills": user.skills,
                "certifications": user.certifications
            },
            "job_data": {
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "requirements": job.requirements
            },
            "form_fields": form_fields
        }
        
        if resume:
            context["resume_content"] = resume.content
        
        if cover_letter:
            context["cover_letter_content"] = cover_letter.content
        
        return context
    
    async def _analyze_application_platform(self, job_url: str) -> Dict[str, Any]:
        """Analyze the application platform and determine automation capabilities."""
        parsed_url = urlparse(job_url)
        domain = parsed_url.netloc.lower()
        
        platform_info = {
            "platform": "unknown",
            "supports_automation": False,
            "automation_level": "none",
            "known_challenges": [],
            "recommended_approach": "manual"
        }
        
        # Platform detection logic
        if "linkedin.com" in domain:
            platform_info.update({
                "platform": "linkedin",
                "supports_automation": True,
                "automation_level": "high",
                "recommended_approach": "automated"
            })
        elif "indeed.com" in domain:
            platform_info.update({
                "platform": "indeed",
                "supports_automation": True,
                "automation_level": "medium",
                "recommended_approach": "semi-automated"
            })
        elif "greenhouse.io" in domain:
            platform_info.update({
                "platform": "greenhouse",
                "supports_automation": True,
                "automation_level": "high",
                "recommended_approach": "automated"
            })
        elif "lever.co" in domain:
            platform_info.update({
                "platform": "lever",
                "supports_automation": True,
                "automation_level": "high",
                "recommended_approach": "automated"
            })
        elif "workday.com" in domain:
            platform_info.update({
                "platform": "workday",
                "supports_automation": False,
                "automation_level": "low",
                "known_challenges": ["Complex multi-step forms", "Dynamic field validation"],
                "recommended_approach": "manual"
            })
        
        return platform_info
    
    async def _submit_automated_application(
        self,
        mistral_service: MistralService,
        context: Dict[str, Any],
        platform_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit application automatically using Mistral 7B."""
        try:
            result = await mistral_service.submit_automated_application(
                application_context=context,
                platform_info=platform_info
            )
            
            return {
                "success": result.get("success", False),
                "status": "submitted" if result.get("success") else "failed",
                "automation_level": "full",
                "fields_filled": result.get("fields_filled", 0),
                "confidence": result.get("confidence", 0.0),
                "tracking_url": result.get("tracking_url"),
                "reference_number": result.get("reference_number"),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Automated application submission failed: {str(e)}")
            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "automation_level": "failed"
            }
    
    async def _prepare_manual_application(
        self,
        mistral_service: MistralService,
        context: Dict[str, Any],
        platform_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare data for manual application submission."""
        try:
            result = await mistral_service.prepare_manual_application(
                application_context=context,
                platform_info=platform_info
            )
            
            return {
                "success": True,
                "status": "prepared",
                "automation_level": "preparation",
                "prepared_data": result.get("prepared_data", {}),
                "instructions": result.get("instructions", []),
                "confidence": result.get("confidence", 0.0),
                "estimated_time": result.get("estimated_time_minutes", 15)
            }
            
        except Exception as e:
            logger.error(f"Manual application preparation failed: {str(e)}")
            return {
                "success": False,
                "status": "preparation_failed",
                "error": str(e)
            }
    
    async def _validate_form_data(
        self,
        filled_fields: Dict[str, Any],
        form_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate and sanitize filled form data."""
        validated_fields = {}
        
        for field_name, field_value in filled_fields.items():
            # Find field definition
            field_def = next(
                (field for field in form_fields if field.get("name") == field_name),
                None
            )
            
            if field_def:
                # Sanitize input based on field type
                field_type = field_def.get("type", "text")
                
                if field_type == "email":
                    validated_fields[field_name] = sanitize_input(str(field_value))
                elif field_type == "phone":
                    validated_fields[field_name] = re.sub(r'[^\d\-\(\)\+\s]', '', str(field_value))
                elif field_type == "text" or field_type == "textarea":
                    validated_fields[field_name] = sanitize_input(str(field_value))
                else:
                    validated_fields[field_name] = field_value
            else:
                # Unknown field, sanitize as text
                validated_fields[field_name] = sanitize_input(str(field_value))
        
        return validated_fields