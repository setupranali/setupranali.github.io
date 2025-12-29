"""
API Key Authentication & Lifecycle Management for SetuPranali

This module provides:
1. API key authentication for protected endpoints
2. Key lifecycle management (active/revoked status)
3. Usage tracking (last_used_at)
4. Tenant context extraction for RLS

WHY API KEY AUTH?
-----------------
1. BI tools (Power BI, Tableau) have limited auth options
2. API keys work well with HTTP header-based auth
3. Simple to implement and debug
4. No complex token refresh flows needed for read-only analytics

HOW BI TOOLS PASS API KEYS:
---------------------------
- Power BI (OData Feed):
  1. Get Data → OData Feed
  2. Enter URL: http://your-server/v1/odata
  3. Click "Advanced"
  4. Add HTTP Header: X-API-Key = your-key

- Tableau (Web Data Connector):
  1. WDC passes header via fetch() calls
  2. X-API-Key header added to all API requests

- Direct API (curl/Postman):
  curl -H "X-API-Key: dev-key-123" http://localhost:8080/v1/query

SECURITY BEST PRACTICES:
------------------------
- Never log raw API keys
- Track usage for audit trails
- Support key revocation
- Use HTTPS in production
- Rotate keys periodically
"""

import os
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel

from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)


# =============================================================================
# API KEY MODEL
# =============================================================================

class APIKeyRecord(BaseModel):
    """
    API Key record with lifecycle fields.
    
    Attributes:
        key_id: Unique identifier (NOT the key itself)
        tenant: Tenant this key belongs to
        role: Role (admin/viewer)
        name: Human-readable name
        status: active or revoked
        created_at: When key was created
        last_used_at: Last successful authentication
    """
    key_id: str
    tenant: str
    role: str
    name: str
    status: str = "active"  # active | revoked
    created_at: datetime = None
    last_used_at: Optional[datetime] = None
    
    def is_active(self) -> bool:
        return self.status == "active"


# =============================================================================
# API KEY REGISTRY
# =============================================================================
# In production, this would be stored in a database with encrypted keys.
# For now, we use an in-memory registry with lifecycle support.

