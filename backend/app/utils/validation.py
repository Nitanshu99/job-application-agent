"""
Validation utilities for job automation system.

Provides functions for validating various types of input data including
emails, phone numbers, URLs, passwords, and business data.
"""

import re
import html
import urllib.parse
from typing import Dict, Any, List, Optional, Union
from email_validator import validate_email as email_validate, EmailNotValidError
import phonenumbers
from phonenumbers import NumberParseException


def validate_email(email: str) -> bool:
    """
    Validate email address format and deliverability.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    try:
        # Use email-validator library for comprehensive validation
        valid = email_validate(email)
        return True
        
    except EmailNotValidError:
        return False


def validate_phone(phone: str, region: str = "US") -> bool:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        region: Default region code (ISO 3166-1 alpha-2)
        
    Returns:
        True if phone number is valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    try:
        # Parse phone number
        parsed_number = phonenumbers.parse(phone, region)
        
        # Check if valid
        return phonenumbers.is_valid_number(parsed_number)
        
    except NumberParseException:
        return False


def validate_url(url: str, allowed_schemes: List[str] = None) -> bool:
    """
    Validate URL format and scheme.
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        
    Returns:
        True if URL is valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    try:
        parsed = urllib.parse.urlparse(url)
        
        # Check scheme
        if parsed.scheme.lower() not in allowed_schemes:
            return False
        
        # Check netloc (domain)
        if not parsed.netloc:
            return False
        
        # Basic domain validation
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        
        # Remove port if present
        domain = parsed.netloc.split(':')[0]
        
        return re.match(domain_pattern, domain) is not None
        
    except Exception:
        return False


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength and return detailed feedback.
    
    Args:
        password: Password to validate
        
    Returns:
        Dictionary with validation results and feedback
    """
    if not password or not isinstance(password, str):
        return {
            "is_valid": False,
            "score": 0,
            "errors": ["Password is required"]
        }
    
    errors = []
    score = 0
    
    # Check length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    else:
        score += 1
        
        # Bonus for longer passwords
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
    
    # Check for uppercase letters
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    else:
        score += 1
    
    # Check for lowercase letters
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    else:
        score += 1
    
    # Check for numbers
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    else:
        score += 1
    
    # Check for special characters
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    else:
        score += 1
    
    # Check for common patterns
    common_patterns = [
        r'123456',
        r'password',
        r'qwerty',
        r'abc123',
        r'admin'
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            errors.append("Password contains common patterns")
            score -= 1
            break
    
    # Check for repeated characters
    if re.search(r'(.)\1{2,}', password):
        errors.append("Password contains too many repeated characters")
        score -= 1
    
    # Calculate final score (0-5 scale)
    score = max(0, min(5, score))
    
    # Determine strength level
    if score >= 4:
        strength = "Strong"
    elif score >= 3:
        strength = "Good"
    elif score >= 2:
        strength = "Fair"
    else:
        strength = "Weak"
    
    return {
        "is_valid": len(errors) == 0,
        "score": score,
        "strength": strength,
        "errors": errors
    }


def sanitize_input(input_text: str, max_length: int = None) -> str:
    """
    Sanitize user input by escaping HTML and removing dangerous content.
    
    Args:
        input_text: Text to sanitize
        max_length: Maximum allowed length (optional)
        
    Returns:
        Sanitized text
    """
    if not isinstance(input_text, str):
        return ""
    
    # Escape HTML entities
    sanitized = html.escape(input_text)
    
    # Remove potentially dangerous patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>.*?</iframe>',  # IFrames
        r'<object[^>]*>.*?</object>',  # Objects
        r'<embed[^>]*>.*?</embed>',  # Embeds
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    # Truncate if max_length specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def validate_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate job posting data.
    
    Args:
        job_data: Dictionary containing job information
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ['title', 'company', 'description']
    
    for field in required_fields:
        if field not in job_data or not job_data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate specific fields
    if 'title' in job_data:
        title = job_data['title']
        if len(title) < 5:
            errors.append("Job title too short (minimum 5 characters)")
        elif len(title) > 200:
            errors.append("Job title too long (maximum 200 characters)")
    
    if 'company' in job_data:
        company = job_data['company']
        if len(company) < 2:
            errors.append("Company name too short (minimum 2 characters)")
        elif len(company) > 100:
            errors.append("Company name too long (maximum 100 characters)")
    
    if 'description' in job_data:
        description = job_data['description']
        if len(description) < 50:
            warnings.append("Job description is quite short (recommended minimum 50 characters)")
        elif len(description) > 10000:
            errors.append("Job description too long (maximum 10,000 characters)")
    
    if 'salary_min' in job_data and 'salary_max' in job_data:
        try:
            salary_min = float(job_data['salary_min'])
            salary_max = float(job_data['salary_max'])
            
            if salary_min < 0:
                errors.append("Minimum salary cannot be negative")
            if salary_max < 0:
                errors.append("Maximum salary cannot be negative")
            if salary_min > salary_max:
                errors.append("Minimum salary cannot be greater than maximum salary")
            if salary_min > 1000000:
                warnings.append("Salary seems unusually high")
                
        except (ValueError, TypeError):
            errors.append("Invalid salary values")
    
    if 'location' in job_data:
        location = job_data['location']
        if len(location) > 200:
            errors.append("Location too long (maximum 200 characters)")
    
    if 'requirements' in job_data:
        requirements = job_data['requirements']
        if isinstance(requirements, list):
            if len(requirements) > 50:
                warnings.append("Very long requirements list")
        elif isinstance(requirements, str):
            if len(requirements) > 5000:
                warnings.append("Requirements text is very long")
    
    if 'job_type' in job_data:
        valid_job_types = ['full-time', 'part-time', 'contract', 'temporary', 'internship', 'volunteer']
        if job_data['job_type'].lower() not in valid_job_types:
            warnings.append(f"Unusual job type: {job_data['job_type']}")
    
    if 'remote' in job_data:
        if not isinstance(job_data['remote'], bool):
            errors.append("Remote field must be boolean (true/false)")
    
    # Validate URL fields
    url_fields = ['company_website', 'application_url']
    for field in url_fields:
        if field in job_data and job_data[field]:
            if not validate_url(job_data[field]):
                errors.append(f"Invalid URL format for {field}")
    
    # Validate email fields
    if 'contact_email' in job_data and job_data['contact_email']:
        if not validate_email(job_data['contact_email']):
            errors.append("Invalid contact email format")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate user profile data.
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ['email', 'full_name']
    
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate email
    if 'email' in user_data and user_data['email']:
        if not validate_email(user_data['email']):
            errors.append("Invalid email format")
    
    # Validate full name
    if 'full_name' in user_data:
        full_name = user_data['full_name']
        if len(full_name) < 2:
            errors.append("Full name too short (minimum 2 characters)")
        elif len(full_name) > 100:
            errors.append("Full name too long (maximum 100 characters)")
        
        # Check for reasonable name format
        if not re.match(r'^[a-zA-Z\s\'-\.]+$', full_name):
            warnings.append("Name contains unusual characters")
    
    # Validate phone number
    if 'phone_number' in user_data and user_data['phone_number']:
        if not validate_phone(user_data['phone_number']):
            errors.append("Invalid phone number format")
    
    # Validate experience years
    if 'experience_years' in user_data:
        try:
            exp_years = int(user_data['experience_years'])
            if exp_years < 0:
                errors.append("Experience years cannot be negative")
            elif exp_years > 70:
                warnings.append("Experience years seems unusually high")
        except (ValueError, TypeError):
            errors.append("Invalid experience years value")
    
    # Validate skills
    if 'skills' in user_data:
        skills = user_data['skills']
        if isinstance(skills, list):
            if len(skills) > 100:
                warnings.append("Very long skills list")
            
            # Check each skill
            for skill in skills:
                if not isinstance(skill, str):
                    errors.append("All skills must be text")
                elif len(skill) > 50:
                    warnings.append(f"Skill name too long: {skill}")
        else:
            errors.append("Skills must be a list")
    
    # Validate location
    if 'location' in user_data:
        location = user_data['location']
        if len(location) > 200:
            errors.append("Location too long (maximum 200 characters)")
    
    # Validate education
    if 'education' in user_data:
        education = user_data['education']
        if isinstance(education, list):
            for edu in education:
                if not isinstance(edu, dict):
                    errors.append("Education entries must be objects")
                elif 'degree' not in edu or 'institution' not in edu:
                    warnings.append("Education entry missing degree or institution")
    
    # Validate work experience
    if 'work_experience' in user_data:
        work_exp = user_data['work_experience']
        if isinstance(work_exp, list):
            for exp in work_exp:
                if not isinstance(exp, dict):
                    errors.append("Work experience entries must be objects")
                elif 'company' not in exp or 'position' not in exp:
                    warnings.append("Work experience entry missing company or position")
    
    # Validate portfolio URLs
    if 'portfolio_urls' in user_data:
        urls = user_data['portfolio_urls']
        if isinstance(urls, list):
            for url in urls:
                if not validate_url(url):
                    errors.append(f"Invalid portfolio URL: {url}")
        else:
            errors.append("Portfolio URLs must be a list")
    
    # Validate social profiles
    if 'social_profiles' in user_data:
        profiles = user_data['social_profiles']
        if isinstance(profiles, dict):
            for platform, url in profiles.items():
                if url and not validate_url(url):
                    errors.append(f"Invalid {platform} profile URL")
        else:
            errors.append("Social profiles must be an object")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_file_upload(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate file upload data.
    
    Args:
        file_data: Dictionary containing file information
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    # Check required fields
    if 'filename' not in file_data:
        errors.append("Filename is required")
    
    if 'size' not in file_data:
        errors.append("File size is required")
    
    if 'content_type' not in file_data:
        errors.append("Content type is required")
    
    # Validate file size (10MB limit)
    if 'size' in file_data:
        try:
            file_size = int(file_data['size'])
            max_size = 10 * 1024 * 1024  # 10MB
            
            if file_size <= 0:
                errors.append("File size must be greater than 0")
            elif file_size > max_size:
                errors.append(f"File size exceeds limit ({max_size // (1024*1024)}MB)")
            elif file_size > 5 * 1024 * 1024:  # 5MB warning
                warnings.append("Large file size may slow down processing")
                
        except (ValueError, TypeError):
            errors.append("Invalid file size")
    
    # Validate filename
    if 'filename' in file_data:
        filename = file_data['filename']
        
        # Check for dangerous characters
        if re.search(r'[<>:"/\\|?*]', filename):
            errors.append("Filename contains invalid characters")
        
        # Check length
        if len(filename) > 255:
            errors.append("Filename too long (maximum 255 characters)")
        elif len(filename) < 1:
            errors.append("Filename cannot be empty")
        
        # Check for hidden files or system files
        if filename.startswith('.') or filename.startswith('~'):
            warnings.append("Hidden or temporary file detected")
    
    # Validate content type
    if 'content_type' in file_data:
        content_type = file_data['content_type']
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        
        if content_type not in allowed_types:
            errors.append(f"File type not allowed: {content_type}")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_search_query(query: str, max_length: int = 500) -> Dict[str, Any]:
    """
    Validate search query input.
    
    Args:
        query: Search query string
        max_length: Maximum allowed query length
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    if not query or not isinstance(query, str):
        errors.append("Search query is required")
        return {"is_valid": False, "errors": errors, "warnings": warnings}
    
    # Check length
    if len(query.strip()) < 2:
        errors.append("Search query too short (minimum 2 characters)")
    elif len(query) > max_length:
        errors.append(f"Search query too long (maximum {max_length} characters)")
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',
        r'eval\s*\(',
        r'document\.',
        r'window\.'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            errors.append("Search query contains potentially dangerous content")
            break
    
    # Check for extremely long words (potential attack)
    words = query.split()
    for word in words:
        if len(word) > 100:
            errors.append("Search query contains unusually long words")
            break
    
    # Check for repeated characters (potential spam)
    if re.search(r'(.)\1{10,}', query):
        warnings.append("Search query contains many repeated characters")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "sanitized_query": sanitize_input(query, max_length)
    }