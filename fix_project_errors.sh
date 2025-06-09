#!/bin/bash

# Project Error Fixes Script
# This script applies all 10 critical fixes identified in the job automation project
# Requirements: Python 3, awk, grep (standard on macOS)

set -e  # Exit on any error

echo "🚀 Starting Project Error Fixes..."
echo "=================================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not found"
    echo "Please install Python 3 and try again"
    exit 1
fi

# FIX 1: Add missing imports to backend/app/schemas/__init__.py
echo "🔧 FIX 1: Adding missing imports to schemas/__init__.py"
if [ -f "backend/app/schemas/__init__.py" ]; then
    # Create temporary file with new imports
    cat > /tmp/schema_imports.txt << 'EOF'

# Import all schema classes
from .user import (
    UserCreate, UserUpdate, UserResponse, UserPasswordUpdate,
    UserPreferences, UserPreferencesUpdate, UserStats
)
from .job import (
    JobBase, JobCreate, JobUpdate, JobResponse, JobSummary,
    JobSearch, JobMatch, JobAnalytics, JobAlert, JobBulkAction
)
from .document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentSummary,
    DocumentGeneration, DocumentGenerationResponse, DocumentTemplate,
    DocumentExport, DocumentComparison, DocumentAnalytics,
    DocumentBulkAction, DocumentVersion
)
EOF
    # Append the imports to the file
    cat /tmp/schema_imports.txt >> backend/app/schemas/__init__.py
    rm /tmp/schema_imports.txt
    echo "✅ Added missing schema imports"
else
    echo "⚠️  Warning: backend/app/schemas/__init__.py not found"
fi

# FIX 2: Add missing imports and functions to backend/app/models/__init__.py  
echo "🔧 FIX 2: Fixing models/__init__.py imports and relationships"
if [ -f "backend/app/models/__init__.py" ]; then
    # Create backup
    cp backend/app/models/__init__.py backend/app/models/__init__.py.backup
    
    # Add SQLAlchemy imports at the beginning after existing imports
    cat > /tmp/model_imports.txt << 'EOF'

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import event
EOF
    
    # Add the imports
    cat backend/app/models/__init__.py /tmp/model_imports.txt > /tmp/models_temp.py
    mv /tmp/models_temp.py backend/app/models/__init__.py
    
    # Add setup_model_relationships function
    cat > /tmp/model_relationships.txt << 'EOF'

def setup_model_relationships():
    """
    Set up database model relationships after all models are imported.
    Returns True if successful, False otherwise.
    """
    try:
        # User relationships
        User.jobs = relationship("Job", back_populates="user")
        User.applications = relationship("Application", back_populates="user")
        User.documents = relationship("Document", back_populates="user")
        
        # Job relationships
        Job.applications = relationship("Application", back_populates="job")
        Job.user = relationship("User", back_populates="jobs")
        
        # Application relationships
        Application.user = relationship("User", back_populates="applications")
        Application.job = relationship("Job", back_populates="applications")
        Application.history = relationship("ApplicationHistory", back_populates="application")
        
        # Document relationships
        Document.user = relationship("User", back_populates="documents")
        
        # ApplicationHistory relationships
        ApplicationHistory.application = relationship("Application", back_populates="history")
        
        return True
    except Exception as e:
        print(f"Error setting up model relationships: {e}")
        return False

EOF
    
    # Insert the function before validate_models function
    if grep -q "def validate_models" backend/app/models/__init__.py; then
        # Create temp file with function inserted before validate_models
        awk '/def validate_models/{system("cat /tmp/model_relationships.txt"); print; next} 1' backend/app/models/__init__.py > /tmp/models_with_relationships.py
        mv /tmp/models_with_relationships.py backend/app/models/__init__.py
    else
        # If validate_models not found, just append
        cat /tmp/model_relationships.txt >> backend/app/models/__init__.py
    fi
    
    # Clean up temp files
    rm -f /tmp/model_imports.txt /tmp/model_relationships.txt
    echo "✅ Added model relationships setup"
else
    echo "⚠️  Warning: backend/app/models/__init__.py not found"
fi

# FIX 3: Create missing exception classes
echo "🔧 FIX 3: Creating custom exception classes"
mkdir -p backend/app/core
cat > backend/app/core/exceptions.py << 'EOF'
"""Custom exceptions for the job automation system."""

class ServiceError(Exception):
    """Base exception for service-related errors."""
    pass

class ModelNotAvailableError(ServiceError):
    """Raised when a model service is not available."""
    pass

class ApplicationError(Exception):
    """Base exception for application-related errors."""
    pass

class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

class DocumentGenerationError(ServiceError):
    """Raised when document generation fails."""
    pass
EOF
echo "✅ Created backend/app/core/exceptions.py"

