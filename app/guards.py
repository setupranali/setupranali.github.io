"""
Request Safety Guards for SetuPranali

This module provides safety guards to prevent:
1. Excessive resource consumption
2. Runaway queries
3. Malformed requests that could crash the system

WHY SAFETY GUARDS?
------------------
BI tools can generate unexpected query patterns:
- Power BI may request millions of rows
- Tableau may send deeply nested filters
- Users may accidentally create cartesian products

These guards protect the platform without breaking BI tool compatibility.

GUARD PHILOSOPHY:
-----------------
- Fail with clear, actionable error messages
- Return HTTP 400 (not 500) for validation failures
- Don't silently truncate - inform the user
- Guards are configurable via environment

DEFAULT LIMITS:
---------------
- QUERY_MAX_ROWS: 100,000 (prevent memory exhaustion)
- QUERY_MAX_DIMENSIONS: 20 (prevent wide result sets)
- QUERY_MAX_METRICS: 50 (prevent excessive aggregation)
- QUERY_MAX_FILTER_DEPTH: 10 (prevent deeply nested filters)
- QUERY_TIMEOUT_SECONDS: 30 (prevent hanging connections)
"""

import os
import logging
import signal
from typing import Optional, Dict, Any, List
from functools import wraps
from contextlib import contextmanager

from fastapi import HTTPException

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class SafetyConfig:
    """Safety guard configuration loaded from environment."""
    
    def __init__(self):
        self.max_rows = int(os.environ.get("QUERY_MAX_ROWS", "100000"))
        self.max_dimensions = int(os.environ.get("QUERY_MAX_DIMENSIONS", "20"))
        self.max_metrics = int(os.environ.get("QUERY_MAX_METRICS", "50"))
        self.max_filter_depth = int(os.environ.get("QUERY_MAX_FILTER_DEPTH", "10"))
        self.timeout_seconds = int(os.environ.get("QUERY_TIMEOUT_SECONDS", "30"))
        self.enabled = os.environ.get("SAFETY_GUARDS_ENABLED", "true").lower() == "true"


_config: Optional[SafetyConfig] = None


def get_safety_config() -> SafetyConfig:
    """Get or create safety configuration."""
    global _config
    if _config is None:
        _config = SafetyConfig()
    return _config


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class QueryValidationError(Exception):
    """Raised when a query fails validation."""
    
    def __init__(self, message: str, field: str = None, limit: Any = None, actual: Any = None):
        self.message = message
        self.field = field
        self.limit = limit
        self.actual = actual
        super().__init__(message)
    
    def to_dict(self) -> dict:
        return {
            "error": "query_validation_failed",
            "message": self.message,
            "field": self.field,
            "limit": self.limit,
            "actual": self.actual
        }


# =============================================================================
# LIMIT VALIDATION
# =============================================================================

def validate_limit(limit: int) -> int:
    """
    Validate and cap the row limit.
    
    - If limit exceeds max, cap to max and warn
    - Never allow more than configured maximum
    """
    config = get_safety_config()
    
    if not config.enabled:
        return limit
    
    if limit > config.max_rows:
        logger.warning(f"Query limit {limit} exceeds max {config.max_rows}, capping")
        return config.max_rows
    
    if limit < 1:
        return 1
    
    return limit


def validate_dimensions(dimensions: List[Any]) -> None:
    """
    Validate number of dimensions.
    
    Too many dimensions can cause:
    - Wide result sets
    - Memory issues
    - Slow GROUP BY operations
    """
    config = get_safety_config()
    
    if not config.enabled:
        return
    
    if len(dimensions) > config.max_dimensions:
        raise QueryValidationError(
            f"Too many dimensions: {len(dimensions)} exceeds limit of {config.max_dimensions}",
            field="dimensions",
            limit=config.max_dimensions,
            actual=len(dimensions)
        )


def validate_metrics(metrics: List[Any]) -> None:
    """
    Validate number of metrics.
    
    Too many metrics can cause:
    - Expensive aggregation
    - Complex SQL generation
    """
    config = get_safety_config()
    
    if not config.enabled:
        return
    
    if len(metrics) > config.max_metrics:
        raise QueryValidationError(
            f"Too many metrics: {len(metrics)} exceeds limit of {config.max_metrics}",
            field="metrics",
            limit=config.max_metrics,
            actual=len(metrics)
        )


