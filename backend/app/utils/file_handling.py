"""
File handling utilities for job automation system.

Provides functions for file operations, validation, processing, and conversion.
"""

import os
import shutil
import hashlib
import zipfile
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import magic
from PIL import Image
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import docx
from docx import Document
import aiofiles


def save_file(file_content: bytes, filename: str, directory: str = "/tmp") -> str:
    """
    Save file content to specified directory.
    
    Args:
        file_content: Binary content of the file
        filename: Name for the saved file
        directory: Directory to save the file (default: /tmp)
        
    Returns:
        Full path to the saved file
    """
    try:
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Create full file path
        file_path = os.path.join(directory, filename)
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path
        
    except Exception as e:
        raise IOError(f"Failed to save file: {str(e)}")


def delete_file(file_path: str) -> bool:
    """
    Delete a file from the filesystem.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        True if file was deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
        
    except Exception:
        return False


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file information
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    stat = os.stat(file_path)
    path_obj = Path(file_path)
    
    return {
        "filename": path_obj.name,
        "extension": path_obj.suffix,
        "size": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_ctime),
        "modified_at": datetime.fromtimestamp(stat.st_mtime),
        "is_file": os.path.isfile(file_path),
        "is_readable": os.access(file_path, os.R_OK),
        "is_writable": os.access(file_path, os.W_OK),
        "absolute_path": os.path.abspath(file_path)
    }


def validate_file_type(file_path: str, allowed_types: List[str]) -> bool:
    """
    Validate if file type is in allowed list.
    
    Args:
        file_path: Path to the file or filename
        allowed_types: List of allowed file extensions (e.g., ['.pdf', '.docx'])
        
    Returns:
        True if file type is allowed, False otherwise
    """
    if not file_path:
        return False
    
    # Get file extension
    _, ext = os.path.splitext(file_path.lower())
    
    # Normalize allowed types to lowercase
    allowed_types_lower = [ext.lower() for ext in allowed_types]
    
    return ext in allowed_types_lower


def compress_file(file_path: str, output_path: str) -> str:
    """
    Compress a file into a ZIP archive.
    
    Args:
        file_path: Path to the file to compress
        output_path: Path for the output ZIP file
        
    Returns:
        Path to the created ZIP file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add file to zip with just its basename
            zipf.write(file_path, os.path.basename(file_path))
        
        return output_path
        
    except Exception as e:
        raise IOError(f"Failed to compress file: {str(e)}")


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text content
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        text_content = ""
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        
        return text_content.strip()
        
    except Exception as e:
        raise IOError(f"Failed to extract text from PDF: {str(e)}")


def convert_to_pdf(content: str, output_path: str, title: str = "Document") -> str:
    """
    Convert text content to PDF file.
    
    Args:
        content: Text content to convert
        output_path: Path for the output PDF file
        title: Title for the PDF document
        
    Returns:
        Path to the created PDF file
    """
    try:
        # Create PDF canvas
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Set title
        c.setTitle(title)
        
        # Set font
        c.setFont("Helvetica", 12)
        
        # Split content into lines
        lines = content.split('\n')
        y_position = height - 50  # Start near top of page
        line_height = 14
        
        for line in lines:
            # Handle page breaks
            if y_position < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 50
            
            # Wrap long lines
            if len(line) > 80:
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    if len(current_line + word) < 80:
                        current_line += word + " "
                    else:
                        if current_line:
                            c.drawString(50, y_position, current_line.strip())
                            y_position -= line_height
                            
                            if y_position < 50:
                                c.showPage()
                                c.setFont("Helvetica", 12)
                                y_position = height - 50
                        
                        current_line = word + " "
                
                if current_line:
                    c.drawString(50, y_position, current_line.strip())
                    y_position -= line_height
            else:
                c.drawString(50, y_position, line)
                y_position -= line_height
        
        # Save PDF
        c.save()
        
        return output_path
        
    except Exception as e:
        raise IOError(f"Failed to create PDF: {str(e)}")


