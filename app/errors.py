"""
SetuPranali - Structured Error Handling

This module provides clear, actionable error responses for debugging.

ERROR DESIGN PRINCIPLES:
------------------------
1. Every error has a unique code for log searching
2. Messages are human-readable and actionable
3. Suggestions guide users to fix the issue
4. Documentation links provide more context
5. Request IDs enable cross-system tracing

ERROR RESPONSE FORMAT:
----------------------
{
    "error": {
        "code": "ERR_DATASET_NOT_FOUND",
        "message": "Dataset 'orders' not found in catalog",
        "details": {
            "dataset": "orders",
            "available_datasets": ["sales", "customers"]
        },
        "suggestion": "Check catalog.yaml for available datasets",
        "docs": "https://setupranali.github.io/guides/datasets/",
        "request_id": "abc-123"
    }
}
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCode(str, Enum):
    """Unique error codes for every error type."""
    
    # Authentication & Authorization (1xxx)
    ERR_API_KEY_MISSING = "ERR_1001"
    ERR_API_KEY_INVALID = "ERR_1002"
    ERR_API_KEY_EXPIRED = "ERR_1003"
    ERR_API_KEY_REVOKED = "ERR_1004"
    ERR_PERMISSION_DENIED = "ERR_1005"
    ERR_ADMIN_REQUIRED = "ERR_1006"
    
    # Dataset & Catalog (2xxx)
    ERR_DATASET_NOT_FOUND = "ERR_2001"
    ERR_DIMENSION_NOT_FOUND = "ERR_2002"
    ERR_METRIC_NOT_FOUND = "ERR_2003"
    ERR_CATALOG_LOAD_FAILED = "ERR_2004"
    ERR_CATALOG_INVALID = "ERR_2005"
    
    # Query Validation (3xxx)
    ERR_QUERY_INVALID = "ERR_3001"
    ERR_LIMIT_EXCEEDED = "ERR_3002"
    ERR_TOO_MANY_DIMENSIONS = "ERR_3003"
    ERR_TOO_MANY_METRICS = "ERR_3004"
    ERR_FILTER_TOO_DEEP = "ERR_3005"
    ERR_INVALID_FILTER = "ERR_3006"
    ERR_INVALID_SORT = "ERR_3007"
    ERR_SQL_UNSAFE = "ERR_3008"
    
    # Query Execution (4xxx)
    ERR_QUERY_TIMEOUT = "ERR_4001"
    ERR_QUERY_FAILED = "ERR_4002"
    ERR_CONNECTION_FAILED = "ERR_4003"
    ERR_SOURCE_NOT_FOUND = "ERR_4004"
    ERR_ADAPTER_ERROR = "ERR_4005"
    
    # Data Source (5xxx)
    ERR_SOURCE_INVALID = "ERR_5001"
    ERR_SOURCE_DUPLICATE = "ERR_5002"
    ERR_SOURCE_CONFIG_INVALID = "ERR_5003"
    ERR_ENCRYPTION_FAILED = "ERR_5004"
    ERR_DECRYPTION_FAILED = "ERR_5005"
    
    # Rate Limiting (6xxx)
    ERR_RATE_LIMITED = "ERR_6001"
    ERR_QUOTA_EXCEEDED = "ERR_6002"
    
    # RLS (7xxx)
    ERR_RLS_CONFIG_INVALID = "ERR_7001"
    ERR_RLS_TENANT_MISSING = "ERR_7002"
    ERR_RLS_COLUMN_NOT_FOUND = "ERR_7003"
    
    # NLQ (8xxx)
    ERR_NLQ_PROVIDER_MISSING = "ERR_8001"
    ERR_NLQ_TRANSLATION_FAILED = "ERR_8002"
    ERR_NLQ_API_KEY_MISSING = "ERR_8003"
    
    # Internal (9xxx)
    ERR_INTERNAL = "ERR_9001"
    ERR_NOT_IMPLEMENTED = "ERR_9002"
    ERR_SERVICE_UNAVAILABLE = "ERR_9003"


# =============================================================================
# DOCUMENTATION LINKS
# =============================================================================

DOCS_BASE = "https://setupranali.github.io"

ERROR_DOCS = {
    ErrorCode.ERR_API_KEY_MISSING: f"{DOCS_BASE}/api-reference/authentication/",
    ErrorCode.ERR_API_KEY_INVALID: f"{DOCS_BASE}/api-reference/authentication/",
    ErrorCode.ERR_DATASET_NOT_FOUND: f"{DOCS_BASE}/guides/datasets/",
    ErrorCode.ERR_DIMENSION_NOT_FOUND: f"{DOCS_BASE}/guides/datasets/#dimensions",
    ErrorCode.ERR_METRIC_NOT_FOUND: f"{DOCS_BASE}/guides/datasets/#metrics",
    ErrorCode.ERR_QUERY_INVALID: f"{DOCS_BASE}/api-reference/query/",
    ErrorCode.ERR_LIMIT_EXCEEDED: f"{DOCS_BASE}/concepts/rate-limiting/",
    ErrorCode.ERR_TOO_MANY_DIMENSIONS: f"{DOCS_BASE}/concepts/rate-limiting/",
    ErrorCode.ERR_TOO_MANY_METRICS: f"{DOCS_BASE}/concepts/rate-limiting/",
    ErrorCode.ERR_SOURCE_NOT_FOUND: f"{DOCS_BASE}/api-reference/sources/",
    ErrorCode.ERR_SOURCE_CONFIG_INVALID: f"{DOCS_BASE}/integrations/sources/",
    ErrorCode.ERR_RLS_CONFIG_INVALID: f"{DOCS_BASE}/guides/rls/",
    ErrorCode.ERR_NLQ_PROVIDER_MISSING: f"{DOCS_BASE}/api-reference/nlq/",
    ErrorCode.ERR_RATE_LIMITED: f"{DOCS_BASE}/concepts/rate-limiting/",
    ErrorCode.ERR_SQL_UNSAFE: f"{DOCS_BASE}/api-reference/sql/",
}


# =============================================================================
# ERROR RESPONSE
# =============================================================================

@dataclass
class SetuPranaliError(Exception):
    """
    Structured error with all context needed for debugging.
    
    Attributes:
        code: Unique error code for searching logs
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional context (dict)
        suggestion: How to fix the issue
        request_id: Request tracing ID
    """
    code: ErrorCode
    message: str
    status_code: int = 400
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: Optional[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        error_dict = {
            "code": self.code.value,
            "message": self.message,
        }
        
        if self.details:
            error_dict["details"] = self.details
        
        if self.suggestion:
            error_dict["suggestion"] = self.suggestion
        
        # Add documentation link if available
        docs_url = ERROR_DOCS.get(self.code)
        if docs_url:
            error_dict["docs"] = docs_url
        
        if self.request_id:
            error_dict["request_id"] = self.request_id
        
        error_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return {"error": error_dict}
    
    def to_response(self) -> JSONResponse:
        """Convert to FastAPI JSONResponse."""
        return JSONResponse(
            status_code=self.status_code,
            content=self.to_dict()
        )
    
    def log(self, level: str = "error"):
        """Log the error with context."""
        log_msg = f"[{self.code.value}] {self.message}"
        if self.details:
            log_msg += f" | details={self.details}"
        if self.request_id:
            log_msg += f" | request_id={self.request_id}"
        
        getattr(logger, level)(log_msg)


# =============================================================================
# ERROR FACTORY FUNCTIONS
# =============================================================================

def dataset_not_found(
    dataset: str,
    available_datasets: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create dataset not found error with helpful context."""
    details = {"dataset": dataset}
    
    if available_datasets:
        # Show up to 10 available datasets
        details["available_datasets"] = available_datasets[:10]
        if len(available_datasets) > 10:
            details["total_available"] = len(available_datasets)
    
    suggestion = f"Check that '{dataset}' is defined in catalog.yaml"
    if available_datasets:
        # Suggest similar datasets
        similar = [d for d in available_datasets if dataset.lower() in d.lower()]
        if similar:
            suggestion += f". Did you mean: {', '.join(similar[:3])}?"
    
    return SetuPranaliError(
        code=ErrorCode.ERR_DATASET_NOT_FOUND,
        message=f"Dataset '{dataset}' not found",
        status_code=404,
        details=details,
        suggestion=suggestion,
        request_id=request_id
    )