def validate_filter_depth(filters: Any, current_depth: int = 0) -> int:
    """
    Validate filter nesting depth.
    
    Deeply nested filters can cause:
    - Stack overflow
    - Exponential SQL complexity
    - DoS via crafted requests
    """
    config = get_safety_config()
    
    if not config.enabled:
        return current_depth
    
    if filters is None:
        return current_depth
    
    if current_depth > config.max_filter_depth:
        raise QueryValidationError(
            f"Filter too deeply nested: depth {current_depth} exceeds limit of {config.max_filter_depth}",
            field="filters",
            limit=config.max_filter_depth,
            actual=current_depth
        )
    
    # Convert Pydantic models to dict
    if hasattr(filters, 'model_dump'):
        filters = filters.model_dump(by_alias=True, exclude_none=True)
    
    if isinstance(filters, dict):
        # Check for AND/OR nesting
        if 'and' in filters:
            for sub_filter in filters['and']:
                validate_filter_depth(sub_filter, current_depth + 1)
        elif 'or' in filters:
            for sub_filter in filters['or']:
                validate_filter_depth(sub_filter, current_depth + 1)
        elif 'not' in filters:
            validate_filter_depth(filters['not'], current_depth + 1)
    
    return current_depth


# =============================================================================
# QUERY REQUEST VALIDATION
# =============================================================================

def validate_query_request(req: "QueryRequest") -> "QueryRequest":
    """
    Validate a complete query request.
    
    Checks:
    - Row limit within bounds
    - Dimension count within bounds
    - Metric count within bounds
    - Filter depth within bounds
    
    Returns the request with capped limit if valid.
    Raises QueryValidationError if invalid.
    """
    config = get_safety_config()
    
    if not config.enabled:
        return req
    
    try:
        # Validate and cap limit
        req.limit = validate_limit(req.limit)
        
        # Validate dimensions
        validate_dimensions(req.dimensions)
        
        # Validate metrics
        validate_metrics(req.metrics)
        
        # Validate filter depth
        validate_filter_depth(req.filters)
        
        return req
        
    except QueryValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        raise QueryValidationError(f"Request validation failed: {str(e)}")


def handle_validation_error(error: QueryValidationError) -> None:
    """Convert QueryValidationError to HTTPException."""
    raise HTTPException(
        status_code=400,
        detail=error.to_dict()
    )


# =============================================================================
# TIMEOUT PROTECTION
# =============================================================================

class QueryTimeout(Exception):
    """Raised when a query exceeds the timeout."""
    pass


@contextmanager
def query_timeout(seconds: Optional[int] = None):
    """
    Context manager for query timeout.
    
    Usage:
        with query_timeout(30):
            execute_expensive_query()
    
    Note: This uses signal.SIGALRM which only works on Unix.
    On Windows, this is a no-op.
    """
    config = get_safety_config()
    timeout = seconds or config.timeout_seconds
    
    if not config.enabled or timeout <= 0:
        yield
        return
    
    # Check if signal-based timeout is available (Unix only)
    if not hasattr(signal, 'SIGALRM'):
        logger.debug("Signal-based timeout not available (Windows?)")
        yield
        return
    
    def timeout_handler(signum, frame):
        raise QueryTimeout(f"Query exceeded {timeout} second timeout")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        yield
    finally:
        # Cancel the alarm and restore old handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# =============================================================================
# RESULT SIZE GUARD
# =============================================================================

def check_result_size(rows: List[Dict], warn_threshold: int = 50000) -> None:
    """
    Check result size and log warning if large.
    
    This doesn't fail the query, but helps with monitoring.
    """
    row_count = len(rows)
    
    if row_count >= warn_threshold:
        logger.warning(f"Large query result: {row_count} rows")


# =============================================================================
# SAFETY STATUS
# =============================================================================

def get_safety_status() -> dict:
    """Get safety guards status for health checks."""
    config = get_safety_config()
    
    return {
        "enabled": config.enabled,
        "limits": {
            "max_rows": config.max_rows,
            "max_dimensions": config.max_dimensions,
            "max_metrics": config.max_metrics,
            "max_filter_depth": config.max_filter_depth,
            "timeout_seconds": config.timeout_seconds
        }
    }

