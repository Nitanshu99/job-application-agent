"""
Document generation service for AI-powered job automation system.

This service handles the generation of personalized resumes and cover letters
using the Phi-3 Mini model. It integrates with user profiles, job data, and 
document templates to create tailored application documents.

Features:
- Resume generation with multiple templates
- Cover letter generation with personalization
- Document formatting and styling
- Template management and customization
- Integration with LLM services
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.llm.phi3_service import Phi3Service
from app.templates.resume_template import ResumeTemplate
from app.templates.cover_letter_template import CoverLetterTemplate
from app.utils.text_processing import clean_text, extract_keywords
from app.utils.file_handling import save_file, generate_thumbnail
from app.utils.validation import validate_user_data

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for generating and managing job application documents."""
    
    def __init__(self):
        self.phi3_service = None
        self.resume_template = ResumeTemplate()
        self.cover_letter_template = CoverLetterTemplate()
        
    async def get_phi3_service(self) -> Phi3Service:
        """Get or initialize Phi-3 service."""
        if not self.phi3_service:
            self.phi3_service = Phi3Service()
            await self.phi3_service.initialize()
        return self.phi3_service
    
    async def generate_resume(
        self,
        user_id: int,
        job_id: int,
        template: str = "modern",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized resume for a specific job.
        
        Args:
            user_id: ID of the user
            job_id: ID of the target job
            template: Resume template to use
            db: Database session
            
        Returns:
            Dictionary containing generated resume data
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
            
            # Validate user data
            if not validate_user_data(user.__dict__):
                raise HTTPException(status_code=400, detail="Incomplete user profile")
            
            logger.info(f"Generating resume for user {user_id} and job {job_id}")
            
            # Prepare context for resume generation
            context = await self._prepare_resume_context(user, job, template)
            
            # Get Phi-3 service
            phi3_service = await self.get_phi3_service()
            
            # Generate resume content using Phi-3
            generation_result = await phi3_service.generate_resume(
                user_profile=context["user_profile"],
                job_description=context["job_description"],
                template=template,
                max_length=2000
            )
            
            if not generation_result.get("success"):
                raise HTTPException(
                    status_code=500, 
                    detail=f"Resume generation failed: {generation_result.get('error')}"
                )
            
            # Process and format the generated content
            resume_content = generation_result["content"]
            formatted_resume = await self._format_resume(resume_content, template)
            
            # Extract keywords for relevance scoring
            keywords = extract_keywords(resume_content)
            
            # Save document to database
            document_data = {
                "user_id": user_id,
                "job_id": job_id,
                "type": "resume",
                "template": template,
                "content": formatted_resume,
                "keywords": keywords,
                "generated_at": datetime.utcnow(),
                "model_used": "phi3-mini",
                "generation_metadata": {
                    "template": template,
                    "word_count": len(resume_content.split()),
                    "keywords_count": len(keywords),
                    "relevance_score": await self._calculate_relevance_score(resume_content, job.description)
                }
            }
            
            document = Document(**document_data)
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"Resume generated successfully with ID {document.id}")
            
            return {
                "id": document.id,
                "content": formatted_resume,
                "template": template,
                "keywords": keywords,
                "metadata": document.generation_metadata,
                "success": True,
                "model_used": "phi3-mini"
            }
            
        except Exception as e:
            logger.error(f"Resume generation failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Resume generation failed: {str(e)}")
    
    async def generate_cover_letter(
        self,
        user_id: int,
        job_id: int,
        template: str = "professional",
        custom_notes: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized cover letter for a specific job.
        
        Args:
            user_id: ID of the user
            job_id: ID of the target job
            template: Cover letter template to use
            custom_notes: Additional custom notes to include
            db: Database session
            
        Returns:
            Dictionary containing generated cover letter data
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
            
            logger.info(f"Generating cover letter for user {user_id} and job {job_id}")
            
            # Prepare context for cover letter generation
            context = await self._prepare_cover_letter_context(user, job, template, custom_notes)
            
            # Get Phi-3 service
            phi3_service = await self.get_phi3_service()
            
            # Generate cover letter content using Phi-3
            generation_result = await phi3_service.generate_cover_letter(
                user_profile=context["user_profile"],
                job_description=context["job_description"],
                company_info=context["company_info"],
                template=template,
                custom_notes=custom_notes,
                max_length=800
            )
            
            if not generation_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Cover letter generation failed: {generation_result.get('error')}"
                )
            
            # Process and format the generated content
            cover_letter_content = generation_result["content"]
            formatted_cover_letter = await self._format_cover_letter(cover_letter_content, template)
            
            # Extract keywords for relevance scoring
            keywords = extract_keywords(cover_letter_content)
            
            # Save document to database
            document_data = {
                "user_id": user_id,
                "job_id": job_id,
                "type": "cover_letter",
                "template": template,
                "content": formatted_cover_letter,
                "keywords": keywords,
                "generated_at": datetime.utcnow(),
                "model_used": "phi3-mini",
                "generation_metadata": {
                    "template": template,
                    "word_count": len(cover_letter_content.split()),
                    "keywords_count": len(keywords),
                    "custom_notes_included": bool(custom_notes),
                    "relevance_score": await self._calculate_relevance_score(cover_letter_content, job.description)
                }
            }
            
            document = Document(**document_data)
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"Cover letter generated successfully with ID {document.id}")
            
            return {
                "id": document.id,
                "content": formatted_cover_letter,
                "template": template,
                "keywords": keywords,
                "metadata": document.generation_metadata,
                "success": True,
                "model_used": "phi3-mini"
            }
            
        except Exception as e:
            logger.error(f"Cover letter generation failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")
    
    async def get_document(self, document_id: int, user_id: int, db: Session = None) -> Optional[Document]:
        """Get a document by ID for a specific user."""
        if not db:
            db = next(get_db())
        
        return db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
    
    async def list_user_documents(
        self,
        user_id: int,
        document_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        db: Session = None
    ) -> List[Document]:
        """List documents for a user with optional filtering."""
        if not db:
            db = next(get_db())
        
        query = db.query(Document).filter(Document.user_id == user_id)
        
        if document_type:
            query = query.filter(Document.type == document_type)
        
        return query.order_by(Document.generated_at.desc()).offset(offset).limit(limit).all()
    
    async def delete_document(self, document_id: int, user_id: int, db: Session = None) -> bool:
        """Delete a document for a specific user."""
        if not db:
            db = next(get_db())
        
        document = await self.get_document(document_id, user_id, db)
        if not document:
            return False
        
        db.delete(document)
        db.commit()
        return True
    
    async def regenerate_document(
        self,
        document_id: int,
        user_id: int,
        template: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Regenerate an existing document with optional template change."""
        if not db:
            db = next(get_db())
        
        # Get existing document
        existing_doc = await self.get_document(document_id, user_id, db)
        if not existing_doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Use new template or existing one
        template = template or existing_doc.template
        
        # Regenerate based on document type
        if existing_doc.type == "resume":
            return await self.generate_resume(user_id, existing_doc.job_id, template, db)
        elif existing_doc.type == "cover_letter":
            return await self.generate_cover_letter(user_id, existing_doc.job_id, template, db)
        else:
            raise HTTPException(status_code=400, detail="Unknown document type")
    
    # Private helper methods
    
    async def _prepare_resume_context(self, user: User, job: Job, template: str) -> Dict[str, Any]:
        """Prepare context data for resume generation."""
        return {
            "user_profile": {
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "phone": user.phone,
                "location": user.location,
                "summary": user.professional_summary,
                "experience": user.work_experience,
                "education": user.education,
                "skills": user.skills,
                "certifications": user.certifications,
                "projects": user.projects
            },
            "job_description": {
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "requirements": job.requirements,
                "skills_required": job.skills_required,
                "experience_level": job.experience_level
            },
            "template": template
        }
    
    async def _prepare_cover_letter_context(
        self,
        user: User,
        job: Job,
        template: str,
        custom_notes: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare context data for cover letter generation."""
        return {
            "user_profile": {
                "name": f"{user.first_name} {user.last_name}",
                "professional_summary": user.professional_summary,
                "key_achievements": user.key_achievements,
                "experience": user.work_experience,
                "skills": user.skills,
                "motivation": user.career_goals
            },
            "job_description": {
                "title": job.title,
                "description": job.description,
                "requirements": job.requirements,
                "company_culture": job.company_culture
            },
            "company_info": {
                "name": job.company,
                "industry": job.industry,
                "size": job.company_size,
                "location": job.location
            },
            "template": template,
            "custom_notes": custom_notes
        }
    
    async def _format_resume(self, content: str, template: str) -> str:
        """Format resume content using the specified template."""
        return await self.resume_template.format_content(content, template)
    
    async def _format_cover_letter(self, content: str, template: str) -> str:
        """Format cover letter content using the specified template."""
        return await self.cover_letter_template.format_content(content, template)
    
    async def _calculate_relevance_score(self, document_content: str, job_description: str) -> float:
        """Calculate relevance score between document content and job description."""
        try:
            from app.utils.text_processing import similarity_score
            return similarity_score(document_content, job_description)
        except Exception as e:
            logger.warning(f"Failed to calculate relevance score: {str(e)}")
            return 0.0
    
    async def get_generation_statistics(self, user_id: int, db: Session = None) -> Dict[str, Any]:
        """Get document generation statistics for a user."""
        if not db:
            db = next(get_db())
        
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        
        stats = {
            "total_documents": len(documents),
            "resumes_generated": len([d for d in documents if d.type == "resume"]),
            "cover_letters_generated": len([d for d in documents if d.type == "cover_letter"]),
            "templates_used": list(set([d.template for d in documents])),
            "average_relevance_score": sum([
                d.generation_metadata.get("relevance_score", 0) for d in documents
            ]) / max(len(documents), 1),
            "most_recent_generation": max([d.generated_at for d in documents]) if documents else None
        }
        
        return stats