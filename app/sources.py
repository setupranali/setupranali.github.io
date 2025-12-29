"""
Persistent Data Source Registry with Encrypted Credentials

This module manages data sources (Postgres, etc.) with:
- SQLite persistence (survives server restarts)
- Encrypted credentials at rest
- Safe API responses (credentials never returned)

DATABASE:
---------
Sources are stored in app/db/sources.db with the following schema:
- id: Unique identifier (UUID)
- name: Human-readable name
- type: Source type (postgres, mysql, etc.)
- encrypted_config: Fernet-encrypted JSON credentials
- status: active/inactive
- created_at, updated_at: Timestamps

SECURITY:
---------
- Credentials are encrypted using Fernet (AES-128-CBC)
- API responses NEVER include decrypted credentials
- Only internal functions (like connection_manager) access decrypted configs
- Use get_source_config() to get decrypted config (internal use only)

BACKWARD COMPATIBILITY:
-----------------------
- Same API as the previous in-memory implementation
- register_source(), list_sources(), get_source() unchanged
- SOURCES dict exposed for compatibility (now backed by DB)
"""

import sqlite3
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.crypto import encrypt_config, decrypt_config, mask_sensitive_config


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database path - stored in app/db/ directory
_DB_DIR = Path(__file__).parent / "db"
_DB_PATH = _DB_DIR / "sources.db"

# SQL schema for sources table
_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    encrypted_config TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(type);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
"""


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def _get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    # Ensure directory exists
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    return conn


def init_database():
    """
    Initialize the database schema.
    
    Called on application startup to ensure the sources table exists.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = _get_db_connection()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# SOURCE CRUD OPERATIONS
# =============================================================================

def register_source(payload: dict) -> dict:
    """
    Register a new data source.
    
    Args:
        payload: Dict with keys:
            - name: Human-readable source name
            - type: Source type (postgres, mysql, etc.)
            - config: Connection configuration (will be encrypted)
    
    Returns:
        Source metadata (WITHOUT decrypted config)
    
    Example:
        source = register_source({
            "name": "Production DB",
            "type": "postgres",
            "config": {
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "user": "admin",
                "password": "secret"
            }
        })
    """
    # Validate required fields
    if "name" not in payload:
        raise ValueError("Source name is required")
    if "type" not in payload:
        raise ValueError("Source type is required")
    if "config" not in payload:
        raise ValueError("Source config is required")
    
    source_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Encrypt the config
    encrypted = encrypt_config(payload["config"])
    
    conn = _get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO sources (id, name, type, encrypted_config, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, payload["name"], payload["type"], encrypted, "active", now, now)
        )
        conn.commit()
    finally:
        conn.close()
    
    # Return safe response (no credentials)
    return {
        "id": source_id,
        "name": payload["name"],
        "type": payload["type"],
        "status": "active",
        "created_at": now,
        "updated_at": now
    }