def dimension_not_found(
    dimension: str,
    dataset: str,
    available_dimensions: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create dimension not found error."""
    details = {"dimension": dimension, "dataset": dataset}
    
    if available_dimensions:
        details["available_dimensions"] = available_dimensions[:10]
    
    suggestion = f"Check dimensions in dataset '{dataset}' in catalog.yaml"
    if available_dimensions:
        similar = [d for d in available_dimensions if dimension.lower() in d.lower()]
        if similar:
            suggestion += f". Did you mean: {', '.join(similar[:3])}?"
    
    return SetuPranaliError(
        code=ErrorCode.ERR_DIMENSION_NOT_FOUND,
        message=f"Dimension '{dimension}' not found in dataset '{dataset}'",
        status_code=400,
        details=details,
        suggestion=suggestion,
        request_id=request_id
    )


def metric_not_found(
    metric: str,
    dataset: str,
    available_metrics: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create metric not found error."""
    details = {"metric": metric, "dataset": dataset}
    
    if available_metrics:
        details["available_metrics"] = available_metrics[:10]
    
    suggestion = f"Check metrics in dataset '{dataset}' in catalog.yaml"
    if available_metrics:
        similar = [m for m in available_metrics if metric.lower() in m.lower()]
        if similar:
            suggestion += f". Did you mean: {', '.join(similar[:3])}?"
    
    return SetuPranaliError(
        code=ErrorCode.ERR_METRIC_NOT_FOUND,
        message=f"Metric '{metric}' not found in dataset '{dataset}'",
        status_code=400,
        details=details,
        suggestion=suggestion,
        request_id=request_id
    )


def api_key_missing(request_id: Optional[str] = None) -> SetuPranaliError:
    """Create API key missing error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_API_KEY_MISSING,
        message="API key is required",
        status_code=401,
        details={"header": "X-API-Key"},
        suggestion="Add 'X-API-Key: your-api-key' header to your request",
        request_id=request_id
    )


def api_key_invalid(key_prefix: Optional[str] = None, request_id: Optional[str] = None) -> SetuPranaliError:
    """Create API key invalid error."""
    details = {}
    if key_prefix:
        details["key_prefix"] = key_prefix[:8] + "..."
    
    return SetuPranaliError(
        code=ErrorCode.ERR_API_KEY_INVALID,
        message="API key is invalid or expired",
        status_code=401,
        details=details,
        suggestion="Check that your API key is correct and not expired. Contact your admin for a new key.",
        request_id=request_id
    )


def permission_denied(
    action: str,
    resource: str,
    required_role: Optional[str] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create permission denied error."""
    details = {"action": action, "resource": resource}
    if required_role:
        details["required_role"] = required_role
    
    return SetuPranaliError(
        code=ErrorCode.ERR_PERMISSION_DENIED,
        message=f"Permission denied for {action} on {resource}",
        status_code=403,
        details=details,
        suggestion=f"You need {required_role or 'higher'} role to perform this action",
        request_id=request_id
    )


def query_validation_error(
    message: str,
    field: Optional[str] = None,
    limit: Optional[Any] = None,
    actual: Optional[Any] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create query validation error."""
    details = {}
    if field:
        details["field"] = field
    if limit is not None:
        details["limit"] = limit
    if actual is not None:
        details["actual"] = actual
    
    return SetuPranaliError(
        code=ErrorCode.ERR_QUERY_INVALID,
        message=message,
        status_code=400,
        details=details,
        suggestion="Check your query parameters against the API documentation",
        request_id=request_id
    )


def too_many_dimensions(
    count: int,
    limit: int,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create too many dimensions error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_TOO_MANY_DIMENSIONS,
        message=f"Too many dimensions: {count} exceeds limit of {limit}",
        status_code=400,
        details={"actual": count, "limit": limit},
        suggestion="Reduce the number of dimensions in your query. Consider filtering or aggregating differently.",
        request_id=request_id
    )


def too_many_metrics(
    count: int,
    limit: int,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create too many metrics error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_TOO_MANY_METRICS,
        message=f"Too many metrics: {count} exceeds limit of {limit}",
        status_code=400,
        details={"actual": count, "limit": limit},
        suggestion="Reduce the number of metrics in your query. Consider splitting into multiple queries.",
        request_id=request_id
    )


def filter_too_deep(
    depth: int,
    limit: int,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create filter too deep error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_FILTER_TOO_DEEP,
        message=f"Filter nesting too deep: depth {depth} exceeds limit of {limit}",
        status_code=400,
        details={"actual": depth, "limit": limit},
        suggestion="Simplify your filter by flattening nested AND/OR conditions",
        request_id=request_id
    )


def query_timeout(
    timeout_seconds: int,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create query timeout error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_QUERY_TIMEOUT,
        message=f"Query exceeded {timeout_seconds} second timeout",
        status_code=504,
        details={"timeout_seconds": timeout_seconds},
        suggestion="Add filters to reduce data volume, or request fewer dimensions/metrics",
        request_id=request_id
    )


def connection_failed(
    source: str,
    reason: str,
    engine: Optional[str] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create connection failed error."""
    details = {"source": source, "reason": reason}
    if engine:
        details["engine"] = engine
    
    return SetuPranaliError(
        code=ErrorCode.ERR_CONNECTION_FAILED,
        message=f"Failed to connect to data source '{source}'",
        status_code=503,
        details=details,
        suggestion="Check source credentials and network connectivity. Verify the source is accessible from the server.",
        request_id=request_id
    )


def source_not_found(
    source: str,
    available_sources: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create source not found error."""
    details = {"source": source}
    if available_sources:
        details["available_sources"] = available_sources
    
    return SetuPranaliError(
        code=ErrorCode.ERR_SOURCE_NOT_FOUND,
        message=f"Data source '{source}' not found",
        status_code=404,
        details=details,
        suggestion="Register the source using POST /v1/sources first",
        request_id=request_id
    )


def sql_unsafe(
    reason: str,
    pattern: Optional[str] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create SQL unsafe error."""
    details = {"reason": reason}
    if pattern:
        details["blocked_pattern"] = pattern
    
    return SetuPranaliError(
        code=ErrorCode.ERR_SQL_UNSAFE,
        message="SQL query contains disallowed operations",
        status_code=400,
        details=details,
        suggestion="Only SELECT queries are allowed. DDL, DML, and administrative commands are blocked.",
        request_id=request_id
    )


def rate_limited(
    retry_after: int,
    limit: Optional[str] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create rate limited error."""
    details = {"retry_after_seconds": retry_after}
    if limit:
        details["limit"] = limit
    
    return SetuPranaliError(
        code=ErrorCode.ERR_RATE_LIMITED,
        message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
        status_code=429,
        details=details,
        suggestion="Reduce query frequency or contact admin to increase your rate limit",
        request_id=request_id
    )


def rls_config_invalid(
    dataset: str,
    reason: str,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create RLS config invalid error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_RLS_CONFIG_INVALID,
        message=f"Invalid RLS configuration for dataset '{dataset}'",
        status_code=500,
        details={"dataset": dataset, "reason": reason},
        suggestion="Check the 'rls' section in your dataset configuration in catalog.yaml",
        request_id=request_id
    )


def nlq_provider_missing(
    provider: str,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create NLQ provider missing error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_NLQ_PROVIDER_MISSING,
        message=f"NLQ provider '{provider}' is not configured",
        status_code=400,
        details={
            "provider": provider,
            "supported_providers": ["openai", "anthropic"]
        },
        suggestion=f"Set the appropriate API key environment variable for {provider}",
        request_id=request_id
    )


def nlq_translation_failed(
    reason: str,
    provider: Optional[str] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create NLQ translation failed error."""
    details = {"reason": reason}
    if provider:
        details["provider"] = provider
    
    return SetuPranaliError(
        code=ErrorCode.ERR_NLQ_TRANSLATION_FAILED,
        message="Failed to translate natural language query",
        status_code=400,
        details=details,
        suggestion="Try rephrasing your question with more specific terms",
        request_id=request_id
    )


def internal_error(
    message: str = "An unexpected error occurred",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create internal error - use sparingly, prefer specific errors."""
    return SetuPranaliError(
        code=ErrorCode.ERR_INTERNAL,
        message=message,
        status_code=500,
        details=details or {},
        suggestion="If this persists, please report at https://github.com/setupranali/setupranali.github.io/issues",
        request_id=request_id
    )


def decryption_failed(
    source: str,
    request_id: Optional[str] = None
) -> SetuPranaliError:
    """Create decryption failed error."""
    return SetuPranaliError(
        code=ErrorCode.ERR_DECRYPTION_FAILED,
        message=f"Failed to decrypt credentials for source '{source}'",
        status_code=500,
        details={"source": source},
        suggestion="The encryption key (UBI_SECRET_KEY) may have changed. Re-register the source with current credentials.",
        request_id=request_id
    )


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

async def setupranali_error_handler(request: Request, exc: SetuPranaliError) -> JSONResponse:
    """Handle SetuPranaliError and return structured response."""
    # Add request ID if available
    if not exc.request_id:
        exc.request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())[:8]
    
    # Log the error
    exc.log()
    
    return exc.to_response()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException and convert to structured format."""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())[:8]
    
    # Convert to structured format
    error_response = {
        "error": {
            "code": f"ERR_HTTP_{exc.status_code}",
            "message": str(exc.detail) if isinstance(exc.detail, str) else exc.detail.get("message", str(exc.detail)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id
        }
    }
    
    # If detail is already structured, merge it
    if isinstance(exc.detail, dict):
        error_response["error"]["details"] = {
            k: v for k, v in exc.detail.items() 
            if k not in ("message", "error")
        }
    
    logger.error(f"[ERR_HTTP_{exc.status_code}] {exc.detail} | request_id={request_id}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())[:8]
    
    # Log full traceback for debugging
    logger.exception(f"Unhandled exception | request_id={request_id}")
    
    error = internal_error(
        message="An unexpected error occurred",
        details={"exception_type": type(exc).__name__},
        request_id=request_id
    )
    
    return error.to_response()


# =============================================================================
# HELPER TO INSTALL HANDLERS
# =============================================================================

def install_error_handlers(app):
    """Install error handlers on FastAPI app."""
    from fastapi import HTTPException as FastAPIHTTPException
    
    app.add_exception_handler(SetuPranaliError, setupranali_error_handler)
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Structured error handlers installed")

