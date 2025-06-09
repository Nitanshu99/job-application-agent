"""
Application manager service for job automation system.

This service handles application history tracking, duplicate prevention,
and analytics for job applications. It provides comprehensive application
management with intelligent duplicate detection and performance tracking.

Features:
- Application history tracking and management
- Intelligent duplicate detection with similarity scoring
- Application analytics and success metrics
- Status tracking and update management
- Performance insights and recommendations
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.application_history import ApplicationHistory
from app.utils.text_processing import similarity_score, clean_text
from app.utils.validation import sanitize_input

logger = logging.getLogger(__name__)


class ApplicationManager:
    """Service for managing job application history and duplicate prevention."""
    
    def __init__(self):
        self.duplicate_threshold = float(settings.DUPLICATE_SIMILARITY_THRESHOLD or 0.85)
        self.history_retention_days = int(settings.APPLICATION_HISTORY_RETENTION_DAYS or 365)
        
    async def check_duplicate(
        self,
        user_id: int,
        job_url: str,
        company: str,
        job_title: str,
        db: Session = None
    ) -> bool:
        """
        Check if a similar application already exists for this user.
        
        Args:
            user_id: ID of the user
            job_url: URL of the job posting
            company: Company name
            job_title: Job title
            db: Database session
            
        Returns:
            True if duplicate found, False otherwise
        """
        try:
            if not db:
                db = next(get_db())
            
            # Generate URL hash for exact match
            url_hash = self._generate_url_hash(job_url)
            
            # Check for exact URL match first
            exact_match = db.query(ApplicationHistory).filter(
                ApplicationHistory.user_id == user_id,
                ApplicationHistory.job_url_hash == url_hash
            ).first()
            
            if exact_match:
                logger.info(f"Exact duplicate found for user {user_id}: {job_url}")
                return True
            
            # Check for similar applications using fuzzy matching
            recent_applications = db.query(ApplicationHistory).filter(
                ApplicationHistory.user_id == user_id,
                ApplicationHistory.applied_at >= datetime.utcnow() - timedelta(days=90)
            ).all()
            
            for app_history in recent_applications:
                # Calculate similarity scores
                company_similarity = similarity_score(
                    company.lower().strip(),
                    app_history.company.lower().strip()
                )
                
                title_similarity = similarity_score(
                    job_title.lower().strip(),
                    app_history.job_title.lower().strip()
                )
                
                # Combined similarity score with weights
                combined_similarity = (company_similarity * 0.4) + (title_similarity * 0.6)
                
                if combined_similarity >= self.duplicate_threshold:
                    logger.info(
                        f"Similar application found for user {user_id}: "
                        f"Company similarity: {company_similarity:.2f}, "
                        f"Title similarity: {title_similarity:.2f}, "
                        f"Combined: {combined_similarity:.2f}"
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Duplicate check failed for user {user_id}: {str(e)}")
            # In case of error, err on the side of caution and allow application
            return False
    
    async def record_application(
        self,
        user_id: int,
        job_id: int,
        application_id: int,
        job_url: str,
        company: str,
        job_title: str,
        status: str = "submitted",
        db: Session = None
    ) -> ApplicationHistory:
        """
        Record a new application in the history tracking system.
        
        Args:
            user_id: ID of the user
            job_id: ID of the job
            application_id: ID of the application
            job_url: URL of the job posting
            company: Company name
            job_title: Job title
            status: Application status
            db: Database session
            
        Returns:
            Created ApplicationHistory record
        """
        try:
            if not db:
                db = next(get_db())
            
            # Generate URL hash
            url_hash = self._generate_url_hash(job_url)
            
            # Create application history record
            history_data = {
                "user_id": user_id,
                "job_id": job_id,
                "application_id": application_id,
                "job_url": sanitize_input(job_url),
                "job_url_hash": url_hash,
                "company": sanitize_input(company),
                "job_title": sanitize_input(job_title),
                "status": status,
                "applied_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
                "metadata": {
                    "initial_status": status,
                    "created_by": "application_manager",
                    "duplicate_check_passed": True
                }
            }
            
            history_record = ApplicationHistory(**history_data)
            db.add(history_record)
            db.commit()
            db.refresh(history_record)
            
            logger.info(f"Application history recorded: {history_record.id}")
            
            return history_record
            
        except Exception as e:
            logger.error(f"Failed to record application history: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to record application: {str(e)}")
    
    async def update_application_status(
        self,
        application_id: int,
        user_id: int,
        new_status: str,
        notes: Optional[str] = None,
        response_date: Optional[datetime] = None,
        db: Session = None
    ) -> bool:
        """
        Update application status in both Application and ApplicationHistory.
        
        Args:
            application_id: ID of the application
            user_id: ID of the user (for security)
            new_status: New status to set
            notes: Optional notes about the status change
            response_date: Optional date of the status change
            db: Database session
            
        Returns:
            True if update was successful
        """
        try:
            if not db:
                db = next(get_db())
            
            # Update main application record
            application = db.query(Application).filter(
                Application.id == application_id,
                Application.user_id == user_id
            ).first()
            
            if not application:
                logger.warning(f"Application {application_id} not found for user {user_id}")
                return False
            
            old_status = application.status
            application.status = new_status
            application.updated_at = datetime.utcnow()
            
            if response_date:
                application.response_date = response_date
            
            # Update application history
            history_record = db.query(ApplicationHistory).filter(
                ApplicationHistory.application_id == application_id,
                ApplicationHistory.user_id == user_id
            ).first()
            
            if history_record:
                history_record.status = new_status
                history_record.last_updated = datetime.utcnow()
                
                # Update status history in metadata
                if not history_record.metadata:
                    history_record.metadata = {}
                
                if "status_history" not in history_record.metadata:
                    history_record.metadata["status_history"] = []
                
                history_record.metadata["status_history"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "old_status": old_status,
                    "new_status": new_status,
                    "notes": notes,
                    "response_date": response_date.isoformat() if response_date else None
                })
            
            db.commit()
            
            logger.info(f"Application {application_id} status updated from {old_status} to {new_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update application status: {str(e)}")
            if db:
                db.rollback()
            return False
    
    async def get_application_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        company_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        db: Session = None
    ) -> List[ApplicationHistory]:
        """
        Get application history for a user with optional filters.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of records to return
            offset: Number of records to skip
            status_filter: Optional status filter
            company_filter: Optional company name filter
            date_from: Optional start date filter
            date_to: Optional end date filter
            db: Database session
            
        Returns:
            List of ApplicationHistory records
        """
        if not db:
            db = next(get_db())
        
        query = db.query(ApplicationHistory).filter(ApplicationHistory.user_id == user_id)
        
        if status_filter:
            query = query.filter(ApplicationHistory.status == status_filter)
        
        if company_filter:
            query = query.filter(ApplicationHistory.company.ilike(f"%{company_filter}%"))
        
        if date_from:
            query = query.filter(ApplicationHistory.applied_at >= date_from)
        
        if date_to:
            query = query.filter(ApplicationHistory.applied_at <= date_to)
        
        return query.order_by(desc(ApplicationHistory.applied_at)).offset(offset).limit(limit).all()
    
    async def get_application_statistics(
        self,
        user_id: int,
        time_period_days: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive application statistics for a user.
        
        Args:
            user_id: ID of the user
            time_period_days: Number of days to analyze
            db: Database session
            
        Returns:
            Dictionary containing various statistics
        """
        try:
            if not db:
                db = next(get_db())
            
            # Date range for analysis
            start_date = datetime.utcnow() - timedelta(days=time_period_days)
            
            # Get all applications in the time period
            applications = db.query(ApplicationHistory).filter(
                ApplicationHistory.user_id == user_id,
                ApplicationHistory.applied_at >= start_date
            ).all()
            
            # Get all-time applications for comparison
            all_time_applications = db.query(ApplicationHistory).filter(
                ApplicationHistory.user_id == user_id
            ).all()
            
            # Calculate statistics
            stats = {
                "time_period": {
                    "days": time_period_days,
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "application_count": {
                    "period": len(applications),
                    "all_time": len(all_time_applications),
                    "average_per_day": len(applications) / max(time_period_days, 1)
                },
                "status_breakdown": self._calculate_status_breakdown(applications),
                "response_rates": await self._calculate_response_rates(applications),
                "company_analysis": self._analyze_companies(applications),
                "timeline_analysis": self._analyze_timeline(applications),
                "success_metrics": await self._calculate_success_metrics(all_time_applications),
                "recommendations": await self._generate_recommendations(applications, all_time_applications)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate application statistics: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Statistics calculation failed: {str(e)}")
    
    async def get_duplicate_analysis(
        self,
        user_id: int,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Analyze potential duplicates and near-duplicates in application history.
        
        Args:
            user_id: ID of the user
            db: Database session
            
        Returns:
            Dictionary containing duplicate analysis
        """
        try:
            if not db:
                db = next(get_db())
            
            applications = db.query(ApplicationHistory).filter(
                ApplicationHistory.user_id == user_id
            ).order_by(ApplicationHistory.applied_at).all()
            
            duplicates = []
            near_duplicates = []
            
            for i, app1 in enumerate(applications):
                for app2 in applications[i+1:]:
                    # Calculate similarity
                    company_sim = similarity_score(app1.company.lower(), app2.company.lower())
                    title_sim = similarity_score(app1.job_title.lower(), app2.job_title.lower())
                    combined_sim = (company_sim * 0.4) + (title_sim * 0.6)
                    
                    if combined_sim >= self.duplicate_threshold:
                        duplicates.append({
                            "application_1": {
                                "id": app1.id,
                                "company": app1.company,
                                "title": app1.job_title,
                                "applied_at": app1.applied_at.isoformat()
                            },
                            "application_2": {
                                "id": app2.id,
                                "company": app2.company,
                                "title": app2.job_title,
                                "applied_at": app2.applied_at.isoformat()
                            },
                            "similarity_score": combined_sim,
                            "company_similarity": company_sim,
                            "title_similarity": title_sim
                        })
                    elif combined_sim >= (self.duplicate_threshold - 0.1):
                        near_duplicates.append({
                            "application_1": {
                                "id": app1.id,
                                "company": app1.company,
                                "title": app1.job_title,
                                "applied_at": app1.applied_at.isoformat()
                            },
                            "application_2": {
                                "id": app2.id,
                                "company": app2.company,
                                "title": app2.job_title,
                                "applied_at": app2.applied_at.isoformat()
                            },
                            "similarity_score": combined_sim
                        })
            
            return {
                "total_applications": len(applications),
                "exact_duplicates": len(duplicates),
                "near_duplicates": len(near_duplicates),
                "duplicate_details": duplicates,
                "near_duplicate_details": near_duplicates,
                "duplicate_threshold": self.duplicate_threshold,
                "analysis_metadata": {
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "comparison_count": len(applications) * (len(applications) - 1) // 2
                }
            }
            
        except Exception as e:
            logger.error(f"Duplicate analysis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Duplicate analysis failed: {str(e)}")
    
    async def cleanup_old_records(
        self,
        user_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, int]:
        """
        Clean up old application history records beyond retention period.
        
        Args:
            user_id: Optional specific user ID, if None cleans all users
            db: Database session
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            if not db:
                db = next(get_db())
            
            cutoff_date = datetime.utcnow() - timedelta(days=self.history_retention_days)
            
            query = db.query(ApplicationHistory).filter(
                ApplicationHistory.applied_at < cutoff_date
            )
            
            if user_id:
                query = query.filter(ApplicationHistory.user_id == user_id)
            
            old_records = query.all()
            records_to_delete = len(old_records)
            
            # Delete old records
            query.delete(synchronize_session=False)
            db.commit()
            
            logger.info(f"Cleaned up {records_to_delete} old application history records")
            
            return {
                "records_deleted": records_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.history_retention_days
            }
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            if db:
                db.rollback()
            raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
    
    async def get_company_application_history(
        self,
        user_id: int,
        company: str,
        db: Session = None
    ) -> List[ApplicationHistory]:
        """Get all applications to a specific company for a user."""
        if not db:
            db = next(get_db())
        
        return db.query(ApplicationHistory).filter(
            ApplicationHistory.user_id == user_id,
            ApplicationHistory.company.ilike(f"%{company}%")
        ).order_by(desc(ApplicationHistory.applied_at)).all()
    
    # Private helper methods
    
    def _generate_url_hash(self, url: str) -> str:
        """Generate a hash for URL-based duplicate detection."""
        # Normalize URL for consistent hashing
        normalized_url = url.lower().strip().rstrip('/')
        return hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
    
    def _calculate_status_breakdown(self, applications: List[ApplicationHistory]) -> Dict[str, Any]:
        """Calculate breakdown of application statuses."""
        status_counts = defaultdict(int)
        
        for app in applications:
            status_counts[app.status] += 1
        
        total = len(applications)
        
        return {
            "counts": dict(status_counts),
            "percentages": {
                status: (count / total * 100) if total > 0 else 0
                for status, count in status_counts.items()
            },
            "total": total
        }
    
    async def _calculate_response_rates(self, applications: List[ApplicationHistory]) -> Dict[str, Any]:
        """Calculate various response rates."""
        total_apps = len(applications)
        
        if total_apps == 0:
            return {"response_rate": 0, "interview_rate": 0, "offer_rate": 0}
        
        responses = len([app for app in applications if app.status not in ["submitted", "pending"]])
        interviews = len([app for app in applications if "interview" in app.status.lower()])
        offers = len([app for app in applications if "offer" in app.status.lower()])
        rejections = len([app for app in applications if "reject" in app.status.lower()])
        
        return {
            "response_rate": (responses / total_apps) * 100,
            "interview_rate": (interviews / total_apps) * 100,
            "offer_rate": (offers / total_apps) * 100,
            "rejection_rate": (rejections / total_apps) * 100,
            "pending_rate": ((total_apps - responses) / total_apps) * 100
        }
    
    def _analyze_companies(self, applications: List[ApplicationHistory]) -> Dict[str, Any]:
        """Analyze company-related statistics."""
        company_counts = defaultdict(int)
        
        for app in applications:
            company_counts[app.company] += 1
        
        # Sort companies by application count
        sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "unique_companies": len(company_counts),
            "most_applied": sorted_companies[:10],
            "average_applications_per_company": sum(company_counts.values()) / max(len(company_counts), 1),
            "companies_with_multiple_applications": len([c for c in company_counts.values() if c > 1])
        }
    
    def _analyze_timeline(self, applications: List[ApplicationHistory]) -> Dict[str, Any]:
        """Analyze application timeline patterns."""
        if not applications:
            return {"pattern": "no_data"}
        
        # Sort by date
        sorted_apps = sorted(applications, key=lambda x: x.applied_at)
        
        # Calculate time gaps between applications
        gaps = []
        for i in range(1, len(sorted_apps)):
            gap = (sorted_apps[i].applied_at - sorted_apps[i-1].applied_at).days
            gaps.append(gap)
        
        # Analyze weekly patterns
        day_counts = defaultdict(int)
        for app in applications:
            day_counts[app.applied_at.strftime("%A")] += 1
        
        return {
            "first_application": sorted_apps[0].applied_at.isoformat() if sorted_apps else None,
            "last_application": sorted_apps[-1].applied_at.isoformat() if sorted_apps else None,
            "average_gap_days": sum(gaps) / max(len(gaps), 1) if gaps else 0,
            "most_active_day": max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else None,
            "daily_distribution": dict(day_counts),
            "application_frequency": "consistent" if gaps and max(gaps) - min(gaps) < 7 else "irregular"
        }
    
    async def _calculate_success_metrics(self, all_applications: List[ApplicationHistory]) -> Dict[str, Any]:
        """Calculate long-term success metrics."""
        if not all_applications:
            return {"overall_success_rate": 0, "average_response_time": 0}
        
        successful_outcomes = ["offer", "hired", "accepted"]
        positive_responses = ["interview", "phone_screen", "assessment"] + successful_outcomes
        
        success_count = len([
            app for app in all_applications 
            if any(outcome in app.status.lower() for outcome in successful_outcomes)
        ])
        
        positive_count = len([
            app for app in all_applications 
            if any(response in app.status.lower() for response in positive_responses)
        ])
        
        return {
            "overall_success_rate": (success_count / len(all_applications)) * 100,
            "positive_response_rate": (positive_count / len(all_applications)) * 100,
            "total_applications": len(all_applications),
            "successful_applications": success_count,
            "positive_responses": positive_count
        }
    
    async def _generate_recommendations(
        self,
        recent_applications: List[ApplicationHistory],
        all_applications: List[ApplicationHistory]
    ) -> List[str]:
        """Generate recommendations based on application patterns."""
        recommendations = []
        
        if not recent_applications:
            recommendations.append("Start applying to more positions to increase your chances")
            return recommendations
        
        # Analyze response rates
        response_rates = await self._calculate_response_rates(recent_applications)
        
        if response_rates["response_rate"] < 20:
            recommendations.append("Consider tailoring your resume and cover letter more specifically to each job")
        
        if response_rates["interview_rate"] < 10:
            recommendations.append("Focus on applying to positions that better match your experience level")
        
        # Analyze application frequency
        if len(recent_applications) < 5:
            recommendations.append("Increase your application volume to improve your chances")
        
        # Analyze company diversity
        company_analysis = self._analyze_companies(recent_applications)
        if company_analysis["companies_with_multiple_applications"] > len(recent_applications) * 0.3:
            recommendations.append("Diversify your applications across more companies")
        
        return recommendations