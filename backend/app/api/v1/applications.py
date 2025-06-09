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
):
    """
    Get paginated list of user's job applications with filtering and sorting.
    """
    query = db.query(Application).filter(Application.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Application.status == status)
    
    if company:
        query = query.filter(Application.company_name.ilike(f"%{company}%"))
    
    if job_title:
        query = query.filter(Application.job_title.ilike(f"%{job_title}%"))
    
    if date_from:
        query = query.filter(Application.created_at >= date_from)
    
    if date_to:
        query = query.filter(Application.created_at <= date_to)
    
    # Apply sorting
    if hasattr(Application, sort_by):
        sort_column = getattr(Application, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
    
    # Execute query with pagination
    applications = query.offset(offset).limit(limit).all()
    
    return [ApplicationResponse.from_orm(app) for app in applications]


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific application by ID.
    """
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
    
    return ApplicationResponse.from_orm(application)


@router.post("/", response_model=ApplicationResponse)
async def create_application(
    application_data: ApplicationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new job application.
    """
    application_manager = ApplicationManager(db)
    
    # Check for duplicate applications
    is_duplicate = await application_manager.check_duplicate_application(
        user_id=current_user.id,
        job_id=application_data.job_id,
        company_name=application_data.company_name,
        job_title=application_data.job_title
    )
    
    if is_duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job or a similar position at this company"
        )
    
    # Create application
    application = Application(
        user_id=current_user.id,
        job_id=application_data.job_id,
        job_title=application_data.job_title,
        company_name=application_data.company_name,
        job_url=application_data.job_url,
        status="pending",
        applied_at=datetime.utcnow(),
        resume_used=application_data.resume_used,
        cover_letter_used=application_data.cover_letter_used,
        notes=application_data.notes,
        source=application_data.source,
        salary_offered=application_data.salary_offered,
        location=application_data.location,
        employment_type=application_data.employment_type
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    # Create application history entry
    history_entry = ApplicationHistory(
        application_id=application.id,
        status="pending",
        notes="Application submitted",
        changed_by=current_user.id,
        changed_at=datetime.utcnow()
    )
    db.add(history_entry)
    db.commit()
    
    # Send notification
    background_tasks.add_task(
        _send_application_notification,
        application.id,
        "Application submitted successfully"
    )
    
    return ApplicationResponse.from_orm(application)


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    application_data: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing application.
    """
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
    
    # Update application fields
    for field, value in application_data.dict(exclude_unset=True).items():
        if hasattr(application, field):
            setattr(application, field, value)
    
    application.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    
    return ApplicationResponse.from_orm(application)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update application status and add history entry.
    """
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
    
    old_status = application.status
    application.status = status_update.status
    application.updated_at = datetime.utcnow()
    
    # Update specific status fields
    if status_update.status == "interview":
        application.interview_date = status_update.interview_date
    elif status_update.status == "offer":
        application.offer_date = datetime.utcnow()
        application.salary_offered = status_update.salary_offered
    elif status_update.status == "rejected":
        application.rejection_date = datetime.utcnow()
        application.rejection_reason = status_update.rejection_reason
    
    db.commit()
    
    # Create history entry
    history_entry = ApplicationHistory(
        application_id=application.id,
        status=status_update.status,
        notes=status_update.notes or f"Status changed from {old_status} to {status_update.status}",
        changed_by=current_user.id,
        changed_at=datetime.utcnow(),
        interview_date=status_update.interview_date,
        salary_offered=status_update.salary_offered,
        rejection_reason=status_update.rejection_reason
    )
    db.add(history_entry)
    db.commit()
    
    # Send notification for important status changes
    if status_update.status in ["interview", "offer", "rejected"]:
        background_tasks.add_task(
            _send_application_notification,
            application.id,
            f"Application status updated to {status_update.status}"
        )
    
    db.refresh(application)
    return ApplicationResponse.from_orm(application)


@router.get("/{application_id}/history")
async def get_application_history(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get application status history.
    """
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
    
    history = db.query(ApplicationHistory).filter(
        ApplicationHistory.application_id == application_id
    ).order_by(desc(ApplicationHistory.changed_at)).all()
    
    return [
        {
            "id": entry.id,
            "status": entry.status,
            "notes": entry.notes,
            "changed_at": entry.changed_at,
            "interview_date": entry.interview_date,
            "salary_offered": entry.salary_offered,
            "rejection_reason": entry.rejection_reason
        }
        for entry in history
    ]


@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an application.
    """
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
    
    # Delete related history entries
    db.query(ApplicationHistory).filter(
        ApplicationHistory.application_id == application_id
    ).delete()
    
    # Delete application
    db.delete(application)
    db.commit()
    
    return {"message": "Application deleted successfully"}


@router.get("/stats/overview", response_model=ApplicationStats)
async def get_application_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get application statistics for the user.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get applications from the specified time period
    applications = db.query(Application).filter(
        and_(
            Application.user_id == current_user.id,
            Application.created_at >= cutoff_date
        )
    ).all()
    
    total_applications = len(applications)
    
    # Calculate status breakdown
    status_counts = {}
    for app in applications:
        status = app.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Calculate response rate
    responses = len([app for app in applications if app.status not in ["pending", "applied"]])
    response_rate = (responses / total_applications * 100) if total_applications > 0 else 0
    
    # Calculate interview rate
    interviews = len([app for app in applications if app.status == "interview"])
    interview_rate = (interviews / total_applications * 100) if total_applications > 0 else 0
    
    # Calculate offer rate
    offers = len([app for app in applications if app.status == "offer"])
    offer_rate = (offers / total_applications * 100) if total_applications > 0 else 0
    
    # Top companies applied to
    company_counts = {}
    for app in applications:
        company = app.company_name
        company_counts[company] = company_counts.get(company, 0) + 1
    
    top_companies = dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    
    return ApplicationStats(
        total_applications=total_applications,
        period_days=days,
        status_breakdown=status_counts,
        response_rate=response_rate,
        interview_rate=interview_rate,
        offer_rate=offer_rate,
        applications_this_week=len([app for app in applications if app.created_at >= datetime.utcnow() - timedelta(days=7)]),
        applications_this_month=len([app for app in applications if app.created_at >= datetime.utcnow() - timedelta(days=30)]),
        top_companies=top_companies,
        average_response_time=_calculate_average_response_time(applications)
    )


@router.post("/bulk-apply")
async def bulk_apply_to_jobs(
    bulk_request: BulkApplicationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Apply to multiple jobs in bulk.
    """
    application_service = ApplicationService(db)
    
    # Add bulk application task to background
    background_tasks.add_task(
        _process_bulk_applications,
        bulk_request,
        current_user.id,
        db
    )
    
    return {
        "message": f"Bulk application process initiated for {len(bulk_request.job_ids)} jobs",
        "job_count": len(bulk_request.job_ids),
        "estimated_completion": "10-30 minutes"
    }


async def _process_bulk_applications(
    bulk_request: BulkApplicationRequest,
    user_id: int,
    db: Session
):
    """
    Background task to process bulk job applications.
    """
    application_service = ApplicationService(db)
    application_manager = ApplicationManager(db)
    
    successful_applications = 0
    failed_applications = 0
    
    for job_id in bulk_request.job_ids:
        try:
            # Get job details
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                failed_applications += 1
                continue
            
            # Check for duplicates
            is_duplicate = await application_manager.check_duplicate_application(
                user_id=user_id,
                job_id=job_id,
                company_name=job.company_name,
                job_title=job.title
            )
            
            if is_duplicate:
                failed_applications += 1
                continue
            
            # Create application
            application = Application(
                user_id=user_id,
                job_id=job_id,
                job_title=job.title,
                company_name=job.company_name,
                job_url=job.external_url,
                status="pending",
                applied_at=datetime.utcnow(),
                resume_used=bulk_request.resume_template,
                cover_letter_used=bulk_request.cover_letter_template,
                notes="Applied via bulk application",
                source=job.source,
                location=job.location,
                employment_type=job.employment_type
            )
            
            db.add(application)
            successful_applications += 1
            
            # Add delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(bulk_request.delay_between_applications or 5)
            
        except Exception as e:
            print(f"Error applying to job {job_id}: {str(e)}")
            failed_applications += 1
            continue
    
    db.commit()
    
    # Send completion notification
    notification_service = NotificationService()
    await notification_service.send_bulk_application_summary(
        user_id=user_id,
        successful=successful_applications,
        failed=failed_applications
    )


@router.get("/automation/settings")
async def get_auto_application_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's auto-application settings.
    """
    return {
        "enabled": current_user.auto_apply_enabled,
        "max_applications_per_day": current_user.max_applications_per_day,
        "preferred_job_titles": current_user.preferred_job_titles or [],
        "preferred_locations": current_user.preferred_locations or [],
        "excluded_companies": current_user.excluded_companies or [],
        "salary_requirements": {
            "min": current_user.salary_min,
            "max": current_user.salary_max
        },
        "employment_types": current_user.employment_type,
        "remote_preference": current_user.remote_preference
    }


@router.put("/automation/settings")
async def update_auto_application_settings(
    settings: AutoApplicationSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user's auto-application settings.
    """
    # Update user settings
    current_user.auto_apply_enabled = settings.enabled
    current_user.max_applications_per_day = settings.max_applications_per_day
    current_user.preferred_job_titles = settings.preferred_job_titles
    current_user.preferred_locations = settings.preferred_locations
    current_user.excluded_companies = settings.excluded_companies
    current_user.salary_min = settings.salary_min
    current_user.salary_max = settings.salary_max
    current_user.employment_type = settings.employment_types
    current_user.remote_preference = settings.remote_preference
    
    db.commit()
    
    return {"message": "Auto-application settings updated successfully"}


@router.post("/automation/test-run")
async def test_auto_application(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(5, description="Maximum number of jobs to apply to in test run")
):
    """
    Run a test of the auto-application system.
    """
    if not current_user.auto_apply_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-application is not enabled. Please configure settings first."
        )
    
    # Add test run task to background
    background_tasks.add_task(
        _run_auto_application_test,
        current_user.id,
        limit,
        db
    )
    
    return {
        "message": "Auto-application test run initiated",
        "max_applications": limit,
        "note": "This is a test run. Review results before enabling full automation."
    }


async def _run_auto_application_test(user_id: int, limit: int, db: Session):
    """
    Background task to test auto-application system.
    """
    application_service = ApplicationService(db)
    
    # Run auto-application logic
    results = await application_service.run_auto_application(
        user_id=user_id,
        max_applications=limit,
        test_mode=True
    )
    
    # Send test results notification
    notification_service = NotificationService()
    await notification_service.send_auto_application_test_results(
        user_id=user_id,
        results=results
    )


async def _send_application_notification(application_id: int, message: str):
    """
    Background task to send application-related notifications.
    """
    notification_service = NotificationService()
    await notification_service.send_application_update(application_id, message)


def _calculate_average_response_time(applications: List[Application]) -> float:
    """
    Calculate average response time for applications.
    """
    response_times = []
    
    for app in applications:
        if app.status not in ["pending", "applied"] and app.updated_at:
            response_time = (app.updated_at - app.created_at).days
            response_times.append(response_time)
    
    return sum(response_times) / len(response_times) if response_times else 0.0