def list_sources() -> List[dict]:
    """
    List all registered sources.
    
    Returns:
        List of source metadata (WITHOUT decrypted configs)
    
    SECURITY: Credentials are never returned in the list.
    """
    conn = _get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, name, type, status, created_at, updated_at FROM sources"
        )
        rows = cursor.fetchall()
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_source(source_id: str) -> dict:
    """
    Get source metadata by ID.
    
    Args:
        source_id: UUID of the source
    
    Returns:
        Source metadata (WITHOUT decrypted config)
    
    Raises:
        KeyError: If source not found
    
    SECURITY: This returns safe metadata only.
    Use get_source_config() for internal credential access.
    """
    conn = _get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, name, type, status, created_at, updated_at FROM sources WHERE id = ?",
            (source_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise KeyError(f"Source not found: {source_id}")
        
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    finally:
        conn.close()


def get_source_with_config(source_id: str) -> dict:
    """
    Get source with decrypted config (INTERNAL USE ONLY).
    
    WARNING: This returns decrypted credentials!
    Only use this internally (e.g., connection_manager, source testing).
    NEVER return this data in API responses.
    
    Args:
        source_id: UUID of the source
    
    Returns:
        Source metadata including decrypted 'config' field
    
    Raises:
        KeyError: If source not found
        ValueError: If decryption fails
    """
    conn = _get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, name, type, encrypted_config, status, created_at, updated_at FROM sources WHERE id = ?",
            (source_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise KeyError(f"Source not found: {source_id}")
        
        # Decrypt the config
        config = decrypt_config(row["encrypted_config"])
        
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "config": config,  # Decrypted - internal use only!
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    finally:
        conn.close()


def update_source(source_id: str, updates: dict) -> dict:
    """
    Update a source.
    
    Args:
        source_id: UUID of the source
        updates: Dict with optional keys: name, type, config, status
    
    Returns:
        Updated source metadata (WITHOUT decrypted config)
    """
    # Get existing source to ensure it exists
    get_source(source_id)
    
    now = datetime.now(timezone.utc).isoformat()
    
    conn = _get_db_connection()
    try:
        # Build update query dynamically
        set_clauses = ["updated_at = ?"]
        params = [now]
        
        if "name" in updates:
            set_clauses.append("name = ?")
            params.append(updates["name"])
        
        if "type" in updates:
            set_clauses.append("type = ?")
            params.append(updates["type"])
        
        if "config" in updates:
            set_clauses.append("encrypted_config = ?")
            params.append(encrypt_config(updates["config"]))
        
        if "status" in updates:
            set_clauses.append("status = ?")
            params.append(updates["status"])
        
        params.append(source_id)
        
        conn.execute(
            f"UPDATE sources SET {', '.join(set_clauses)} WHERE id = ?",
            params
        )
        conn.commit()
    finally:
        conn.close()
    
    return get_source(source_id)


def delete_source(source_id: str) -> bool:
    """
    Delete a source.
    
    Args:
        source_id: UUID of the source
    
    Returns:
        True if deleted, False if not found
    """
    conn = _get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM sources WHERE id = ?",
            (source_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# =============================================================================
# BACKWARD COMPATIBILITY: SOURCES DICT INTERFACE
# =============================================================================
# The old implementation used a SOURCES dict. We maintain compatibility by
# providing a dict-like interface that's backed by the database.

class SourcesProxy:
    """
    Dict-like proxy to the sources database.
    
    Provides backward compatibility with code that accesses SOURCES dict.
    
    Example:
        if source_id in SOURCES:
            src = SOURCES[source_id]
    
    NOTE: This proxy includes decrypted configs for internal use.
    It should only be used by internal code (connection_manager).
    """
    
    def __getitem__(self, source_id: str) -> dict:
        """Get source with decrypted config."""
        return get_source_with_config(source_id)
    
    def __contains__(self, source_id: str) -> bool:
        """Check if source exists."""
        try:
            get_source(source_id)
            return True
        except KeyError:
            return False
    
    def __iter__(self):
        """Iterate over source IDs."""
        return iter(source["id"] for source in list_sources())
    
    def __len__(self) -> int:
        """Count sources."""
        return len(list_sources())
    
    def values(self) -> List[dict]:
        """Get all sources with decrypted configs (internal use only)."""
        sources = []
        for source in list_sources():
            sources.append(get_source_with_config(source["id"]))
        return sources
    
    def keys(self) -> List[str]:
        """Get all source IDs."""
        return [source["id"] for source in list_sources()]
    
    def items(self):
        """Get all (id, source) pairs with decrypted configs."""
        for source in list_sources():
            yield source["id"], get_source_with_config(source["id"])
    
    def get(self, source_id: str, default=None) -> Optional[dict]:
        """Get source or return default."""
        try:
            return get_source_with_config(source_id)
        except KeyError:
            return default


# Singleton proxy instance for backward compatibility
# This allows code like: SOURCES[source_id]["config"]
SOURCES = SourcesProxy()
