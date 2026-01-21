"""
FastAPI Dependencies

Reusable dependencies for dependency injection.
"""

from fastapi import Depends, Header, HTTPException
from typing import Optional

from app.core.security import require_api_key, TenantContext
from app.core.config import settings


def get_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """Extract API key from header."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header."
        )
    return x_api_key


def get_tenant_context(
    api_key: str = Depends(get_api_key)
) -> TenantContext:
    """Get tenant context from API key."""
    return require_api_key(api_key)
