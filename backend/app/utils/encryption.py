"""
Encryption and security utilities for job automation system.

Provides functions for data encryption, password hashing, token generation,
and secure file handling.
"""

import os
import hashlib
import secrets
import base64
import hmac
import json
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import bcrypt
import jwt
from passlib.context import CryptContext


# Initialize password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_key() -> bytes:
    """
    Generate a secure encryption key.
    
    Returns:
        32-byte encryption key
    """
    return Fernet.generate_key()


def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
    """
    Derive encryption key from password using PBKDF2.
    
    Args:
        password: Password to derive key from
        salt: Salt bytes (generated if not provided)
        
    Returns:
        Tuple of (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_data(data: Union[str, bytes], password: str) -> str:
    """
    Encrypt data using password-derived key.
    
    Args:
        data: Data to encrypt (string or bytes)
        password: Password for encryption
        
    Returns:
        Base64-encoded encrypted data with salt
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Derive key from password
    key, salt = derive_key_from_password(password)
    
    # Create Fernet cipher
    f = Fernet(key)
    
    # Encrypt data
    encrypted_data = f.encrypt(data)
    
    # Combine salt and encrypted data
    combined = salt + encrypted_data
    
    # Return base64 encoded result
    return base64.urlsafe_b64encode(combined).decode('utf-8')


def decrypt_data(encrypted_data: str, password: str) -> str:
    """
    Decrypt data using password-derived key.
    
    Args:
        encrypted_data: Base64-encoded encrypted data
        password: Password for decryption
        
    Returns:
        Decrypted data as string
        
    Raises:
        ValueError: If decryption fails
    """
    try:
        # Decode from base64
        combined = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
        
        # Extract salt (first 16 bytes) and encrypted data
        salt = combined[:16]
        encrypted_bytes = combined[16:]
        
        # Derive key from password and salt
        key, _ = derive_key_from_password(password, salt)
        
        # Create Fernet cipher
        f = Fernet(key)
        
        # Decrypt data
        decrypted_data = f.decrypt(encrypted_bytes)
        
        return decrypted_data.decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token(data: Dict[str, Any] = None, secret_key: str = None, 
                  expires_delta: timedelta = None) -> str:
    """
    Generate JWT token.
    
    Args:
        data: Data to encode in token
        secret_key: Secret key for signing (generated if not provided)
        expires_delta: Token expiration time
        
    Returns:
        JWT token string
    """
    if data is None:
        # Generate random token data
        data = {
            "token_id": secrets.token_hex(16),
            "created_at": datetime.utcnow().isoformat()
        }
    
    if secret_key is None:
        secret_key = secrets.token_hex(32)
    
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    # Add expiration time
    expire = datetime.utcnow() + expires_delta
    data.update({"exp": expire})
    
    # Generate token
    token = jwt.encode(data, secret_key, algorithm="HS256")
    
    return token


def verify_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token to verify
        secret_key: Secret key for verification
        
    Returns:
        Decoded token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
        
    except jwt.PyJWTError:
        return None


def encrypt_file(file_path: str, password: str, output_path: str = None) -> str:
    """
    Encrypt a file using password-derived key.
    
    Args:
        file_path: Path to file to encrypt
        password: Password for encryption
        output_path: Output path for encrypted file (optional)
        
    Returns:
        Path to encrypted file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        IOError: If encryption fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if output_path is None:
        output_path = file_path + ".encrypted"
    
    try:
        # Read file content
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Derive key from password
        key, salt = derive_key_from_password(password)
        
        # Create Fernet cipher
        f = Fernet(key)
        
        # Encrypt file data
        encrypted_data = f.encrypt(file_data)
        
        # Write encrypted file with salt
        with open(output_path, 'wb') as f:
            f.write(salt + encrypted_data)
        
        return output_path
        
    except Exception as e:
        raise IOError(f"File encryption failed: {str(e)}")


def decrypt_file(encrypted_file_path: str, password: str, output_path: str = None) -> str:
    """
    Decrypt a file using password-derived key.
    
    Args:
        encrypted_file_path: Path to encrypted file
        password: Password for decryption
        output_path: Output path for decrypted file (optional)
        
    Returns:
        Path to decrypted file
        
    Raises:
        FileNotFoundError: If encrypted file doesn't exist
        ValueError: If decryption fails
    """
    if not os.path.exists(encrypted_file_path):
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
    
    if output_path is None:
        # Remove .encrypted extension if present
        if encrypted_file_path.endswith('.encrypted'):
            output_path = encrypted_file_path[:-10]
        else:
            output_path = encrypted_file_path + ".decrypted"
    
    try:
        # Read encrypted file
        with open(encrypted_file_path, 'rb') as f:
            encrypted_content = f.read()
        
        # Extract salt (first 16 bytes) and encrypted data
        salt = encrypted_content[:16]
        encrypted_data = encrypted_content[16:]
        
        # Derive key from password and salt
        key, _ = derive_key_from_password(password, salt)
        
        # Create Fernet cipher
        f = Fernet(key)
        
        # Decrypt data
        decrypted_data = f.decrypt(encrypted_data)
        
        # Write decrypted file
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return output_path
        
    except Exception as e:
        raise ValueError(f"File decryption failed: {str(e)}")


def generate_secure_filename(original_filename: str) -> str:
    """
    Generate secure filename by adding random prefix.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Secure filename with random prefix
    """
    # Generate random prefix
    prefix = secrets.token_hex(8)
    
    # Clean filename
    import re
    clean_name = re.sub(r'[^a-zA-Z0-9._-]', '_', original_filename)
    
    return f"{prefix}_{clean_name}"


def generate_api_key(length: int = 32) -> str:
    """
    Generate secure API key.
    
    Args:
        length: Length of the API key
        
    Returns:
        Secure API key string
    """
    return secrets.token_urlsafe(length)


def generate_csrf_token() -> str:
    """
    Generate CSRF token for form protection.
    
    Returns:
        CSRF token string
    """
    return secrets.token_hex(16)


def create_signature(data: str, secret_key: str) -> str:
    """
    Create HMAC signature for data integrity.
    
    Args:
        data: Data to sign
        secret_key: Secret key for signing
        
    Returns:
        Hexadecimal signature string
    """
    signature = hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    )
    return signature.hexdigest()


def verify_signature(data: str, signature: str, secret_key: str) -> bool:
    """
    Verify HMAC signature.
    
    Args:
        data: Original data
        signature: Signature to verify
        secret_key: Secret key for verification
        
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = create_signature(data, secret_key)
    return hmac.compare_digest(signature, expected_signature)


