"""Document generation endpoints for the job automation system."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import os
import uuid

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.job import Job
from app.models.document import Document
from app.schemas.document import (
    DocumentResponse,
    DocumentCreate,
    DocumentUpdate,
    ResumeGenerationRequest,
    CoverLetterGenerationRequest,
    DocumentTemplate,
    DocumentAnalysis,
    BulkDocumentRequest
)
from app.services.document_service import DocumentService
from app.services.llm.model_manager import ModelManager
from app.utils.file_handling import save_uploaded_file, generate_pdf, validate_file_type

router = APIRouter()


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    limit: int = Query(50, description="Maximum number of documents to return"),
    offset: int = Query(0, description="Number of documents to skip")
) -> List[DocumentResponse]:
    """
    Get user's documents with optional filtering.
    
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :param document_type: Filter by document type
    :type document_type: Optional[str]
    :param limit: Maximum number of documents to return
    :type limit: int
    :param offset: Number of documents to skip
    :type offset: int
    :return: List of user documents
    :rtype: List[DocumentResponse]
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    query = query.order_by(desc(Document.created_at))
    documents = query.offset(offset).limit(limit).all()
    
    return [DocumentResponse.from_orm(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Get specific document by ID.
    
    :param document_id: Document ID to retrieve
    :type document_id: int
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Document details
    :rtype: DocumentResponse
    :raises HTTPException: If document not found
    """
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse.from_orm(document)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query(..., description="Type of document (resume, cover_letter, portfolio)"),
    title: Optional[str] = Query(None, description="Document title"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Upload a document file.
    
    :param file: File to upload
    :type file: UploadFile
    :param document_type: Type of document
    :type document_type: str
    :param title: Document title
    :type title: Optional[str]
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Created document record
    :rtype: DocumentResponse
    :raises HTTPException: If file type is invalid
    """
    # Validate file type
    if not validate_file_type(file.filename, allowed_types=['.pdf', '.docx', '.doc', '.txt']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF, DOCX, DOC, and TXT files are allowed."
        )
    
    # Save uploaded file
    file_path = await save_uploaded_file(file, current_user.id)
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        title=title or file.filename,
        document_type=document_type,
        file_path=file_path,
        file_name=file.filename,
        file_size=file.size or 0,
        is_generated=False,
        created_at=datetime.utcnow()
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)


@router.post("/generate/resume", response_model=DocumentResponse)
async def generate_resume(
    generation_request: ResumeGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Generate a customized resume using AI.
    
    :param generation_request: Resume generation parameters
    :type generation_request: ResumeGenerationRequest
    :param background_tasks: Background task queue
    :type background_tasks: BackgroundTasks
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Generated resume document
    :rtype: DocumentResponse
    """
    document_service = DocumentService(db)
    
    # Generate resume content
    resume_content = await document_service.generate_resume(
        user=current_user,
        job_description=generation_request.job_description,
        template=generation_request.template,
        include_sections=generation_request.include_sections,
        focus_keywords=generation_request.focus_keywords
    )
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        title=generation_request.title or f"Resume - {datetime.now().strftime('%Y-%m-%d')}",
        document_type="resume",
        content=resume_content,
        job_id=generation_request.job_id,
        template_used=generation_request.template,
        is_generated=True,
        generation_metadata={
            "model_used": generation_request.model_preference or "phi3",
            "keywords_focused": generation_request.focus_keywords,
            "sections_included": generation_request.include_sections,
            "job_description_analyzed": bool(generation_request.job_description)
        },
        created_at=datetime.utcnow()
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Generate PDF in background if requested
    if generation_request.generate_pdf:
        background_tasks.add_task(
            _generate_document_pdf,
            document.id,
            db
        )
    
    return DocumentResponse.from_orm(document)


@router.post("/generate/cover-letter", response_model=DocumentResponse)
async def generate_cover_letter(
    generation_request: CoverLetterGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Generate a customized cover letter using AI.
    
    :param generation_request: Cover letter generation parameters
    :type generation_request: CoverLetterGenerationRequest
    :param background_tasks: Background task queue
    :type background_tasks: BackgroundTasks
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Generated cover letter document
    :rtype: DocumentResponse
    """
    document_service = DocumentService(db)
    
    # Get job details if job_id provided
    job = None
    if generation_request.job_id:
        job = db.query(Job).filter(Job.id == generation_request.job_id).first()
    
    # Generate cover letter content
    cover_letter_content = await document_service.generate_cover_letter(
        user=current_user,
        job=job,
        company_name=generation_request.company_name,
        job_title=generation_request.job_title,
        job_description=generation_request.job_description,
        template=generation_request.template,
        tone=generation_request.tone,
        key_achievements=generation_request.key_achievements,
        custom_message=generation_request.custom_message
    )
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        title=generation_request.title or f"Cover Letter - {generation_request.company_name}",
        document_type="cover_letter",
        content=cover_letter_content,
        job_id=generation_request.job_id,
        template_used=generation_request.template,
        is_generated=True,
        generation_metadata={
            "model_used": generation_request.model_preference or "phi3",
            "tone": generation_request.tone,
            "company_name": generation_request.company_name,
            "job_title": generation_request.job_title,
            "achievements_highlighted": len(generation_request.key_achievements or [])
        },
        created_at=datetime.utcnow()
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Generate PDF in background if requested
    if generation_request.generate_pdf:
        background_tasks.add_task(
            _generate_document_pdf,
            document.id,
            db
        )
    
    return DocumentResponse.from_orm(document)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Update document content or metadata.
    
    :param document_id: Document ID to update
    :type document_id: int
    :param document_update: Document update data
    :type document_update: DocumentUpdate
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Updated document
    :rtype: DocumentResponse
    :raises HTTPException: If document not found
    """
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update document fields
    for field, value in document_update.dict(exclude_unset=True).items():
        if hasattr(document, field):
            setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Delete a document and its associated files.
    
    :param document_id: Document ID to delete
    :type document_id: int
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Deletion confirmation
    :rtype: Dict[str, str]
    :raises HTTPException: If document not found
    """
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete associated files
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    if document.pdf_path and os.path.exists(document.pdf_path):
        os.remove(document.pdf_path)
    
    # Delete document record
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    format: str = Query("original", description="Download format: original, pdf, txt"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """
    Download document in specified format.
    
    :param document_id: Document ID to download
    :type document_id: int
    :param format: Download format
    :type format: str
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: File response with document
    :rtype: FileResponse
    :raises HTTPException: If document not found or format unavailable
    """
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if format == "pdf":
        if not document.pdf_path or not os.path.exists(document.pdf_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF version not available. Please generate PDF first."
            )
        return FileResponse(
            document.pdf_path,
            media_type="application/pdf",
            filename=f"{document.title}.pdf"
        )
    
    elif format == "txt" and document.content:
        # Create temporary text file
        temp_path = f"/tmp/{uuid.uuid4()}.txt"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(document.content)
        
        return FileResponse(
            temp_path,
            media_type="text/plain",
            filename=f"{document.title}.txt"
        )
    
    elif format == "original" and document.file_path:
        if not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original file not found"
            )
        
        return FileResponse(
            document.file_path,
            filename=document.file_name or f"{document.title}"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format requested or file not available"
        )


@router.post("/{document_id}/generate-pdf")
async def generate_document_pdf(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Generate PDF version of document.
    
    :param document_id: Document ID to generate PDF for
    :type document_id: int
    :param background_tasks: Background task queue
    :type background_tasks: BackgroundTasks
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: PDF generation confirmation
    :rtype: Dict[str, str]
    :raises HTTPException: If document not found or has no content
    """
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no content to convert to PDF"
        )
    
    # Generate PDF in background
    background_tasks.add_task(_generate_document_pdf, document_id, db)
    
    return {"message": "PDF generation initiated. Check back in a few moments."}


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    analysis_type: str = Query("ats_score", description="Type of analysis: ats_score, keywords, suggestions"),
    current_user: User = Depends(get_current_active_user)
) -> DocumentAnalysis:
    """
    Analyze document for ATS compatibility, keywords, and suggestions.
    
    :param file: File to analyze
    :type file: UploadFile
    :param analysis_type: Type of analysis to perform
    :type analysis_type: str
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Document analysis results
    :rtype: DocumentAnalysis
    :raises HTTPException: If file type invalid or analysis fails
    """
    # Validate file type
    if not validate_file_type(file.filename, allowed_types=['.pdf', '.docx', '.doc', '.txt']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type for analysis"
        )
    
    document_service = DocumentService(db=None)
    
    try:
        # Extract text from uploaded file
        file_content = await file.read()
        extracted_text = await document_service.extract_text_from_file(
            file_content, 
            file.filename
        )
        
        # Perform analysis based on type
        analysis_result: Dict[str, Any]
        if analysis_type == "ats_score":
            analysis_result = await document_service.analyze_ats_compatibility(extracted_text)
        elif analysis_type == "keywords":
            analysis_result = await document_service.extract_keywords(extracted_text)
        elif analysis_type == "suggestions":
            analysis_result = await document_service.generate_improvement_suggestions(extracted_text)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid analysis type"
            )
        
        return DocumentAnalysis(
            analysis_type=analysis_type,
            results=analysis_result,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/templates/", response_model=List[DocumentTemplate])
async def get_document_templates(
    document_type: str = Query(..., description="Type of templates: resume, cover_letter"),
    current_user: User = Depends(get_current_active_user)
) -> List[DocumentTemplate]:
    """
    Get available document templates.
    
    :param document_type: Type of templates to retrieve
    :type document_type: str
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: List of available templates
    :rtype: List[DocumentTemplate]
    """
    document_service = DocumentService(db=None)
    templates = document_service.get_available_templates(document_type)
    
    return [
        DocumentTemplate(
            id=template["id"],
            name=template["name"],
            description=template["description"],
            document_type=document_type,
            preview_url=template.get("preview_url"),
            is_premium=template.get("is_premium", False)
        )
        for template in templates
    ]


@router.post("/bulk-generate")
async def bulk_generate_documents(
    bulk_request: BulkDocumentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Generate documents for multiple jobs in bulk.
    
    :param bulk_request: Bulk generation request data
    :type bulk_request: BulkDocumentRequest
    :param background_tasks: Background task queue
    :type background_tasks: BackgroundTasks
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :return: Bulk generation initiation confirmation
    :rtype: Dict[str, Any]
    :raises HTTPException: If too many jobs requested
    """
    if len(bulk_request.job_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 jobs allowed per bulk request"
        )
    
    # Add bulk generation task to background
    background_tasks.add_task(
        _process_bulk_document_generation,
        bulk_request,
        current_user.id,
        db
    )
    
    return {
        "message": f"Bulk document generation initiated for {len(bulk_request.job_ids)} jobs",
        "job_count": len(bulk_request.job_ids),
        "document_types": bulk_request.document_types,
        "estimated_completion": f"{len(bulk_request.job_ids) * 2} minutes"
    }


@router.get("/stats/usage")
async def get_document_usage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days: int = Query(30, description="Number of days to analyze")
) -> Dict[str, Any]:
    """
    Get document generation and usage statistics.
    
    :param db: Database session
    :type db: Session
    :param current_user: Currently authenticated user
    :type current_user: User
    :param days: Number of days to analyze
    :type days: int
    :return: Document usage statistics
    :rtype: Dict[str, Any]
    """
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get documents from the specified time period
    documents = db.query(Document).filter(
        and_(
            Document.user_id == current_user.id,
            Document.created_at >= cutoff_date
        )
    ).all()
    
    total_documents = len(documents)
    generated_documents = len([doc for doc in documents if doc.is_generated])
    uploaded_documents = total_documents - generated_documents
    
    # Document type breakdown
    type_breakdown: Dict[str, int] = {}
    for doc in documents:
        doc_type = doc.document_type
        type_breakdown[doc_type] = type_breakdown.get(doc_type, 0) + 1
    
    # Template usage
    template_usage: Dict[str, int] = {}
    for doc in documents:
        if doc.template_used:
            template = doc.template_used
            template_usage[template] = template_usage.get(template, 0) + 1
    
    return {
        "total_documents": total_documents,
        "generated_documents": generated_documents,
        "uploaded_documents": uploaded_documents,
        "type_breakdown": type_breakdown,
        "template_usage": template_usage,
        "period_days": days,
        "generation_rate": generated_documents / max(days, 1),
        "most_used_template": max(template_usage.items(), key=lambda x: x[1])[0] if template_usage else None
    }


async def _generate_document_pdf(document_id: int, db: Session) -> None:
    """
    Background task to generate PDF from document content.
    
    :param document_id: Document ID to generate PDF for
    :type document_id: int
    :param db: Database session
    :type db: Session
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or not document.content:
        return
    
    try:
        # Generate PDF file
        pdf_path = await generate_pdf(
            content=document.content, 
            title=document.title, 
            user_id=document.user_id
        )
        
        # Update document with PDF path
        document.pdf_path = pdf_path
        document.pdf_generated_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        print(f"Error generating PDF for document {document_id}: {str(e)}")


async def _process_bulk_document_generation(
    bulk_request: BulkDocumentRequest,
    user_id: int,
    db: Session
) -> None:
    """
    Background task to process bulk document generation.
    
    :param bulk_request: Bulk generation request data
    :type bulk_request: BulkDocumentRequest
    :param user_id: User ID for document generation
    :type user_id: int
    :param db: Database session
    :type db: Session
    """
    document_service = DocumentService(db)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return
    
    successful_generations = 0
    failed_generations = 0
    
    for job_id in bulk_request.job_ids:
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                failed_generations += 1
                continue
            
            # Generate requested document types
            for doc_type in bulk_request.document_types:
                try:
                    content: str
                    if doc_type == "resume":
                        content = await document_service.generate_resume(
                            user=user,
                            job_description=job.description,
                            template=bulk_request.template,
                            include_sections=None,
                            focus_keywords=None
                        )
                    elif doc_type == "cover_letter":
                        content = await document_service.generate_cover_letter(
                            user=user,
                            job=job,
                            company_name=job.company_name,
                            job_title=job.title,
                            job_description=job.description,
                            template=bulk_request.template,
                            tone=None,
                            key_achievements=None,
                            custom_message=None
                        )
                    else:
                        continue
                    
                    # Create document record
                    document = Document(
                        user_id=user_id,
                        title=f"{doc_type.title()} - {job.company_name} - {job.title}",
                        document_type=doc_type,
                        content=content,
                        job_id=job_id,
                        template_used=bulk_request.template,
                        is_generated=True,
                        generation_metadata={
                            "bulk_generated": True,
                            "model_used": "phi3"
                        },
                        created_at=datetime.utcnow()
                    )
                    
                    db.add(document)
                    successful_generations += 1
                    
                except Exception as e:
                    print(f"Error generating {doc_type} for job {job_id}: {str(e)}")
                    failed_generations += 1
            
            # Add delay between jobs
            import asyncio
            await asyncio.sleep(bulk_request.delay_between_generations or 10)
            
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            failed_generations += 1
    
    db.commit()
    
    # Send completion notification
    try:
        from app.services.notification_service import NotificationService
        notification_service = NotificationService()
        await notification_service.send_bulk_generation_summary(
            user_id=user_id,
            successful=successful_generations,
            failed=failed_generations
        )
    except ImportError:
        # Handle case where notification service is not available
        print(f"Bulk generation completed: {successful_generations} successful, {failed_generations} failed")