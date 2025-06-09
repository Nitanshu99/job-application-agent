from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.job import Job
from app.schemas.job import (
    JobResponse, 
    JobCreate, 
    JobUpdate, 
    JobSearchFilters,
    JobSearchRequest,
    JobMatchingResult,
    ScrapingRequest,
    JobAnalytics
)
from app.services.job_service import JobService
from app.services.scrapers.scraper_factory import ScraperFactory
from app.services.llm.model_manager import ModelManager

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, description="Maximum number of jobs to return"),
    offset: int = Query(0, description="Number of jobs to skip"),
    title: Optional[str] = Query(None, description="Filter by job title"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    remote: Optional[bool] = Query(None, description="Filter remote jobs"),
    salary_min: Optional[int] = Query(None, description="Minimum salary filter"),
    employment_type: Optional[str] = Query(None, description="Employment type filter"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    Get paginated list of jobs with optional filtering and sorting.
    """
    query = db.query(Job)
    
    # Apply filters
    if title:
        query = query.filter(Job.title.ilike(f"%{title}%"))
    
    if company:
        query = query.filter(Job.company_name.ilike(f"%{company}%"))
    
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    
    if remote is not None:
        query = query.filter(Job.is_remote == remote)
    
    if salary_min:
        query = query.filter(Job.salary_min >= salary_min)
    
    if employment_type:
        query = query.filter(Job.employment_type == employment_type)
    
    if industry:
        query = query.filter(Job.industry.ilike(f"%{industry}%"))
    
    # Apply sorting
    if hasattr(Job, sort_by):
        sort_column = getattr(Job, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
    
    # Execute query with pagination
    jobs = query.offset(offset).limit(limit).all()
    
    return [JobResponse.from_orm(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific job by ID.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse.from_orm(job)


@router.post("/search", response_model=List[JobMatchingResult])
async def search_jobs(
    search_request: JobSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Advanced job search with AI-powered matching and scoring.
    """
    job_service = JobService(db)
    
    # Perform search with AI matching
    matching_results = await job_service.search_and_match_jobs(
        user=current_user,
        search_criteria=search_request,
        limit=search_request.limit or 50
    )
    
    return matching_results


@router.post("/scrape")
async def scrape_jobs(
    scraping_request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Initiate job scraping from specified sources.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to initiate job scraping"
        )
    
    # Add scraping task to background
    background_tasks.add_task(
        _scrape_jobs_background,
        scraping_request,
        db
    )
    
    return {
        "message": "Job scraping initiated",
        "sources": scraping_request.sources,
        "search_terms": scraping_request.search_terms
    }


async def _scrape_jobs_background(scraping_request: ScrapingRequest, db: Session):
    """
    Background task to scrape jobs from various sources.
    """
    scraper_factory = ScraperFactory()
    
    for source in scraping_request.sources:
        try:
            scraper = scraper_factory.get_scraper(source)
            
            for search_term in scraping_request.search_terms:
                jobs_data = await scraper.scrape_jobs(
                    query=search_term,
                    location=scraping_request.location,
                    limit=scraping_request.limit_per_source or 100
                )
                
                # Save scraped jobs to database
                for job_data in jobs_data:
                    # Check if job already exists
                    existing_job = db.query(Job).filter(
                        and_(
                            Job.external_id == job_data.get("external_id"),
                            Job.source == source
                        )
                    ).first()
                    
                    if not existing_job:
                        job = Job(
                            title=job_data.get("title"),
                            company_name=job_data.get("company"),
                            location=job_data.get("location"),
                            description=job_data.get("description"),
                            external_url=job_data.get("url"),
                            external_id=job_data.get("external_id"),
                            source=source,
                            salary_min=job_data.get("salary_min"),
                            salary_max=job_data.get("salary_max"),
                            employment_type=job_data.get("employment_type"),
                            is_remote=job_data.get("is_remote", False),
                            posted_date=job_data.get("posted_date")
                        )
                        db.add(job)
                
                db.commit()
                
        except Exception as e:
            print(f"Error scraping from {source}: {str(e)}")
            continue


@router.get("/recommendations/{user_id}", response_model=List[JobMatchingResult])
async def get_job_recommendations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(20, description="Number of recommendations to return")
):
    """
    Get personalized job recommendations for a user.
    """
    # Check permissions
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user's recommendations"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    job_service = JobService(db)
    recommendations = await job_service.get_personalized_recommendations(
        user=target_user,
        limit=limit
    )
    
    return recommendations


@router.post("/analyze")
async def analyze_job_posting(
    job_url: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze a job posting from URL and extract structured information.
    """
    job_service = JobService(db)
    
    try:
        analysis = await job_service.analyze_job_posting(job_url)
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to analyze job posting: {str(e)}"
        )


@router.get("/analytics/overview", response_model=JobAnalytics)
async def get_job_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get job market analytics and trends.
    """
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get jobs from the specified time period
    recent_jobs = db.query(Job).filter(Job.created_at >= cutoff_date).all()
    
    # Calculate analytics
    total_jobs = len(recent_jobs)
    
    # Company distribution
    company_counts = {}
    location_counts = {}
    industry_counts = {}
    employment_type_counts = {}
    
    salary_data = []
    
    for job in recent_jobs:
        # Company distribution
        company = job.company_name
        company_counts[company] = company_counts.get(company, 0) + 1
        
        # Location distribution
        location = job.location or "Remote"
        location_counts[location] = location_counts.get(location, 0) + 1
        
        # Industry distribution
        industry = job.industry or "Unknown"
        industry_counts[industry] = industry_counts.get(industry, 0) + 1
        
        # Employment type distribution
        emp_type = job.employment_type or "Unknown"
        employment_type_counts[emp_type] = employment_type_counts.get(emp_type, 0) + 1
        
        # Salary data
        if job.salary_min and job.salary_max:
            salary_data.append({
                "min": job.salary_min,
                "max": job.salary_max,
                "avg": (job.salary_min + job.salary_max) / 2
            })
    
    # Calculate salary statistics
    salary_stats = {}
    if salary_data:
        avg_salaries = [s["avg"] for s in salary_data]
        salary_stats = {
            "average": sum(avg_salaries) / len(avg_salaries),
            "median": sorted(avg_salaries)[len(avg_salaries) // 2],
            "min": min(s["min"] for s in salary_data),
            "max": max(s["max"] for s in salary_data)
        }
    
    return JobAnalytics(
        total_jobs=total_jobs,
        period_days=days,
        top_companies=dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        top_locations=dict(sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        industries=dict(sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)),
        employment_types=employment_type_counts,
        salary_statistics=salary_stats,
        trends={
            "jobs_per_day": total_jobs / max(days, 1),
            "remote_percentage": (location_counts.get("Remote", 0) / total_jobs * 100) if total_jobs > 0 else 0
        }
    )


@router.post("/bulk-import")
async def bulk_import_jobs(
    jobs_data: List[JobCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk import jobs from external data source.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to bulk import jobs"
        )
    
    imported_count = 0
    skipped_count = 0
    
    for job_data in jobs_data:
        try:
            # Check if job already exists
            existing_job = db.query(Job).filter(
                and_(
                    Job.external_id == job_data.external_id,
                    Job.source == job_data.source
                )
            ).first()
            
            if existing_job:
                skipped_count += 1
                continue
            
            # Create new job
            job = Job(**job_data.dict())
            db.add(job)
            imported_count += 1
            
        except Exception as e:
            print(f"Error importing job: {str(e)}")
            skipped_count += 1
            continue
    
    db.commit()
    
    return {
        "message": "Bulk import completed",
        "imported": imported_count,
        "skipped": skipped_count,
        "total_processed": len(jobs_data)
    }


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a job (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete jobs"
        )
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully"}


@router.get("/sources/supported")
async def get_supported_sources(current_user: User = Depends(get_current_active_user)):
    """
    Get list of supported job sources for scraping.
    """
    return {
        "sources": [
            {
                "name": "linkedin",
                "display_name": "LinkedIn Jobs",
                "supported_features": ["search", "location_filter", "date_filter"]
            },
            {
                "name": "indeed",
                "display_name": "Indeed",
                "supported_features": ["search", "location_filter", "salary_filter"]
            },
            {
                "name": "custom",
                "display_name": "Custom Portal",
                "supported_features": ["configurable"]
            }
        ]
    }


@router.post("/{job_id}/bookmark")
async def bookmark_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bookmark a job for later reference.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Add bookmark logic (would typically involve a user_bookmarks table)
    # For now, return success message
    return {"message": "Job bookmarked successfully"}


@router.delete("/{job_id}/bookmark")
async def remove_bookmark(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove bookmark from a job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Remove bookmark logic
    return {"message": "Bookmark removed successfully"}