def encrypt_sensitive_data(data: Dict[str, Any], fields_to_encrypt: list, 
                          encryption_key: str) -> Dict[str, Any]:
    """
    Encrypt specific fields in a data dictionary.
    
    Args:
        data: Dictionary containing data
        fields_to_encrypt: List of field names to encrypt
        encryption_key: Key for encryption
        
    Returns:
        Dictionary with specified fields encrypted
    """
    encrypted_data = data.copy()
    
    for field in fields_to_encrypt:
        if field in encrypted_data and encrypted_data[field] is not None:
            # Convert to JSON if not string
            if not isinstance(encrypted_data[field], str):
                field_data = json.dumps(encrypted_data[field])
            else:
                field_data = encrypted_data[field]
            
            # Encrypt field
            encrypted_data[field] = encrypt_data(field_data, encryption_key)
    
    return encrypted_data


def decrypt_sensitive_data(encrypted_data: Dict[str, Any], fields_to_decrypt: list,
                          encryption_key: str) -> Dict[str, Any]:
    """
    Decrypt specific fields in a data dictionary.
    
    Args:
        encrypted_data: Dictionary containing encrypted data
        fields_to_decrypt: List of field names to decrypt
        encryption_key: Key for decryption
        
    Returns:
        Dictionary with specified fields decrypted
    """
    decrypted_data = encrypted_data.copy()
    
    for field in fields_to_decrypt:
        if field in decrypted_data and decrypted_data[field] is not None:
            try:
                # Decrypt field
                decrypted_value = decrypt_data(decrypted_data[field], encryption_key)
                
                # Try to parse as JSON
                try:
                    decrypted_data[field] = json.loads(decrypted_value)
                except json.JSONDecodeError:
                    decrypted_data[field] = decrypted_value
                    
            except ValueError:
                # If decryption fails, keep original value
                pass
    
    return decrypted_data


def secure_delete_file(file_path: str, passes: int = 3) -> bool:
    """
    Securely delete a file by overwriting it multiple times.
    
    Args:
        file_path: Path to file to delete
        passes: Number of overwrite passes
        
    Returns:
        True if file was securely deleted, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        file_size = os.path.getsize(file_path)
        
        # Overwrite file multiple times
        with open(file_path, 'r+b') as f:
            for _ in range(passes):
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Finally delete the file
        os.remove(file_path)
        return True
        
    except Exception:
        return False


def generate_salt(length: int = 16) -> bytes:
    """
    Generate cryptographically secure salt.
    
    Args:
        length: Length of salt in bytes
        
    Returns:
        Random salt bytes
    """
    return os.urandom(length)


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    
    Args:
        val1: First string
        val2: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    return hmac.compare_digest(val1, val2)


def mask_sensitive_data(data: str, mask_char: str = '*', 
                       visible_start: int = 2, visible_end: int = 2) -> str:
    """
    Mask sensitive data for display purposes.
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_start: Number of characters to show at start
        visible_end: Number of characters to show at end
        
    Returns:
        Masked data string
    """
    if not data or len(data) <= visible_start + visible_end:
        return mask_char * len(data) if data else ""
    
    start = data[:visible_start]
    end = data[-visible_end:] if visible_end > 0 else ""
    middle_length = len(data) - visible_start - visible_end
    middle = mask_char * middle_length
    
    return start + middle + end