from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.core.security import get_current_active_user, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    UserResponse, 
    UserUpdate, 
    UserProfile, 
    UserPreferences,
    ChangePassword,
    UserSearchFilters
)

router = APIRouter()


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get current user's detailed profile information.
    """
    return UserProfile.from_orm(current_user)


@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    """
    # Update user fields
    for field, value in profile_data.dict(exclude_unset=True).items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserProfile.from_orm(current_user)


@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user: User = Depends(get_current_active_user)):
    """
    Get current user's application preferences.
    """
    return UserPreferences(
        preferred_job_titles=current_user.preferred_job_titles or [],
        preferred_locations=current_user.preferred_locations or [],
        preferred_industries=current_user.preferred_industries or [],
        salary_min=current_user.salary_min,
        salary_max=current_user.salary_max,
        remote_preference=current_user.remote_preference,
        employment_type=current_user.employment_type,
        auto_apply_enabled=current_user.auto_apply_enabled,
        max_applications_per_day=current_user.max_applications_per_day,
        notification_settings=current_user.notification_settings or {}
    )


@router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's application preferences.
    """
    # Update preference fields
    current_user.preferred_job_titles = preferences.preferred_job_titles
    current_user.preferred_locations = preferences.preferred_locations
    current_user.preferred_industries = preferences.preferred_industries
    current_user.salary_min = preferences.salary_min
    current_user.salary_max = preferences.salary_max
    current_user.remote_preference = preferences.remote_preference
    current_user.employment_type = preferences.employment_type
    current_user.auto_apply_enabled = preferences.auto_apply_enabled
    current_user.max_applications_per_day = preferences.max_applications_per_day
    current_user.notification_settings = preferences.notification_settings
    
    db.commit()
    db.refresh(current_user)
    
    return UserPreferences.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete current user's account (soft delete by deactivating).
    """
    current_user.is_active = False
    current_user.deleted_at = db.execute("SELECT NOW()").scalar()
    db.commit()
    
    return {"message": "Account deactivated successfully"}


@router.get("/stats")
async def get_user_stats(current_user: User = Depends(get_current_active_user)):
    """
    Get user statistics (applications, success rate, etc.).
    """
    # This would typically involve complex queries across multiple tables
    # For now, returning basic stats structure
    return {
        "total_applications": len(current_user.applications) if current_user.applications else 0,
        "active_applications": len([app for app in current_user.applications if app.status == "pending"]) if current_user.applications else 0,
        "interviews_scheduled": len([app for app in current_user.applications if app.status == "interview"]) if current_user.applications else 0,
        "offers_received": len([app for app in current_user.applications if app.status == "offer"]) if current_user.applications else 0,
        "applications_this_week": 0,  # Would calculate based on created_at
        "applications_this_month": 0,  # Would calculate based on created_at
        "success_rate": 0.0,  # Would calculate percentage
        "average_response_time": 0,  # Would calculate in days
        "top_job_sources": [],  # Would get from applications
        "preferred_industries": current_user.preferred_industries or []
    }


@router.get("/activity")
async def get_user_activity(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(20, description="Number of activities to return"),
    offset: int = Query(0, description="Number of activities to skip")
):
    """
    Get user's recent activity feed.
    """
    # This would typically query an activity/audit log table
    # For now, returning a basic structure
    activities = []
    
    # Add recent applications as activities
    if current_user.applications:
        for app in current_user.applications[-limit:]:
            activities.append({
                "id": app.id,
                "type": "application_submitted",
                "description": f"Applied to {app.job_title} at {app.company_name}",
                "timestamp": app.created_at,
                "metadata": {
                    "job_id": app.job_id,
                    "company": app.company_name,
                    "status": app.status
                }
            })
    
    return {
        "activities": activities[offset:offset + limit],
        "total": len(activities),
        "has_more": len(activities) > offset + limit
    }


@router.get("/search", response_model=List[UserResponse])
async def search_users(
    filters: UserSearchFilters = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, description="Maximum number of users to return"),
    offset: int = Query(0, description="Number of users to skip")
):
    """
    Search users (admin functionality or for networking features).
    Note: This might be restricted to admin users in production.
    """
    query = db.query(User)
    
    # Apply filters
    if filters.email:
        query = query.filter(User.email.ilike(f"%{filters.email}%"))
    
    if filters.username:
        query = query.filter(User.username.ilike(f"%{filters.username}%"))
    
    if filters.full_name:
        query = query.filter(User.full_name.ilike(f"%{filters.full_name}%"))
    
    if filters.is_active is not None:
        query = query.filter(User.is_active == filters.is_active)
    
    if filters.created_after:
        query = query.filter(User.created_at >= filters.created_after)
    
    if filters.created_before:
        query = query.filter(User.created_at <= filters.created_before)
    
    # Execute query with pagination
    users = query.offset(offset).limit(limit).all()
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user profile by ID (admin functionality or for networking).
    """
    # Check if current user can access other user profiles
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user's profile"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserProfile.from_orm(user)


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user active status (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify user status"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    
    return {"message": f"User status updated to {'active' if is_active else 'inactive'}"}


@router.get("/{user_id}/applications-summary")
async def get_user_applications_summary(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of user's applications (for admin dashboard).
    """
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user's application data"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get application statistics
    applications = user.applications or []
    
    summary = {
        "user_id": user_id,
        "total_applications": len(applications),
        "status_breakdown": {},
        "recent_activity": len([app for app in applications if app.created_at.date() == db.execute("SELECT CURRENT_DATE").scalar()]),
        "success_metrics": {
            "response_rate": 0.0,
            "interview_rate": 0.0,
            "offer_rate": 0.0
        }
    }
    
    # Calculate status breakdown
    for app in applications:
        status = app.status
        summary["status_breakdown"][status] = summary["status_breakdown"].get(status, 0) + 1
    
    return summary