def generate_thumbnail(image_path: str, size: tuple = (150, 150)) -> str:
    """
    Generate a thumbnail for an image file.
    
    Args:
        image_path: Path to the source image
        size: Tuple of (width, height) for thumbnail
        
    Returns:
        Path to the generated thumbnail
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    try:
        # Open image
        with Image.open(image_path) as img:
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Generate thumbnail filename
            path_obj = Path(image_path)
            thumbnail_name = f"{path_obj.stem}_thumb{path_obj.suffix}"
            thumbnail_path = os.path.join(path_obj.parent, thumbnail_name)
            
            # Save thumbnail
            img.save(thumbnail_path)
            
            return thumbnail_path
            
    except Exception as e:
        raise IOError(f"Failed to generate thumbnail: {str(e)}")


def get_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Generate hash for a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hashing algorithm (sha256, md5, sha1)
        
    Returns:
        Hexadecimal hash string
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        # Get hash function
        hash_func = hashlib.new(algorithm)
        
        # Read file in chunks for memory efficiency
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
        
    except Exception as e:
        raise IOError(f"Failed to generate file hash: {str(e)}")


def get_file_mime_type(file_path: str) -> str:
    """
    Get MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        mime_type = magic.from_file(file_path, mime=True)
        return mime_type
        
    except Exception:
        # Fallback to extension-based detection
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.zip': 'application/zip',
            '.html': 'text/html',
            '.json': 'application/json',
            '.xml': 'application/xml'
        }
        
        return mime_types.get(ext, 'application/octet-stream')


def copy_file(source_path: str, destination_path: str) -> str:
    """
    Copy a file from source to destination.
    
    Args:
        source_path: Path to source file
        destination_path: Path to destination
        
    Returns:
        Path to the copied file
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    try:
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Copy file
        shutil.copy2(source_path, destination_path)
        
        return destination_path
        
    except Exception as e:
        raise IOError(f"Failed to copy file: {str(e)}")


def move_file(source_path: str, destination_path: str) -> str:
    """
    Move a file from source to destination.
    
    Args:
        source_path: Path to source file
        destination_path: Path to destination
        
    Returns:
        Path to the moved file
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    try:
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Move file
        shutil.move(source_path, destination_path)
        
        return destination_path
        
    except Exception as e:
        raise IOError(f"Failed to move file: {str(e)}")


async def save_file_async(file_content: bytes, filename: str, directory: str = "/tmp") -> str:
    """
    Asynchronously save file content to specified directory.
    
    Args:
        file_content: Binary content of the file
        filename: Name for the saved file
        directory: Directory to save the file
        
    Returns:
        Full path to the saved file
    """
    try:
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Create full file path
        file_path = os.path.join(directory, filename)
        
        # Save file asynchronously
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return file_path
        
    except Exception as e:
        raise IOError(f"Failed to save file: {str(e)}")


def extract_docx_text(docx_path: str) -> str:
    """
    Extract text content from a DOCX file.
    
    Args:
        docx_path: Path to the DOCX file
        
    Returns:
        Extracted text content
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")
    
    try:
        doc = Document(docx_path)
        text_content = []
        
        for paragraph in doc.paragraphs:
            text_content.append(paragraph.text)
        
        return '\n'.join(text_content)
        
    except Exception as e:
        raise IOError(f"Failed to extract text from DOCX: {str(e)}")


def cleanup_temp_files(directory: str = "/tmp", pattern: str = None, max_age_hours: int = 24) -> int:
    """
    Clean up temporary files in specified directory.
    
    Args:
        directory: Directory to clean up
        pattern: File pattern to match (optional)
        max_age_hours: Maximum age of files to keep in hours
        
    Returns:
        Number of files deleted
    """
    if not os.path.exists(directory):
        return 0
    
    deleted_count = 0
    current_time = datetime.now()
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            # Check pattern if specified
            if pattern and not filename.startswith(pattern):
                continue
            
            # Check file age
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            age_hours = (current_time - file_mtime).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception:
                    continue
        
        return deleted_count
        
    except Exception:
        return 0