def _generate_key_id(key: str) -> str:
    """Generate a safe key ID from the raw key (for logging/display)."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


# Static registry - in production, load from database
_API_KEY_REGISTRY: Dict[str, APIKeyRecord] = {}


def _init_registry():
    """Initialize the API key registry with default keys."""
    global _API_KEY_REGISTRY
    
    default_keys = {
        # Admin key - bypasses RLS (sees all data)
        "dev-key-123": APIKeyRecord(
            key_id=_generate_key_id("dev-key-123"),
            tenant="default",
            role="admin",
            name="Development Key (Admin)",
            status="active",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ),
        # Viewer key for default tenant - subject to RLS
        "readonly-key-456": APIKeyRecord(
            key_id=_generate_key_id("readonly-key-456"),
            tenant="default",
            role="viewer",
            name="Read-Only Key (Default Tenant)",
            status="active",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ),
        # Tenant A viewer - only sees tenantA data
        "tenantA-key": APIKeyRecord(
            key_id=_generate_key_id("tenantA-key"),
            tenant="tenantA",
            role="viewer",
            name="Tenant A Viewer",
            status="active",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ),
        # Tenant B viewer - only sees tenantB data
        "tenantB-key": APIKeyRecord(
            key_id=_generate_key_id("tenantB-key"),
            tenant="tenantB",
            role="viewer",
            name="Tenant B Viewer",
            status="active",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ),
        # Tenant A admin - bypasses RLS
        "tenantA-admin-key": APIKeyRecord(
            key_id=_generate_key_id("tenantA-admin-key"),
            tenant="tenantA",
            role="admin",
            name="Tenant A Admin",
            status="active",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ),
        # Internal admin key for /internal/* endpoints
        "internal-admin-key": APIKeyRecord(
            key_id=_generate_key_id("internal-admin-key"),
            tenant="system",
            role="internal_admin",
            name="Internal Admin Key",
            status="active",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        ),
        # Example revoked key (for testing)
        "revoked-key-999": APIKeyRecord(
            key_id=_generate_key_id("revoked-key-999"),
            tenant="default",
            role="viewer",
            name="Revoked Test Key",
            status="revoked",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        )
    }
    
    _API_KEY_REGISTRY = default_keys


# Initialize on module load
_init_registry()


# =============================================================================
# KEY MANAGEMENT FUNCTIONS
# =============================================================================

def get_key_record(api_key: str) -> Optional[APIKeyRecord]:
    """Get API key record (without exposing the key itself)."""
    return _API_KEY_REGISTRY.get(api_key)


def update_last_used(api_key: str):
    """Update last_used_at timestamp for a key."""
    record = _API_KEY_REGISTRY.get(api_key)
    if record:
        record.last_used_at = datetime.now(timezone.utc)


def revoke_key(api_key: str) -> bool:
    """Revoke an API key."""
    record = _API_KEY_REGISTRY.get(api_key)
    if record:
        record.status = "revoked"
        logger.info(f"API key revoked: {record.key_id}")
        return True
    return False


def list_keys_for_tenant(tenant: str) -> list:
    """List all keys for a tenant (without exposing raw keys)."""
    return [
        {
            "key_id": record.key_id,
            "name": record.name,
            "role": record.role,
            "status": record.status,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None
        }
        for record in _API_KEY_REGISTRY.values()
        if record.tenant == tenant
    ]


# =============================================================================
# TENANT CONTEXT
# =============================================================================

class TenantContext(BaseModel):
    """
    Context returned after successful authentication.
    
    Contains tenant and role information for downstream use:
    - RLS filter injection
    - Cache key scoping
    - Audit logging
    """
    tenant: str
    role: str
    key_name: str
    key_id: str = ""
    
    def is_admin(self) -> bool:
        """Check if this context has admin privileges."""
        return self.role in ("admin", "internal_admin")
    
    def is_internal_admin(self) -> bool:
        """Check if this is an internal admin (for /internal/* endpoints)."""
        return self.role == "internal_admin"


# =============================================================================
# API KEY HEADER SCHEME
# =============================================================================

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # We handle errors ourselves for clearer messages
    description="API key for authentication. Contact admin to get a key."
)


# =============================================================================
# AUTHENTICATION DEPENDENCY
# =============================================================================

async def require_api_key(
    api_key: Optional[str] = Security(api_key_header),
    request: Request = None
) -> TenantContext:
    """
    FastAPI dependency that validates API key and returns tenant context.
    
    Checks:
    1. API key header present
    2. Key exists in registry
    3. Key is not revoked
    
    Usage:
        @app.get("/protected")
        def protected_route(ctx: TenantContext = Depends(require_api_key)):
            return {"tenant": ctx.tenant}
    
    Returns:
        TenantContext with tenant and role information
    
    Raises:
        HTTPException 401: If X-API-Key header is missing
        HTTPException 403: If API key is invalid or revoked
    """
    
    # Check if API key header is present
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "Missing X-API-Key header",
                "hint": "Add header: X-API-Key: <your-api-key>"
            }
        )
    
    # Look up key in registry
    record = get_key_record(api_key)
    
    if not record:
        # SECURITY: Never log the actual key
        logger.warning(f"Invalid API key attempted from {request.client.host if request else 'unknown'}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invalid_api_key",
                "message": "The provided API key is invalid",
                "hint": "Check your API key or contact admin for a valid key"
            }
        )
    
    # Check if key is revoked
    if not record.is_active():
        logger.warning(f"Revoked API key used: {record.key_id}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "api_key_revoked",
                "message": "This API key has been revoked",
                "hint": "Contact admin for a new API key"
            }
        )
    
    # Update last used timestamp
    update_last_used(api_key)
    
    # Return tenant context for downstream use
    return TenantContext(
        tenant=record.tenant,
        role=record.role,
        key_name=record.name,
        key_id=record.key_id
    )


# =============================================================================
# ADMIN-ONLY DEPENDENCY
# =============================================================================

async def require_internal_admin(
    ctx: TenantContext = Security(require_api_key)
) -> TenantContext:
    """
    Require internal admin role for sensitive endpoints.
    
    Used for:
    - /internal/status
    - Key management
    - System administration
    """
    if not ctx.is_internal_admin():
        raise HTTPException(
            status_code=403,
            detail={
                "error": "admin_required",
                "message": "This endpoint requires internal admin access",
                "hint": "Use an internal admin API key"
            }
        )
    return ctx


# =============================================================================
# OPTIONAL AUTH DEPENDENCY
# =============================================================================

async def optional_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[TenantContext]:
    """
    Optional authentication - returns context if key provided, None otherwise.
    
    Useful for endpoints that have different behavior for authenticated
    vs anonymous users (e.g., health check shows more details to admins).
    """
    if not api_key:
        return None
    
    record = get_key_record(api_key)
    if not record or not record.is_active():
        return None
    
    update_last_used(api_key)
    
    return TenantContext(
        tenant=record.tenant,
        role=record.role,
        key_name=record.name,
        key_id=record.key_id
    )


# =============================================================================
# SECURITY STATUS
# =============================================================================

def get_security_status() -> dict:
    """Get security module status for health checks."""
    return {
        "total_keys": len(_API_KEY_REGISTRY),
        "active_keys": sum(1 for r in _API_KEY_REGISTRY.values() if r.is_active()),
        "revoked_keys": sum(1 for r in _API_KEY_REGISTRY.values() if not r.is_active())
    }
