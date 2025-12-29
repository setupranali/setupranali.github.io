"""
Encryption utilities for credential storage.

WHY ENCRYPTION?
---------------
Data source credentials (passwords, API keys, connection strings) must be
protected at rest. Even if an attacker gains access to the database file,
they should not be able to read plaintext credentials.

This module uses Fernet symmetric encryption from the cryptography library:
- AES-128-CBC encryption
- HMAC-SHA256 authentication
- Base64 encoding for storage

KEY MANAGEMENT:
---------------
- The encryption key is loaded from the UBI_SECRET_KEY environment variable
- For production, use a secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Key rotation is supported by re-encrypting all credentials with a new key

SECURITY NOTES:
---------------
- Never log decrypted credentials
- Never return decrypted credentials in API responses
- Decrypt only when needed internally (e.g., to connect to a database)
- The key must be kept secure and rotated periodically
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet, InvalidToken


# =============================================================================
# KEY MANAGEMENT
# =============================================================================

def _get_or_generate_key() -> bytes:
    """
    Get encryption key from environment variable or generate a new one.
    
    In production:
    - Set UBI_SECRET_KEY environment variable
    - Use a 32-byte URL-safe base64-encoded key
    - Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    
    For development:
    - A key is auto-generated if not set (NOT SECURE FOR PRODUCTION)
    - The auto-generated key is logged as a warning
    """
    key_str = os.environ.get("UBI_SECRET_KEY")
    
    if key_str:
        # Use provided key
        return key_str.encode()
    
    # Development fallback: Generate a deterministic key from a fixed seed
    # WARNING: This is for development only! In production, always set UBI_SECRET_KEY
    import warnings
    warnings.warn(
        "UBI_SECRET_KEY not set! Using development fallback key. "
        "This is NOT secure for production. Set UBI_SECRET_KEY environment variable.",
        RuntimeWarning
    )
    
    # Generate a deterministic key for development (based on a fixed seed)
    # This ensures the same key across restarts during development
    import hashlib
    seed = b"setupranali-dev-key-do-not-use-in-production"
    key_bytes = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(key_bytes)


# Singleton Fernet instance
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create the Fernet encryption instance."""
    global _fernet
    if _fernet is None:
        key = _get_or_generate_key()
        _fernet = Fernet(key)
    return _fernet


# =============================================================================
# ENCRYPTION / DECRYPTION API
# =============================================================================

def encrypt_config(config: Dict[str, Any]) -> str:
    """
    Encrypt a configuration dictionary.
    
    Args:
        config: Dictionary containing sensitive data (e.g., database credentials)
    
    Returns:
        Base64-encoded encrypted string safe for database storage
    
    Example:
        config = {"host": "localhost", "password": "secret"}
        encrypted = encrypt_config(config)
        # Store encrypted in database
    """
    if not config:
        return ""
    
    fernet = _get_fernet()
    
    # Convert dict to JSON string
    json_bytes = json.dumps(config).encode("utf-8")
    
    # Encrypt and return as string
    encrypted_bytes = fernet.encrypt(json_bytes)
    return encrypted_bytes.decode("utf-8")


def decrypt_config(encrypted: str) -> Dict[str, Any]:
    """
    Decrypt an encrypted configuration string.
    
    Args:
        encrypted: Base64-encoded encrypted string from database
    
    Returns:
        Original configuration dictionary
    
    Raises:
        ValueError: If decryption fails (wrong key, corrupted data)
    
    SECURITY: This function should only be called internally when the
    decrypted credentials are actually needed (e.g., to connect to a database).
    Never return the decrypted result in API responses.
    """
    if not encrypted:
        return {}
    
    fernet = _get_fernet()
    
    try:
        # Decrypt
        decrypted_bytes = fernet.decrypt(encrypted.encode("utf-8"))
        
        # Parse JSON
        return json.loads(decrypted_bytes.decode("utf-8"))
    
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt config. This may indicate: "
            "(1) Wrong encryption key, (2) Corrupted data, or "
            "(3) Key was rotated without re-encrypting data."
        )
    except json.JSONDecodeError:
        raise ValueError("Decrypted data is not valid JSON")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_encryption_configured() -> bool:
    """Check if encryption is properly configured for production."""
    return os.environ.get("UBI_SECRET_KEY") is not None


def generate_key() -> str:
    """
    Generate a new Fernet key.
    
    Use this to generate a key for the UBI_SECRET_KEY environment variable:
    
        python -c "from app.crypto import generate_key; print(generate_key())"
    
    Returns:
        A URL-safe base64-encoded 32-byte key
    """
    return Fernet.generate_key().decode("utf-8")


def mask_sensitive_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a config dict with sensitive values masked.
    
    Use this for logging or API responses where you need to show
    the config structure without revealing sensitive values.
    
    Sensitive keys: password, secret, token, key, credential, auth
    """
    if not config:
        return {}
    
    sensitive_keys = {"password", "secret", "token", "key", "credential", "auth", "api_key"}
    
    masked = {}
    for k, v in config.items():
        # Check if key contains a sensitive word
        if any(s in k.lower() for s in sensitive_keys):
            masked[k] = "********"
        elif isinstance(v, dict):
            # Recursively mask nested dicts
            masked[k] = mask_sensitive_config(v)
        else:
            masked[k] = v
    
    return masked

