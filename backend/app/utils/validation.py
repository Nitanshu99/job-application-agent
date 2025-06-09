"""Input validation utilities."""
from typing import Dict, Any

def validate_user_data(user_profile: Dict[str, Any]) -> bool:
    """Validate user profile data."""
    required_fields = ['id', 'email']
    for field in required_fields:
        if field not in user_profile:
            raise ValueError(f"Missing required field: {field}")
    return True

def validate_application_data(app_data: Dict[str, Any]) -> bool:
    """Validate application data."""
    required_fields = ['user_id', 'job_id']
    for field in required_fields:
        if field not in app_data:
            raise ValueError(f"Missing required field: {field}")
    return True

def validate_job_data(job_details: Dict[str, Any]) -> bool:
    """Validate job details data."""
    required_fields = ['id', 'title', 'company']
    for field in required_fields:
        if field not in job_details:
            raise ValueError(f"Missing required field: {field}")
    return True
