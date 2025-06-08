"""
Unit tests for utility functions.

Tests text processing, file handling, validation, and encryption utilities.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, mock_open
from datetime import datetime
from PIL import Image
import io

from app.utils.text_processing import (
    clean_text, extract_keywords, similarity_score, 
    normalize_text, extract_emails, extract_phone_numbers,
    count_words, truncate_text, remove_html_tags
)
from app.utils.file_handling import (
    save_file, delete_file, get_file_info, validate_file_type,
    compress_file, extract_text_from_pdf, convert_to_pdf,
    generate_thumbnail, get_file_hash
)
from app.utils.validation import (
    validate_email, validate_phone, validate_url,
    validate_password_strength, sanitize_input,
    validate_job_data, validate_user_data
)
from app.utils.encryption import (
    encrypt_data, decrypt_data, hash_password,
    generate_token, verify_token, encrypt_file, decrypt_file
)


class TestTextProcessing:
    """Test suite for text processing utilities."""

    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        dirty_text = "  Hello\n\nWorld!\t  "
        clean = clean_text(dirty_text)
        
        assert clean == "Hello World!"

    def test_clean_text_with_special_chars(self):
        """Test cleaning text with special characters."""
        text = "Hello @#$% World!!! 123"
        clean = clean_text(text, remove_special_chars=True)
        
        assert clean == "Hello World 123"

    def test_extract_keywords(self):
        """Test keyword extraction from text."""
        text = """
        Senior Software Engineer position requiring Python, JavaScript, and React.
        Experience with Django, FastAPI, and PostgreSQL databases.
        Strong problem-solving skills and team collaboration.
        """
        
        keywords = extract_keywords(text, limit=5)
        
        assert len(keywords) <= 5
        assert any("python" in kw.lower() for kw in keywords)
        assert any("react" in kw.lower() for kw in keywords)

    def test_similarity_score(self):
        """Test text similarity scoring."""
        text1 = "Senior Python Developer with FastAPI experience"
        text2 = "Python Developer with FastAPI and Django skills"
        text3 = "Marketing Manager with social media experience"
        
        # Similar texts should have high score
        score1 = similarity_score(text1, text2)
        assert score1 > 0.7
        
        # Different texts should have low score
        score2 = similarity_score(text1, text3)
        assert score2 < 0.3

    def test_normalize_text(self):
        """Test text normalization."""
        text = "Hello WORLD! This is a TEST."
        normalized = normalize_text(text)
        
        assert normalized == "hello world this is a test"

    def test_extract_emails(self):
        """Test email extraction from text."""
        text = """
        Contact us at info@company.com or support@example.org.
        You can also reach john.doe@test.co.uk for more information.
        """
        
        emails = extract_emails(text)
        
        assert "info@company.com" in emails
        assert "support@example.org" in emails
        assert "john.doe@test.co.uk" in emails
        assert len(emails) == 3

    def test_extract_phone_numbers(self):
        """Test phone number extraction from text."""
        text = """
        Call us at (555) 123-4567 or +1-800-555-0199.
        International: +44 20 7946 0958
        """
        
        phones = extract_phone_numbers(text)
        
        assert len(phones) >= 2
        assert any("555" in phone for phone in phones)

    def test_count_words(self):
        """Test word counting."""
        text = "This is a test sentence with seven words."
        count = count_words(text)
        
        assert count == 8

    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a very long sentence that should be truncated."
        
        # Truncate by character count
        truncated = truncate_text(text, max_length=20)
        assert len(truncated) <= 23  # Including "..."
        assert truncated.endswith("...")
        
        # Truncate by word count
        truncated_words = truncate_text(text, max_words=5)
        word_count = len(truncated_words.replace("...", "").split())
        assert word_count <= 5

    def test_remove_html_tags(self):
        """Test HTML tag removal."""
        html_text = "<p>Hello <strong>World</strong>!</p><br><a href='#'>Link</a>"
        clean = remove_html_tags(html_text)
        
        assert clean == "Hello World! Link"
        assert "<" not in clean
        assert ">" not in clean


class TestFileHandling:
    """Test suite for file handling utilities."""

    @pytest.fixture
    def sample_text_file(self):
        """Create a sample text file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test file content.")
            f.flush()
            yield f.name
        
        # Cleanup
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f, format='PNG')
            f.flush()
            yield f.name
        
        # Cleanup
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass

    def test_save_file(self, sample_text_file):
        """Test file saving functionality."""
        with open(sample_text_file, 'rb') as f:
            file_content = f.read()
        
        saved_path = save_file(file_content, "test_save.txt", "/tmp")
        
        assert os.path.exists(saved_path)
        assert saved_path.endswith("test_save.txt")
        
        # Cleanup
        os.unlink(saved_path)

    def test_delete_file(self, sample_text_file):
        """Test file deletion."""
        assert os.path.exists(sample_text_file)
        
        result = delete_file(sample_text_file)
        
        assert result is True
        assert not os.path.exists(sample_text_file)

    def test_delete_nonexistent_file(self):
        """Test deleting non-existent file."""
        result = delete_file("/nonexistent/file.txt")
        
        assert result is False

    def test_get_file_info(self, sample_text_file):
        """Test getting file information."""
        info = get_file_info(sample_text_file)
        
        assert info["filename"] == os.path.basename(sample_text_file)
        assert info["size"] > 0
        assert info["extension"] == ".txt"
        assert "created_at" in info
        assert "modified_at" in info

    def test_validate_file_type_allowed(self):
        """Test file type validation with allowed types."""
        allowed_types = ['.pdf', '.doc', '.docx', '.txt']
        
        assert validate_file_type("resume.pdf", allowed_types) is True
        assert validate_file_type("document.docx", allowed_types) is True
        assert validate_file_type("notes.txt", allowed_types) is True

    def test_validate_file_type_disallowed(self):
        """Test file type validation with disallowed types."""
        allowed_types = ['.pdf', '.doc', '.docx']
        
        assert validate_file_type("image.jpg", allowed_types) is False
        assert validate_file_type("script.exe", allowed_types) is False

    @patch('zipfile.ZipFile')
    def test_compress_file(self, mock_zipfile, sample_text_file):
        """Test file compression."""
        mock_zip = mock_zipfile.return_value.__enter__.return_value
        
        compressed_path = compress_file(sample_text_file, "compressed.zip")
        
        assert compressed_path.endswith("compressed.zip")
        mock_zip.write.assert_called_once()

    @patch('PyPDF2.PdfReader')
    def test_extract_text_from_pdf(self, mock_pdf_reader):
        """Test text extraction from PDF."""
        # Mock PDF reader
        mock_page = mock_pdf_reader.return_value.pages[0]
        mock_page.extract_text.return_value = "Extracted PDF text content"
        
        with patch('builtins.open', mock_open()):
            text = extract_text_from_pdf("test.pdf")
        
        assert text == "Extracted PDF text content"

    def test_generate_thumbnail(self, sample_image_file):
        """Test thumbnail generation."""
        thumbnail_path = generate_thumbnail(sample_image_file, size=(50, 50))
        
        assert os.path.exists(thumbnail_path)
        
        # Verify thumbnail size
        with Image.open(thumbnail_path) as thumb:
            assert thumb.size == (50, 50)
        
        # Cleanup
        os.unlink(thumbnail_path)

    def test_get_file_hash(self, sample_text_file):
        """Test file hash generation."""
        hash1 = get_file_hash(sample_text_file)
        hash2 = get_file_hash(sample_text_file)
        
        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hash length

    def test_get_file_hash_different_files(self, sample_text_file):
        """Test that different files produce different hashes."""
        # Create another file with different content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Different content")
            f.flush()
            different_file = f.name
        
        try:
            hash1 = get_file_hash(sample_text_file)
            hash2 = get_file_hash(different_file)
            
            assert hash1 != hash2
        finally:
            os.unlink(different_file)


