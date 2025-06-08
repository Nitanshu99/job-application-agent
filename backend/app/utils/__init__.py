"""
Utility functions package for job automation system.

This package provides common utility functions for:
- Text processing and analysis
- File handling and operations
- Input validation and sanitization
- Data encryption and security

Usage:
    from app.utils.text_processing import clean_text, extract_keywords
    from app.utils.file_handling import save_file, get_file_info
    from app.utils.validation import validate_email, validate_job_data
    from app.utils.encryption import encrypt_data, hash_password
"""

from .text_processing import (
    clean_text,
    extract_keywords,
    similarity_score,
    normalize_text,
    extract_emails,
    extract_phone_numbers,
    count_words,
    truncate_text,
    remove_html_tags
)

from .file_handling import (
    save_file,
    delete_file,
    get_file_info,
    validate_file_type,
    compress_file,
    extract_text_from_pdf,
    convert_to_pdf,
    generate_thumbnail,
    get_file_hash,
    save_file_async
)

from .validation import (
    validate_email,
    validate_phone,
    validate_url,
    validate_password_strength,
    sanitize_input,
    validate_job_data,
    validate_user_data,
    validate_file_upload,
    validate_search_query
)

from .encryption import (
    encrypt_data,
    decrypt_data,
    hash_password,
    verify_password,
    generate_token,
    verify_token,
    encrypt_file,
    decrypt_file,
    generate_api_key,
    generate_csrf_token,
    mask_sensitive_data
)

__version__ = "1.0.0"
__author__ = "Job Automation System"
__description__ = "Utility functions for job automation and application management"

# Package metadata
__all__ = [
    # Text processing
    "clean_text",
    "extract_keywords", 
    "similarity_score",
    "normalize_text",
    "extract_emails",
    "extract_phone_numbers",
    "count_words",
    "truncate_text",
    "remove_html_tags",
    
    # File handling
    "save_file",
    "delete_file",
    "get_file_info",
    "validate_file_type",
    "compress_file",
    "extract_text_from_pdf",
    "convert_to_pdf",
    "generate_thumbnail",
    "get_file_hash",
    "save_file_async",
    
    # Validation
    "validate_email",
    "validate_phone",
    "validate_url",
    "validate_password_strength",
    "sanitize_input",
    "validate_job_data",
    "validate_user_data",
    "validate_file_upload",
    "validate_search_query",
    
    # Encryption
    "encrypt_data",
    "decrypt_data",
    "hash_password",
    "verify_password",
    "generate_token",
    "verify_token",
    "encrypt_file",
    "decrypt_file",
    "generate_api_key",
    "generate_csrf_token",
    "mask_sensitive_data"
]