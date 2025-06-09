"""Application management endpoints for the job automation system."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.application_history import ApplicationHistory
from app.schemas.application import (
    ApplicationResponse,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatusUpdate,
    ApplicationFilters,
    ApplicationStats,
    BulkApplicationRequest,
    AutoApplicationSettings
)
from app.services.application_service import ApplicationService
from app.services.application_manager import ApplicationManager
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/", response_model=List[ApplicationResponse])
async def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, description="Maximum number of applications to return"),
    offset: int = Query(0, description="Number of applications to skip"),
    status: Optional[str] = Query(None, description="Filter by application status"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    job_title: Optional[str] = Query(None, description="Filter by job title"),
    date_from: Optional[datetime] = Query(None, description="Filter applications from date"),
    date_to: Optional[datetime] = Query(None, description="Filter applications to date"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
) -> List[ApplicationResponse]:
    """
    Get paginated list of user's job applications with filtering and sorting.
    """
    try:
        # Build query
        query = db.query(Application).filter(Application.user_id == current_user.id)
        
        # Apply filters
        if status:
            query = query.filter(Application.status == status)
        if company:
            query = query.join(Job).filter(Job.company.ilike(f"%{company}%"))
        if job_title:
            query = query.join(Job).filter(Job.title.ilike(f"%{job_title}%"))
        if date_from:
            query = query.filter(Application.created_at >= date_from)
        if date_to:
            query = query.filter(Application.created_at <= date_to)
        
        # Apply sorting
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(Application, sort_by)))
        else:
            query = query.order_by(getattr(Application, sort_by))
        
        # Apply pagination
        applications = query.offset(offset).limit(limit).all()
        
        return applications
        
    except Exception as e:
        logger.error(f"Error fetching applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch applications"
        )


@router.post("/", response_model=ApplicationResponse)
async def create_application(
    application_data: ApplicationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> ApplicationResponse:
    """Create a new job application."""
    
    try:
        # Check for duplicates
        existing_application = db.query(Application).filter(
            and_(
                Application.user_id == current_user.id,
                Application.job_id == application_data.job_id
            )
        ).first()
        
        if existing_application:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application already exists for this job"
            )
        
        # Create new application
        application = Application(
            user_id=current_user.id,
            **application_data.dict()
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        
        # Add background task for notifications
        background_tasks.add_task(
            NotificationService.send_application_confirmation,
            current_user.email,
            application.id
        )
        
        return application
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating application: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application"
        )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> ApplicationResponse:
    """Get a specific application by ID."""
    
    application = db.query(Application).filter(
        and_(
            Application.id == application_id,
            Application.user_id == current_user.id
        )
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    application_update: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> ApplicationResponse:
    """Update an existing application."""
    
    application = db.query(Application).filter(
        and_(
            Application.id == application_id,
            Application.user_id == current_user.id
        )
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    try:
        # Update fields
        for field, value in application_update.dict(exclude_unset=True).items():
            setattr(application, field, value)
        
        db.commit()
        db.refresh(application)
        
        return application
        
    except Exception as e:
        logger.error(f"Error updating application: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application"
        )


@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an application."""
    
    application = db.query(Application).filter(
        and_(
            Application.id == application_id,
            Application.user_id == current_user.id
        )
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    try:
        db.delete(application)
        db.commit()
        
        return {"message": "Application deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting application: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete application"
        )
