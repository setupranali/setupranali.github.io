"""
Rate Limiting for SetuPranali

This module provides request rate limiting to protect against abuse and ensure
fair resource allocation across tenants.

WHY RATE LIMITING?
------------------
1. Prevent abuse (intentional or accidental)
2. Protect backend resources from BI refresh storms
3. Ensure fair access across tenants
4. Meet SaaS operational requirements

RATE LIMIT STRATEGY:
--------------------
- Limits are per API key (not per IP)
- Different limits for different endpoint groups
- Graceful degradation if Redis unavailable
- BI-friendly JSON error responses

DEFAULT LIMITS:
---------------
- /v1/query: 60 req/min (semantic queries are expensive)
- /v1/odata/*: 120 req/min (lighter metadata requests)
- /v1/sources/*: 30 req/min (admin operations)

CONFIGURATION:
--------------
Set via environment variables:
- RATE_LIMIT_ENABLED: Enable/disable (default: true)
- RATE_LIMIT_QUERY: Limit for /v1/query (default: 60/minute)
- RATE_LIMIT_ODATA: Limit for /v1/odata/* (default: 120/minute)
- RATE_LIMIT_SOURCES: Limit for /v1/sources/* (default: 30/minute)
"""

import os
import logging
from typing import Optional, Callable
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

# slowapi for rate limiting
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    Limiter = None

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class RateLimitConfig:
    """Rate limit configuration loaded from environment."""
    
    def __init__(self):
        self.enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.query_limit = os.environ.get("RATE_LIMIT_QUERY", "60/minute")
        self.odata_limit = os.environ.get("RATE_LIMIT_ODATA", "120/minute")
        self.sources_limit = os.environ.get("RATE_LIMIT_SOURCES", "30/minute")
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


_config: Optional[RateLimitConfig] = None


def get_rate_limit_config() -> RateLimitConfig:
    """Get or create rate limit configuration."""
    global _config
    if _config is None:
        _config = RateLimitConfig()
    return _config


# =============================================================================
# KEY FUNCTION
# =============================================================================
# Rate limits are per API key, not per IP address.
# This ensures fair distribution across authenticated users.

def get_api_key_from_request(request: Request) -> str:
    """
    Extract API key from request for rate limiting.
    
    Falls back to IP address if no API key present.
    This ensures unauthenticated requests are also limited.
    """
    api_key = request.headers.get("X-API-Key")
    
    if api_key:
        # Use first 8 chars of key for privacy in logs
        # Full key is used internally for accurate limiting
        return f"key:{api_key}"
    
    # Fall back to IP for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


# =============================================================================
# LIMITER INITIALIZATION
# =============================================================================

_limiter: Optional["Limiter"] = None
_limiter_initialized: bool = False


def get_limiter() -> Optional["Limiter"]:
    """
    Get or create the rate limiter.
    
    Returns None if:
    - slowapi not installed
    - Rate limiting disabled
    - Redis unavailable (graceful degradation)
    """
    global _limiter, _limiter_initialized
    
    if _limiter_initialized:
        return _limiter
    
    _limiter_initialized = True
    config = get_rate_limit_config()
    
    if not config.enabled:
        logger.info("Rate limiting disabled by configuration")
        return None
    
    if not SLOWAPI_AVAILABLE:
        logger.warning("slowapi not installed. Rate limiting disabled. pip install slowapi")
        return None
    
    try:
        # Try to use Redis for distributed rate limiting
        # Falls back to in-memory if Redis unavailable
        from slowapi.middleware import SlowAPIMiddleware
        
        _limiter = Limiter(
            key_func=get_api_key_from_request,
            storage_uri=config.redis_url,
            strategy="fixed-window",  # Simple and predictable
            default_limits=["200/minute"]  # Global fallback
        )
        
        logger.info(f"Rate limiter initialized with Redis: {config.redis_url}")
        return _limiter
        
    except Exception as e:
        logger.warning(f"Rate limiter initialization failed: {e}. Using in-memory fallback.")
        
        try:
            # In-memory fallback
            _limiter = Limiter(
                key_func=get_api_key_from_request,
                strategy="fixed-window"
            )
            return _limiter
        except Exception as e2:
            logger.error(f"In-memory rate limiter failed: {e2}. Rate limiting disabled.")
            return None


# =============================================================================
# RATE LIMIT EXCEEDED HANDLER
# =============================================================================

def rate_limit_exceeded_handler(request: Request, exc: "RateLimitExceeded") -> JSONResponse:
    """
    Handle rate limit exceeded errors.
    
    Returns a BI-friendly JSON response with:
    - Clear error message
    - Retry-After header
    - No HTML or redirects
    """
    # Extract retry time from exception
    retry_after = getattr(exc, 'retry_after', 60)
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. Please retry after {retry_after} seconds.",
            "detail": str(exc.detail) if hasattr(exc, 'detail') else "Rate limit exceeded",
            "retry_after": retry_after
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Reset": str(int(datetime.now(timezone.utc).timestamp()) + retry_after)
        }
    )


# =============================================================================
# RATE LIMIT DECORATORS
# =============================================================================
# These are used to apply different limits to different endpoints.

def limit_query(func: Callable) -> Callable:
    """Apply query rate limit (60/minute by default)."""
    limiter = get_limiter()
    if limiter is None:
        return func
    
    config = get_rate_limit_config()
    return limiter.limit(config.query_limit)(func)


def limit_odata(func: Callable) -> Callable:
    """Apply OData rate limit (120/minute by default)."""
    limiter = get_limiter()
    if limiter is None:
        return func
    
    config = get_rate_limit_config()
    return limiter.limit(config.odata_limit)(func)


def limit_sources(func: Callable) -> Callable:
    """Apply sources rate limit (30/minute by default)."""
    limiter = get_limiter()
    if limiter is None:
        return func
    
    config = get_rate_limit_config()
    return limiter.limit(config.sources_limit)(func)


# =============================================================================
# MIDDLEWARE SETUP
# =============================================================================

def setup_rate_limiting(app):
    """
    Setup rate limiting middleware on FastAPI app.
    
    Call this during app initialization:
        from app.rate_limit import setup_rate_limiting
        setup_rate_limiting(app)
    """
    limiter = get_limiter()
    
    if limiter is None:
        logger.info("Rate limiting not available")
        return
    
    if SLOWAPI_AVAILABLE:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
        
        logger.info("Rate limiting middleware configured")


# =============================================================================
# STATUS CHECK
# =============================================================================

def get_rate_limit_status() -> dict:
    """Get rate limiter status for health checks."""
    config = get_rate_limit_config()
    limiter = get_limiter()
    
    return {
        "enabled": config.enabled and limiter is not None,
        "slowapi_available": SLOWAPI_AVAILABLE,
        "limits": {
            "query": config.query_limit,
            "odata": config.odata_limit,
            "sources": config.sources_limit
        }
    }