class TestValidation:
    """Test suite for validation utilities."""

    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@subdomain.example.org"
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..double.dot@example.com",
            "user@.com"
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False

    def test_validate_phone_valid(self):
        """Test phone validation with valid numbers."""
        valid_phones = [
            "+1234567890",
            "(555) 123-4567",
            "555-123-4567",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            assert validate_phone(phone) is True

    def test_validate_phone_invalid(self):
        """Test phone validation with invalid numbers."""
        invalid_phones = [
            "123",
            "abc-def-ghij",
            "123-45-6789",  # Too short
            "++1234567890"  # Double plus
        ]
        
        for phone in invalid_phones:
            assert validate_phone(phone) is False

    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://www.example.com",
            "http://subdomain.example.org/path",
            "https://example.com:8080/api/v1",
            "ftp://files.example.com/file.txt"
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True

    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "http://",
            "https://",
            "example.com",  # Missing protocol
            "http://.com"
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False

    def test_validate_password_strength_strong(self):
        """Test password strength validation with strong passwords."""
        strong_passwords = [
            "StrongP@ssw0rd123",
            "C0mpl3x!P@ssw0rd",
            "Secure123$Password"
        ]
        
        for password in strong_passwords:
            result = validate_password_strength(password)
            assert result["is_strong"] is True
            assert result["score"] >= 8

    def test_validate_password_strength_weak(self):
        """Test password strength validation with weak passwords."""
        weak_passwords = [
            "password",
            "123456",
            "abc123",
            "Password"  # Missing special chars and numbers
        ]
        
        for password in weak_passwords:
            result = validate_password_strength(password)
            assert result["is_strong"] is False
            assert len(result["suggestions"]) > 0

    def test_sanitize_input(self):
        """Test input sanitization."""
        dirty_input = "<script>alert('xss')</script>Hello World!"
        clean = sanitize_input(dirty_input)
        
        assert "<script>" not in clean
        assert "Hello World!" in clean

    def test_validate_job_data_valid(self):
        """Test job data validation with valid data."""
        job_data = {
            "title": "Software Engineer",
            "company": "TechCorp",
            "location": "San Francisco, CA",
            "job_type": "full-time",
            "salary_min": 80000,
            "salary_max": 120000,
            "description": "We are looking for a software engineer...",
            "url": "https://company.com/jobs/123"
        }
        
        result = validate_job_data(job_data)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_job_data_invalid(self):
        """Test job data validation with invalid data."""
        job_data = {
            "title": "",  # Empty title
            "company": "TechCorp",
            "salary_min": 150000,  # Min > Max
            "salary_max": 100000,
            "url": "invalid-url"  # Invalid URL
        }
        
        result = validate_job_data(job_data)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_user_data_valid(self):
        """Test user data validation with valid data."""
        user_data = {
            "email": "user@example.com",
            "full_name": "John Doe",
            "phone_number": "+1234567890",
            "location": "New York, NY",
            "skills": ["Python", "JavaScript"],
            "experience_years": 5
        }
        
        result = validate_user_data(user_data)
        assert result["is_valid"] is True

    def test_validate_user_data_invalid(self):
        """Test user data validation with invalid data."""
        user_data = {
            "email": "invalid-email",
            "full_name": "",
            "phone_number": "invalid-phone",
            "experience_years": -1  # Negative experience
        }
        
        result = validate_user_data(user_data)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0


class TestEncryption:
    """Test suite for encryption utilities."""

    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption."""
        original_data = "Sensitive user information"
        password = "encryption_key_123"
        
        # Encrypt data
        encrypted = encrypt_data(original_data, password)
        assert encrypted != original_data
        
        # Decrypt data
        decrypted = decrypt_data(encrypted, password)
        assert decrypted == original_data

    def test_encrypt_decrypt_with_wrong_password(self):
        """Test decryption with wrong password."""
        original_data = "Secret data"
        correct_password = "correct_key"
        wrong_password = "wrong_key"
        
        encrypted = encrypt_data(original_data, correct_password)
        
        # Should raise exception or return None
        with pytest.raises((ValueError, Exception)):
            decrypt_data(encrypted, wrong_password)

    def test_hash_password(self):
        """Test password hashing."""
        password = "user_password_123"
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Same password should produce different hashes (due to salt)
        assert hash1 != hash2
        assert len(hash1) > 50  # Should include salt and hash

    def test_generate_token(self):
        """Test token generation."""
        token1 = generate_token()
        token2 = generate_token()
        
        # Tokens should be unique
        assert token1 != token2
        assert len(token1) >= 32  # Reasonable token length

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"user_id": 123, "exp": datetime.now().timestamp() + 3600}
        secret = "token_secret"
        
        token = generate_token(data, secret)
        verified_data = verify_token(token, secret)
        
        assert verified_data["user_id"] == 123

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.data"
        secret = "token_secret"
        
        result = verify_token(invalid_token, secret)
        assert result is None

    def test_encrypt_decrypt_file(self, sample_text_file):
        """Test file encryption and decryption."""
        password = "file_encryption_key"
        
        # Encrypt file
        encrypted_path = encrypt_file(sample_text_file, password)
        assert os.path.exists(encrypted_path)
        assert encrypted_path != sample_text_file
        
        # Decrypt file
        decrypted_path = decrypt_file(encrypted_path, password)
        assert os.path.exists(decrypted_path)
        
        # Verify content is same
        with open(sample_text_file, 'r') as f1, open(decrypted_path, 'r') as f2:
            assert f1.read() == f2.read()
        
        # Cleanup
        os.unlink(encrypted_path)
        os.unlink(decrypted_path)

    def test_encrypt_file_with_wrong_password(self, sample_text_file):
        """Test file decryption with wrong password."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        
        encrypted_path = encrypt_file(sample_text_file, correct_password)
        
        # Should raise exception
        with pytest.raises((ValueError, Exception)):
            decrypt_file(encrypted_path, wrong_password)
        
        # Cleanup
        os.unlink(encrypted_path)


class TestUtilityIntegration:
    """Integration tests for utility functions working together."""

    def test_text_processing_pipeline(self):
        """Test complete text processing pipeline."""
        raw_text = """
        <h1>Senior Software Engineer</h1>
        <p>We are looking for a Senior Software Engineer with Python, JavaScript, and React experience.</p>
        <p>Contact us at jobs@company.com or call (555) 123-4567</p>
        <script>alert('xss')</script>
        """
        
        # Step 1: Remove HTML tags
        clean_html = remove_html_tags(raw_text)
        
        # Step 2: Sanitize input
        sanitized = sanitize_input(clean_html)
        
        # Step 3: Clean text
        cleaned = clean_text(sanitized)
        
        # Step 4: Extract information
        emails = extract_emails(cleaned)
        phones = extract_phone_numbers(cleaned)
        keywords = extract_keywords(cleaned, limit=5)
        
        assert "Senior Software Engineer" in cleaned
        assert "jobs@company.com" in emails
        assert len(phones) >= 1
        assert len(keywords) > 0
        assert "<script>" not in cleaned

    def test_file_validation_and_processing(self, sample_text_file):
        """Test file validation and processing pipeline."""
        # Step 1: Validate file type
        is_valid = validate_file_type(sample_text_file, ['.txt', '.pdf'])
        assert is_valid is True
        
        # Step 2: Get file info
        file_info = get_file_info(sample_text_file)
        assert file_info["extension"] == ".txt"
        
        # Step 3: Generate hash
        file_hash = get_file_hash(sample_text_file)
        assert len(file_hash) == 64
        
        # Step 4: Compress file
        with patch('zipfile.ZipFile'):
            compressed_path = compress_file(sample_text_file, "test.zip")
            assert compressed_path.endswith("test.zip")

    def test_data_validation_and_encryption(self):
        """Test data validation and encryption pipeline."""
        user_data = {
            "email": "user@example.com",
            "password": "StrongP@ssw0rd123",
            "phone": "+1234567890"
        }
        
        # Step 1: Validate email
        assert validate_email(user_data["email"]) is True
        
        # Step 2: Validate password strength
        password_check = validate_password_strength(user_data["password"])
        assert password_check["is_strong"] is True
        
        # Step 3: Validate phone
        assert validate_phone(user_data["phone"]) is True
        
        # Step 4: Hash password
        hashed_password = hash_password(user_data["password"])
        assert hashed_password != user_data["password"]
        
        # Step 5: Encrypt sensitive data
        encrypted_email = encrypt_data(user_data["email"], "encryption_key")
        assert encrypted_email != user_data["email"]