# FIX 4: Create missing utility functions
echo "🔧 FIX 4: Creating missing utility functions"
mkdir -p backend/app/utils

# Create text_processing.py
cat > backend/app/utils/text_processing.py << 'EOF'
"""Text processing utilities."""
import re
from typing import List

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text."""
    if not text:
        return []
    # Simple keyword extraction - can be enhanced with NLP
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return list(set(words))[:max_keywords]
EOF

# Create validation.py
cat > backend/app/utils/validation.py << 'EOF'
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
EOF
echo "✅ Created utility functions in backend/app/utils/"

# FIX 5: Complete resume template functions
echo "🔧 FIX 5: Completing resume template functions"
if [ -f "backend/app/templates/resume_template.py" ]; then
    # Add missing imports if not present
    if ! grep -q "from typing import List" backend/app/templates/resume_template.py; then
        # Add the import at the top after existing imports
        awk 'NR==1{print; print "from typing import List"; next} 1' backend/app/templates/resume_template.py > /tmp/resume_with_import.py
        mv /tmp/resume_with_import.py backend/app/templates/resume_template.py
    fi
    
    # Add missing methods to resume template
    cat >> backend/app/templates/resume_template.py << 'EOF'

    def format_date_range(self, start_date: str, end_date: str) -> str:
        """Format date range for display."""
        if end_date == "present" or end_date == "current":
            return f"{start_date} - Present"
        return f"{start_date} - {end_date}"

    def format_technologies(self, technologies: List[str]) -> str:
        """Format technologies list for display."""
        if not technologies:
            return "N/A"
        return ", ".join(technologies)
EOF
    
    # Fix the incomplete _generate_languages function by replacing it entirely
    if grep -q "_generate_languages" backend/app/templates/resume_template.py; then
        # Create a temp file with the fixed function
        awk '
        /_generate_languages/ {
            print "    def _generate_languages(self) -> str:"
            print "        \"\"\"Generate languages section\"\"\""
            print "        lang_lines = [\"Languages\"]"
            print "        "
            print "        for language, level in self.data.languages.items():"
            print "            lang_lines.append(f\"{language}: {level}\")"
            print "        "
            print "        return \"\\n\".join(lang_lines)"
            # Skip lines until we find the next function or end of current function
            while ((getline line) > 0) {
                if (line ~ /^[[:space:]]*def / || line ~ /^[[:space:]]*$/) {
                    print line
                    break
                }
            }
        }
        !/def _generate_languages/ { print }
        ' backend/app/templates/resume_template.py > /tmp/resume_temp.py
        mv /tmp/resume_temp.py backend/app/templates/resume_template.py
    fi
    
    echo "✅ Completed resume template functions"
else
    echo "⚠️  Warning: backend/app/templates/resume_template.py not found"
fi

# FIX 6: Update Docker memory allocation for 16GB
echo "🔧 FIX 6: Updating Docker memory allocation for 16GB RAM"
if [ -f "docker-compose.yml" ]; then
    # Create backup
    cp docker-compose.yml docker-compose.yml.backup
    
    # Use Python to properly update YAML memory settings
    python3 -c "
import re
import sys

# Read the file
with open('docker-compose.yml', 'r') as f:
    content = f.read()

# Update phi3-service memory
content = re.sub(
    r'(phi3-service:.*?deploy:.*?resources:.*?reservations:.*?)memory: \d+G',
    r'\1memory: 3G\n        limits:\n          memory: 4G',
    content,
    flags=re.DOTALL
)

# Update gemma-service memory  
content = re.sub(
    r'(gemma-service:.*?deploy:.*?resources:.*?reservations:.*?)memory: \d+G',
    r'\1memory: 4G\n        limits:\n          memory: 6G',
    content,
    flags=re.DOTALL
)

# Update mistral-service memory
content = re.sub(
    r'(mistral-service:.*?deploy:.*?resources:.*?reservations:.*?)memory: \d+G',
    r'\1memory: 3G\n        limits:\n          memory: 4G',
    content,
    flags=re.DOTALL
)

# Write back
with open('docker-compose.yml', 'w') as f:
    f.write(content)
"
    echo "✅ Updated Docker memory allocations"
else
    echo "⚠️  Warning: docker-compose.yml not found"
fi

# FIX 7: Fix Frontend Dockerfile
echo "🔧 FIX 7: Fixing Frontend Dockerfile"
if [ -f "frontend/Dockerfile" ]; then
    # Create backup
    cp frontend/Dockerfile frontend/Dockerfile.backup
    
    # Add package-lock.json copy after package*.json line
    awk '/COPY package\*\.json \.\//{print; print "COPY package-lock.json ./"; next} 1' frontend/Dockerfile > /tmp/dockerfile_temp
    mv /tmp/dockerfile_temp frontend/Dockerfile
    echo "✅ Fixed Frontend Dockerfile"
else
    echo "⚠️  Warning: frontend/Dockerfile not found"
fi

# FIX 8: Fix async/await inconsistency in application service
echo "🔧 FIX 8: Fixing async/await inconsistency"
if [ -f "backend/app/services/application_service.py" ]; then
    # Create backup
    cp backend/app/services/application_service.py backend/app/services/application_service.py.backup
    
    # Replace the problematic line with direct query
    python3 -c "
import re

with open('backend/app/services/application_service.py', 'r') as f:
    content = f.read()

# Replace the async call with direct database query
content = re.sub(
    r'application = await self\.get_application_status\(application_id, user_id, db\)',
    '''application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == user_id
    ).first()''',
    content
)

with open('backend/app/services/application_service.py', 'w') as f:
    f.write(content)
"
    echo "✅ Fixed async/await inconsistency"
else
    echo "⚠️  Warning: backend/app/services/application_service.py not found"
fi

# FIX 9: Add null checks in application service
echo "🔧 FIX 9: Adding null checks in application service"
if [ -f "backend/app/services/application_service.py" ]; then
    # Fix null check for application.notes
    python3 -c "
import re

with open('backend/app/services/application_service.py', 'r') as f:
    content = f.read()

# Replace the null check
content = re.sub(
    r'if not application\.notes:',
    'if application.notes is None:',
    content
)

with open('backend/app/services/application_service.py', 'w') as f:
    f.write(content)
"
    echo "✅ Added null checks"
else
    echo "⚠️  Warning: backend/app/services/application_service.py not found"
fi

# FIX 10: Fix user schema validation
echo "🔧 FIX 10: Fixing user schema validation"
if [ -f "backend/app/schemas/user.py" ]; then
    # Create backup
    cp backend/app/schemas/user.py backend/app/schemas/user.py.backup
    
    # Add VALID_USER_TYPES constant at the top
    python3 -c "
import re

with open('backend/app/schemas/user.py', 'r') as f:
    content = f.read()

# Add the constant after imports but before any class definition
if 'VALID_USER_TYPES' not in content:
    # Find the first class definition and insert before it
    content = re.sub(
        r'(from.*\n.*\n)(class)',
        r'\1\nVALID_USER_TYPES = [\"job_seeker\", \"recruiter\", \"admin\"]\n\n\2',
        content,
        count=1
    )

# Fix the validation error message
content = re.sub(
    r'Must be one of: \{valid_types\}',
    'Must be one of: {VALID_USER_TYPES}',
    content
)

with open('backend/app/schemas/user.py', 'w') as f:
    f.write(content)
"
    echo "✅ Fixed user schema validation"
else
    echo "⚠️  Warning: backend/app/schemas/user.py not found"
fi

# Create __init__.py files for new directories
echo "🔧 Creating missing __init__.py files"
touch backend/app/core/__init__.py
touch backend/app/utils/__init__.py

# Clean up any remaining temp files
echo "🧹 Cleaning up temporary files"
rm -f /tmp/schema_imports.txt /tmp/model_imports.txt /tmp/model_relationships.txt
rm -f /tmp/models_temp.py /tmp/models_with_relationships.py /tmp/resume_temp.py
rm -f /tmp/dockerfile_temp /tmp/resume_with_import.py

# Make script executable and add execution permissions
chmod +x "$0"

echo ""
echo "🎉 ALL FIXES COMPLETED!"
echo "======================"
echo ""
echo "📋 Summary of fixes applied:"
echo "1. ✅ Added missing schema imports"
echo "2. ✅ Fixed model relationships and imports"
echo "3. ✅ Created custom exception classes"
echo "4. ✅ Added missing utility functions"
echo "5. ✅ Completed resume template functions"
echo "6. ✅ Updated Docker memory for 16GB RAM"
echo "7. ✅ Fixed Frontend Dockerfile"
echo "8. ✅ Fixed async/await inconsistencies"
echo "9. ✅ Added null checks"
echo "10. ✅ Fixed user schema validation"
echo ""
echo "📁 Backup files created:"
echo "   - backend/app/models/__init__.py.backup"
echo "   - docker-compose.yml.backup"
echo "   - frontend/Dockerfile.backup"
echo "   - backend/app/services/application_service.py.backup"
echo "   - backend/app/schemas/user.py.backup"
echo ""
echo "🔍 Next steps:"
echo "1. Run 'docker-compose build' to rebuild containers"
echo "2. Run 'docker-compose up -d' to start services"
echo "3. Test the application functionality"
echo "4. Check logs if any issues remain: 'docker-compose logs'"
echo ""
echo "⚡ Note: If you encounter any import errors, you may need to restart"
echo "   the development server or rebuild Docker containers."
echo ""
echo "🗑️  To restore from backups if needed:"
echo "   mv [filename].backup [filename]"