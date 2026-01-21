"""
SetuPranali - Main Application

A semantic analytics layer for BI tools (Power BI, Tableau).

PRODUCTION FEATURES:
--------------------
- API Key Authentication with lifecycle management
- Row-Level Security (automatic tenant isolation)
- Query Caching (Redis-based with graceful fallback)
- Rate Limiting (per API key)
- Safety Guards (limit validation, timeout protection)
- Structured Logging (request tracing)
"""

import os
import uuid
import time
import logging
from typing import Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, try to load .env manually
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

import duckdb
from fastapi import FastAPI, HTTPException, Depends, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.sources.catalog import load_catalog, get_dataset
from app.shared.types.models import QueryRequest, QueryResponse, ResultColumn
from app.domain.sources.manager import (
    register_source, list_sources, get_source, get_source_with_config,
    init_database as init_sources_db
)
from app.connection_manager import get_engine_and_conn
from app.infrastructure.adapters.duckdb_adapter import get_shared_duckdb
from app.odata import router as odata_router
from app.graphql_api import graphql_router
from app.advanced_routes import router as advanced_router
from app.ecosystem.routes import router as ecosystem_router
from app.enterprise.routes import router as enterprise_router
from app.domain.modeling.modeling.routes import router as modeling_router
from app.api.v1.analytics import router as analytics_router
from app.core.security import require_api_key, require_internal_admin, TenantContext
from app.shared.utils.crypto import is_encryption_configured
from app.rate_limit import limit_query, limit_odata, limit_sources
from app.shared.exceptions.errors import (
    install_error_handlers,
    dataset_not_found,
    dimension_not_found,
    metric_not_found,
    source_not_found,
    connection_failed,
    sql_unsafe,
    query_timeout,
    nlq_provider_missing,
    nlq_translation_failed,
    internal_error,
    decryption_failed,
    SetuPranaliError
)


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add request_id filter
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        return True

for handler in logging.root.handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)


# =============================================================================
# APPLICATION INITIALIZATION
# =============================================================================

app = FastAPI(
    title="SetuPranali API",
    version="1.0.0",
    description="Semantic analytics layer for BI tools (Power BI, Tableau)"
)

# Register API routers
app.include_router(analytics_router)


# =============================================================================
# STARTUP & SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize databases, check configuration, and log warnings."""
    warnings_logged = []
    
    # Install structured error handlers
    install_error_handlers(app)
    
    # Initialize sources database
    init_sources_db()
    logger.info("Sources database initialized")
    
    # Check encryption key
    if not is_encryption_configured():
        msg = "UBI_SECRET_KEY not set. Using development fallback key."
        logger.warning(msg)
        warnings_logged.append(msg)
    
    # Check Redis
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        msg = "REDIS_URL not set. Cache and rate limiting may use in-memory fallback."
        logger.warning(msg)
        warnings_logged.append(msg)
    
    # Check cache
    from app.infrastructure.cache.redis_cache import get_cache_config
    cache_config = get_cache_config()
    if not cache_config.enabled:
        msg = "Query caching is disabled."
        logger.warning(msg)
        warnings_logged.append(msg)
    
    # Check rate limiting
    from app.rate_limit import get_rate_limit_config
    rate_config = get_rate_limit_config()
    if not rate_config.enabled:
        msg = "Rate limiting is disabled."
        logger.warning(msg)
        warnings_logged.append(msg)
    
    # Setup rate limiting
    from app.rate_limit import setup_rate_limiting
    setup_rate_limiting(app)
    
    # Initialize state storage (DuckDB)
    try:
        from app.infrastructure.storage import init_state_storage
        storage = init_state_storage()
        logger.info("State storage (DuckDB) initialized")
        
        # Migrate default API keys from in-memory registry to DuckDB
        try:
            from app.core.security import _API_KEY_REGISTRY
            default_keys = [
                "dev-key-123",
                "readonly-key-456",
                "tenantA-key",
                "tenantB-key",
                "tenantA-admin-key",
                "internal-admin-key",
            ]
            for api_key in default_keys:
                record = _API_KEY_REGISTRY.get(api_key)
                if record:
                    # Check if already exists in DuckDB
                    existing = storage.get_api_key(api_key)
                    if not existing:
                        storage.save_api_key({
                            "key_id": record.key_id,
                            "api_key": api_key,
                            "tenant": record.tenant,
                            "role": record.role,
                            "name": record.name,
                            "status": record.status,
                            "created_at": record.created_at,
                            "last_used_at": record.last_used_at,
                            "expires_at": None,
                        })
            logger.info("Default API keys migrated to DuckDB")
        except Exception as e:
            logger.debug(f"Failed to migrate default keys: {e}")
    except Exception as e:
        logger.warning(f"Failed to initialize state storage: {e}")
    
    # Initialize observability (uses state storage)
    try:
        from app.infrastructure.observability import init_observability, get_analytics
        init_observability()
        # Verify initialization
        analytics = get_analytics()
        if analytics:
            logger.info("✓ Observability initialized successfully")
            logger.info(f"  Analytics enabled: {analytics.config.analytics_enabled}")
            logger.info(f"  Storage type: {'DuckDB' if (hasattr(analytics, '_use_storage') and analytics._use_storage) else 'in-memory'}")
        else:
            logger.error("✗ Observability initialization failed - analytics is None")
    except Exception as e:
        logger.error(f"✗ Failed to initialize observability: {e}", exc_info=True)
    
    # Schedule periodic cleanup of old query records
    try:
        import threading
        from app.infrastructure.storage import get_state_storage
        from app.infrastructure.observability import get_analytics
        
        def cleanup_old_records():
            """Periodic cleanup of old query records."""
            import time
            time.sleep(3600)  # Wait 1 hour before first cleanup
            while True:
                try:
                    storage = get_state_storage()
                    analytics = get_analytics()
                    if storage and analytics:
                        deleted = storage.cleanup_old_records(
                            retention_hours=analytics.config.analytics_retention_hours
                        )
                        if deleted > 0:
                            logger.info(f"Cleaned up {deleted} old query records")
                    time.sleep(3600)  # Run every hour
                except Exception as e:
                    logger.warning(f"Cleanup job error: {e}")
                    time.sleep(3600)  # Wait before retrying
        
        cleanup_thread = threading.Thread(target=cleanup_old_records, daemon=True)
        cleanup_thread.start()
        logger.info("Query records cleanup job started (runs hourly)")
    except Exception as e:
        logger.debug(f"Failed to start cleanup job: {e}")
    
    # Log startup summary
    if warnings_logged:
        logger.warning(f"Startup completed with {len(warnings_logged)} warnings")
    else:
        logger.info("Startup completed successfully")


# =============================================================================
# MIDDLEWARE
# =============================================================================

# Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing and structured logging."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    
    # Add to logging context
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.request_id = request_id
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    logging.setLogRecordFactory(old_factory)
    return response


# CORS middleware for Tableau WDC and browser-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"  # Allow all for development (restrict in production)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*", "X-API-Key", "Content-Type", "Authorization"],
    expose_headers=["*"],
)


# =============================================================================
# PROTECTED ROUTERS
# =============================================================================

app.include_router(
    odata_router,
    prefix="/v1/odata",
    tags=["OData"],
    dependencies=[Depends(require_api_key)]
)

# GraphQL API endpoint
app.include_router(
    graphql_router,
    prefix="/v1/graphql",
    tags=["GraphQL"]
)

# Advanced Features API (Joins, Calculated Metrics, Caching, Federation)
app.include_router(
    advanced_router,
    prefix="/v1/advanced",
    tags=["Advanced Features"]
)

# Ecosystem Integrations (dbt, Cube.js, LookML, Power BI)
app.include_router(
    ecosystem_router,
    prefix="/v1/ecosystem",
    tags=["Ecosystem"]
)

# Enterprise Features (Hyper export, Embed, White-label, Multi-region)
app.include_router(
    enterprise_router,
    prefix="/v1/enterprise",
    tags=["Enterprise"]
)

# Modeling UI APIs (Schema introspection, ERD, Semantic Model, Query Planner)
app.include_router(
    modeling_router,
    tags=["Modeling"]
)

# Analytics API endpoints
app.include_router(analytics_router)


# =============================================================================
# DEMO DATA
# =============================================================================

def seed_demo_data():
    """Seed demo data with multi-tenant data for RLS testing."""
    try:
        adapter = get_shared_duckdb()
        # Use execute_script for multi-statement execution
        adapter.execute_script("""
          CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR,
            tenant_id VARCHAR,
            order_date DATE,
            city VARCHAR,
            revenue DOUBLE,
            qty INTEGER
          );
          
          DELETE FROM orders;
          
          INSERT INTO orders VALUES
            ('o1', 'tenantA', DATE '2025-12-01', 'Indore', 1000.0, 2),
            ('o2', 'tenantA', DATE '2025-12-01', 'Bhopal', 500.0, 1),
            ('o3', 'tenantB', DATE '2025-12-02', 'Indore', 250.0, 1),
            ('o4', 'tenantB', DATE '2025-12-03', 'Delhi', 1200.0, 3),
            ('o5', 'default', DATE '2025-12-02', 'Mumbai', 800.0, 2),
            ('o6', 'default', DATE '2025-12-03', 'Chennai', 600.0, 1);
        """)
        logger.info("Demo data seeded successfully")
    except Exception as e:
        logger.warning(f"Failed to seed demo data: {e}")

seed_demo_data()  # Enabled for testing - comment out for production


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

# API Key Management
@app.get("/v1/api-keys", tags=["API Keys"])
def list_api_keys():
    """List all API keys (for admin purposes)."""
    from app.core.security import _API_KEY_REGISTRY
    
    # Collect keys from both sources and merge (deduplicate by key_id)
    all_keys = {}
    
    # Try DuckDB state storage first
    try:
        from app.infrastructure.storage.state_storage import get_state_storage
        storage = get_state_storage()
        duckdb_keys = storage.list_api_keys()
        for k in duckdb_keys:
            key_id = k.get("key_id")
            if key_id:
                all_keys[key_id] = {
                    "key_id": key_id,
                    "name": k.get("name"),
                    "tenant": k.get("tenant"),
                    "role": k.get("role"),
                    "status": k.get("status"),
                    "created_at": k.get("created_at"),
                    "last_used_at": k.get("last_used_at")
                }
        logger.debug(f"Retrieved {len(duckdb_keys)} keys from DuckDB storage")
    except Exception as e:
        logger.debug(f"Failed to list keys from state storage: {e}")
    
    # Also get from in-memory registry (may have more recent keys)
    for record in _API_KEY_REGISTRY.values():
        key_id = record.key_id
        if key_id:
            # Use in-memory if not in DuckDB, or if in-memory is more recent
            if key_id not in all_keys or (record.created_at and (
                not all_keys[key_id].get("created_at") or 
                record.created_at > all_keys[key_id].get("created_at")
            )):
                all_keys[key_id] = {
                    "key_id": record.key_id,
                    "name": record.name,
                    "tenant": record.tenant,
                    "role": record.role,
                    "status": record.status,
                    "created_at": record.created_at,
                    "last_used_at": record.last_used_at
                }
    
    logger.debug(f"Total unique keys found: {len(all_keys)}")
    
    # Format and return
    return {
        "items": [
            {
                "key_id": k["key_id"],
                "name": k["name"],
                "tenant": k["tenant"],
                "role": k["role"],
                "status": k["status"],
                "created_at": k["created_at"].isoformat() if k.get("created_at") else None,
                "last_used_at": k["last_used_at"].isoformat() if k.get("last_used_at") else None
            }
            for k in all_keys.values()
        ]
    }


@app.post("/v1/api-keys", tags=["API Keys"])
def create_api_key(
    name: str = Body(...),
    tenant: str = Body("default"),
    role: str = Body("user")
):
    """Create a new API key."""
    import secrets
    
    # Generate a secure API key
    api_key = f"ubi_{secrets.token_urlsafe(32)}"
    key_id = f"key_{secrets.token_urlsafe(8)}"
    created_at = datetime.now(timezone.utc)
    
    # Always save to both DuckDB and in-memory registry for consistency
    from app.core.security import _API_KEY_REGISTRY, APIKeyRecord
    
    # Create the record
    record = APIKeyRecord(
        key_id=key_id,
        name=name,
        tenant=tenant,
        role=role,
        status="active",
        created_at=created_at
    )
    
    # Try DuckDB state storage first
    try:
        from app.infrastructure.storage.state_storage import get_state_storage
        storage = get_state_storage()
        storage.save_api_key({
            "key_id": key_id,
            "api_key": api_key,
            "tenant": tenant,
            "role": role,
            "name": name,
            "status": "active",
            "created_at": created_at,
            "last_used_at": None,
            "expires_at": None,
        })
        logger.debug(f"Saved API key {key_id} to DuckDB storage")
    except Exception as e:
        logger.warning(f"Failed to save key to state storage: {e}")
    
    # Always also save to in-memory registry (as backup and for immediate access)
    _API_KEY_REGISTRY[api_key] = record
    logger.debug(f"Saved API key {key_id} to in-memory registry")
    
    # Return the key only once - it won't be retrievable later
    return {
        "key_id": key_id,
        "api_key": api_key,  # Only shown once!
        "name": name,
        "tenant": tenant,
        "role": role,
        "status": "active",
        "warning": "Store this API key securely. It will not be shown again."
    }


@app.delete("/v1/api-keys/{key_id}", tags=["API Keys"])
def delete_api_key(key_id: str):
    """Revoke an API key."""
    # Try DuckDB state storage first
    try:
        from app.infrastructure.storage.state_storage import get_state_storage
        storage = get_state_storage()
        api_key = storage.get_api_key_for_revocation(key_id)
        if api_key and storage.revoke_api_key(api_key):
            return {"deleted": True, "key_id": key_id}
    except Exception as e:
        logger.debug(f"Failed to revoke key in state storage, using fallback: {e}")
    
    # Fallback to in-memory registry
    from app.core.security import _API_KEY_REGISTRY
    
    for api_key, record in list(_API_KEY_REGISTRY.items()):
        if record.key_id == key_id:
            record.status = "revoked"
            return {"deleted": True, "key_id": key_id}
    
    raise HTTPException(status_code=404, detail=f"API key {key_id} not found")


@app.get("/v1/health", tags=["Health"])
def health():
    """Public health check endpoint."""
    from app.infrastructure.cache.redis_cache import get_cache_stats
    
    cache_stats = get_cache_stats()
    
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "cache": {
            "enabled": cache_stats.get("enabled"),
            "redis_available": cache_stats.get("redis_available"),
            "cached_queries": cache_stats.get("cached_queries", 0)
        }
    }


@app.get("/v1/datasets", tags=["Datasets"])
async def list_datasets():
    """List available datasets."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug("Loading catalog for datasets endpoint")
        catalog = load_catalog()
        logger.debug("Catalog loaded successfully")
        
        items = []
        datasets = catalog.get("datasets", {})
        logger.debug(f"Datasets type: {type(datasets)}, count: {len(datasets) if hasattr(datasets, '__len__') else 'N/A'}")
        
        # Handle both dict format (id: config) and list format
        if isinstance(datasets, dict):
            for dataset_id, d in datasets.items():
                if isinstance(d, dict):
                    items.append({
                        "id": dataset_id,
                        "name": d.get("name", dataset_id),
                        "description": d.get("description"),
                        "tags": d.get("tags", []),
                        "defaultTimezone": d.get("defaultTimezone", "UTC")
                    })
        elif isinstance(datasets, list):
            for d in datasets:
                if isinstance(d, dict):
                    items.append({
                        "id": d.get("id", "unknown"),
                        "name": d.get("name", d.get("id", "unknown")),
                        "description": d.get("description"),
                        "tags": d.get("tags", []),
                        "defaultTimezone": d.get("defaultTimezone", "UTC")
                    })
        
        logger.debug(f"Returning {len(items)} datasets")
        # Use JSONResponse to ensure proper Content-Length header
        return JSONResponse(content={"items": items})
    except Exception as e:
        logger.error(f"Error loading datasets: {e}", exc_info=True)
        # Return empty list on error instead of crashing
        return JSONResponse(content={"items": []})


@app.get("/v1/datasets/{datasetId}", tags=["Datasets"])
def get_dataset_detail(datasetId: str, request: Request):
    """Get dataset details."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return d
    except KeyError:
        datasets = catalog.get("datasets", {})
        if isinstance(datasets, dict):
            available = list(datasets.keys())
        else:
            available = [ds.get("id", "unknown") for ds in datasets]
        raise dataset_not_found(
            dataset=datasetId,
            available_datasets=available,
            request_id=getattr(request.state, "request_id", None)
        )


@app.get("/v1/datasets/{datasetId}/schema", tags=["Datasets"])
def get_schema(datasetId: str, request: Request):
    """Get dataset schema."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return {"datasetId": datasetId, "fields": d.get("fields", [])}
    except KeyError:
        available = [ds["id"] for ds in catalog.get("datasets", [])]
        raise dataset_not_found(
            dataset=datasetId,
            available_datasets=available,
            request_id=getattr(request.state, "request_id", None)
        )


@app.get("/v1/datasets/{datasetId}/dimensions", tags=["Datasets"])
def get_dimensions(datasetId: str, request: Request):
    """Get dataset dimensions."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return {"items": d.get("dimensions", [])}
    except KeyError:
        available = [ds["id"] for ds in catalog.get("datasets", [])]
        raise dataset_not_found(
            dataset=datasetId,
            available_datasets=available,
            request_id=getattr(request.state, "request_id", None)
        )


@app.get("/v1/datasets/{datasetId}/metrics", tags=["Datasets"])
def get_metrics(datasetId: str, request: Request):
    """Get dataset metrics."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return {"items": d.get("metrics", [])}
    except KeyError:
        available = [ds["id"] for ds in catalog.get("datasets", [])]
        raise dataset_not_found(
            dataset=datasetId,
            available_datasets=available,
            request_id=getattr(request.state, "request_id", None)
        )


# =============================================================================
# SCHEMA INTROSPECTION API
# =============================================================================

@app.get("/v1/introspection/datasets", tags=["Introspection"])
def introspect_all_datasets():
    """
    Get full schema introspection for all datasets.
    Useful for BI tools to auto-discover available fields.
    """
    catalog = load_catalog()
    datasets = []
    
    for d in catalog.get("datasets", []):
        datasets.append({
            "id": d["id"],
            "name": d.get("name", d["id"]),
            "description": d.get("description"),
            "source": d.get("source"),
            "tags": d.get("tags", []),
            "schema": {
                "dimensions": [
                    {
                        "name": dim["name"],
                        "label": dim.get("label", dim["name"]),
                        "type": dim.get("type", "string"),
                        "description": dim.get("description"),
                        "sql": dim.get("sql"),
                        "hidden": dim.get("hidden", False)
                    }
                    for dim in d.get("dimensions", [])
                ],
                "metrics": [
                    {
                        "name": m["name"],
                        "label": m.get("label", m["name"]),
                        "type": m.get("type", "number"),
                        "description": m.get("description"),
                        "sql": m.get("sql"),
                        "aggregation": m.get("aggregation", "sum"),
                        "format": m.get("format"),
                        "hidden": m.get("hidden", False)
                    }
                    for m in d.get("metrics", [])
                ]
            },
            "defaultTimezone": d.get("defaultTimezone", "UTC"),
            "refreshPolicy": d.get("refreshPolicy", "onDemand")
        })
    
    return {
        "datasets": datasets,
        "version": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat()
    }


@app.get("/v1/introspection/datasets/{datasetId}", tags=["Introspection"])
def introspect_dataset(datasetId: str):
    """
    Get detailed schema introspection for a specific dataset.
    Returns all fields with their types, labels, and SQL definitions.
    """
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return {
        "id": d["id"],
        "name": d.get("name", d["id"]),
        "description": d.get("description"),
        "source": d.get("source"),
        "tags": d.get("tags", []),
        "table": d.get("table"),
        "sql": d.get("sql"),
        "schema": {
            "dimensions": [
                {
                    "name": dim["name"],
                    "label": dim.get("label", dim["name"]),
                    "type": dim.get("type", "string"),
                    "description": dim.get("description"),
                    "sql": dim.get("sql"),
                    "primaryKey": dim.get("primaryKey", False),
                    "hidden": dim.get("hidden", False),
                    "values": dim.get("values"),  # Enum values if applicable
                }
                for dim in d.get("dimensions", [])
            ],
            "metrics": [
                {
                    "name": m["name"],
                    "label": m.get("label", m["name"]),
                    "type": m.get("type", "number"),
                    "description": m.get("description"),
                    "sql": m.get("sql"),
                    "aggregation": m.get("aggregation", "sum"),
                    "format": m.get("format"),
                    "hidden": m.get("hidden", False),
                    "drillMembers": m.get("drillMembers", []),
                }
                for m in d.get("metrics", [])
            ]
        },
        "joins": d.get("joins", []),
        "filters": d.get("defaultFilters", []),
        "rls": {
            "enabled": "rls" in d,
            "field": d.get("rls", {}).get("field") if "rls" in d else None
        },
        "defaultTimezone": d.get("defaultTimezone", "UTC"),
        "refreshPolicy": d.get("refreshPolicy", "onDemand"),
        "generatedAt": datetime.now(timezone.utc).isoformat()
    }


@app.get("/v1/introspection/openapi", tags=["Introspection"])
def get_openapi_spec():
    """
    Get OpenAPI specification for the SetuPranali API.
    """
    return app.openapi()


# =============================================================================
# SQL ENDPOINT WITH RLS
# =============================================================================

class SQLRequest(BaseModel):
    """SQL query request with RLS."""
    sql: str
    dataset: str  # Required for RLS context
    parameters: dict = {}


class SQLResponse(BaseModel):
    """SQL query response."""
    columns: list
    data: list
    rowCount: int
    executionTimeMs: int


@app.post("/v1/sql", tags=["SQL"])
@limit_query
def run_sql_query(
    request: Request,
    req: SQLRequest,
    ctx: TenantContext = Depends(require_api_key)
):
    """
    Execute a raw SQL query with automatic Row-Level Security.
    
    The SQL query will be wrapped to apply RLS based on your API key's tenant.
    You must specify a dataset to determine which RLS rules to apply.
    
    **Authentication Required**: This endpoint requires an API key.
    Create one at: POST /v1/api-keys
    Then use: Header: X-API-Key: <your-api-key>
    
    Example:
        POST /v1/sql
        Headers: X-API-Key: your-api-key
        Body: {
            "sql": "SELECT city, SUM(revenue) as total FROM orders GROUP BY city",
            "dataset": "orders"
        }
    
    Security:
        - RLS is automatically applied based on your API key
        - Only SELECT queries are allowed
        - Dangerous operations (DROP, DELETE, etc.) are blocked
    """
    import time
    
    start_time = time.time()
    
    request_id = getattr(request.state, "request_id", None)
    
    # SQL Validation using SQLGlot
    try:
        from app.domain.query import SQLBuilder
        import sqlglot
        from sqlglot.errors import ParseError
        
        # Parse and validate SQL
        try:
            # Use None for auto-detect or "duckdb" as default for demo
            ast = sqlglot.parse_one(req.sql, read=None)
            
            # Security: Only allow SELECT queries
            if not isinstance(ast, sqlglot.expressions.Select):
                raise sql_unsafe(
                    reason="Only SELECT queries are allowed",
                    pattern="non-SELECT statement",
                    request_id=request_id
                )
            
            # Security: Check for dangerous operations in AST
            dangerous_keywords = [
                "DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE",
                "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
            ]
            
            sql_upper = req.sql.upper()
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    raise sql_unsafe(
                        reason=f"Query contains disallowed operation: {keyword}",
                        pattern=keyword,
                        request_id=request_id
                    )
        
        except ParseError as e:
            raise sql_unsafe(
                reason=f"Invalid SQL syntax: {str(e)}",
                pattern="parse_error",
                request_id=request_id
            )
    
    except ImportError:
        # Fallback to regex-based validation if SQLGlot not available
        import re
        sql_upper = req.sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            raise sql_unsafe(
                reason="Only SELECT queries are allowed",
                pattern="non-SELECT statement",
                request_id=request_id
            )
        
        dangerous_patterns = [
            (r'\bDROP\b', "DROP"),
            (r'\bDELETE\b', "DELETE"),
            (r'\bTRUNCATE\b', "TRUNCATE"),
            (r'\bINSERT\b', "INSERT"),
            (r'\bUPDATE\b', "UPDATE"),
            (r'\bALTER\b', "ALTER"),
            (r'\bCREATE\b', "CREATE"),
            (r'\bGRANT\b', "GRANT"),
            (r'\bREVOKE\b', "REVOKE"),
            (r'\bEXEC\b', "EXEC"),
            (r'\bEXECUTE\b', "EXECUTE"),
        ]
        for pattern, name in dangerous_patterns:
            if re.search(pattern, req.sql, re.IGNORECASE):
                raise sql_unsafe(
                    reason=f"Query contains disallowed operation: {name}",
                    pattern=name,
                    request_id=request_id
                )
    
    # Load dataset for RLS context
    catalog = load_catalog()
    try:
        dataset = get_dataset(catalog, req.dataset)
    except KeyError:
        available = [ds["id"] for ds in catalog.get("datasets", [])]
        raise dataset_not_found(
            dataset=req.dataset,
            available_datasets=available,
            request_id=request_id
        )
    
    # Get RLS configuration
    rls_config = dataset.get("rls", {})
    rls_field = rls_config.get("column", rls_config.get("field", "tenant_id"))
    
    # Apply RLS - for admin/default tenant, use SQL as-is
    # For other tenants, wrap with RLS filter if RLS is enabled
    rls_sql = req.sql
    if ctx.tenant != "default" and ctx.role != "admin" and rls_config.get("enabled", False):
        # Wrap SQL with RLS filter
        rls_sql = f"""
        WITH rls_filtered AS (
            SELECT * FROM ({req.sql}) AS user_query
            WHERE {rls_field} = '{ctx.tenant}'
        )
        SELECT * FROM rls_filtered
        """
    # For admin/default tenant, RLS is bypassed - use SQL as-is
    
    try:
        from app.domain.sources.manager import SOURCES
        from app.infrastructure.adapters.base import BaseAdapter
        engine, conn = get_engine_and_conn(dataset["source"], SOURCES)
        
        # Ensure adapter is connected if it's an adapter
        if isinstance(conn, BaseAdapter) and not conn.is_connected():
            conn.connect()
        
        # Execute query - handle both adapter and legacy connections
        if isinstance(conn, BaseAdapter):
            # New adapter interface - rows are already dicts
            result = conn.execute(rls_sql)
            data = result.rows  # Already list of dicts
            columns = [{"name": col, "type": result.column_types.get(col, "string")} for col in result.columns]
        elif hasattr(conn, 'execute') and hasattr(conn, 'cursor') is False:
            # Legacy DuckDB connection
            result = conn.execute(rls_sql)
            df = result.fetchdf()
            data = df.to_dict(orient="records")  # Already list of dicts
            columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
        else:
            # Legacy Postgres connection
            cur = conn.cursor()
            cur.execute(rls_sql)
            colnames = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            cur.close()
            # Convert tuples to dicts
            data = [dict(zip(colnames, row)) for row in rows]
            columns = [{"name": col, "type": "string"} for col in colnames]
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            "columns": columns,
            "data": data,
            "rowCount": len(data),
            "executionTimeMs": execution_time,
            "rlsApplied": ctx.tenant != "default" and ctx.role != "admin",
            "tenant": ctx.tenant
        }
        
    except SetuPranaliError:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"SQL query error: {e}")
        import traceback
        logger.error(f"SQL query error traceback: {traceback.format_exc()}")
        raise internal_error(
            message=f"Query execution failed: {str(e)}",
            details={"sql_preview": req.sql[:100] + "..." if len(req.sql) > 100 else req.sql},
            request_id=request_id
        )


# =============================================================================
# NATURAL LANGUAGE QUERY ENDPOINT
# =============================================================================

class NLQRequest(BaseModel):
    """Natural language query request."""
    question: str
    dataset: str
    provider: str = "simple"  # simple, openai, anthropic
    model: str = None
    execute: bool = False  # If true, execute the translated query


@app.post("/v1/nlq", tags=["NLQ"])
@limit_query
def natural_language_query(
    request: Request,
    req: NLQRequest,
    ctx: TenantContext = Depends(require_api_key)
):
    """
    Translate a natural language question into a semantic query.
    
    Optionally execute the query and return results.
    
    Providers:
        - simple: Rule-based translation (no AI, always available)
        - openai: Use OpenAI GPT models (requires OPENAI_API_KEY)
        - anthropic: Use Anthropic Claude (requires ANTHROPIC_API_KEY)
    
    Example:
        POST /v1/nlq
        {
            "question": "What are the top 10 cities by revenue?",
            "dataset": "orders",
            "provider": "simple",
            "execute": true
        }
    """
    from app.nlq import translate_question, translate_simple, NLQConfig
    
    request_id = getattr(request.state, "request_id", None)
    
    # Load dataset schema
    catalog = load_catalog()
    try:
        dataset = get_dataset(catalog, req.dataset)
    except KeyError:
        available = [ds["id"] for ds in catalog.get("datasets", [])]
        raise dataset_not_found(
            dataset=req.dataset,
            available_datasets=available,
            request_id=request_id
        )
    
    # Build schema for NLQ
    dataset_schema = {
        "id": dataset["id"],
        "name": dataset.get("name", dataset["id"]),
        "description": dataset.get("description", ""),
        "dimensions": dataset.get("dimensions", []),
        "metrics": dataset.get("metrics", [])
    }
    
    # Translate question
    try:
        if req.provider == "simple":
            result = translate_simple(req.question, dataset_schema)
        else:
            api_key = os.getenv(f"{req.provider.upper()}_API_KEY")
            if not api_key:
                raise nlq_provider_missing(
                    provider=req.provider,
                    request_id=request_id
                )
            config = NLQConfig(
                provider=req.provider,
                model=req.model,
                api_key=api_key
            )
            result = translate_question(req.question, dataset_schema, config)
    except SetuPranaliError:
        raise
    except ImportError as e:
        raise nlq_provider_missing(
            provider=req.provider,
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"NLQ translation error: {e}")
        raise nlq_translation_failed(
            reason=str(e),
            provider=req.provider,
            request_id=request_id
        )
    
    response = {
        "question": result.original_question,
        "query": result.translated_query,
        "explanation": result.explanation,
        "confidence": result.confidence,
        "suggestions": result.suggestions,
        "provider": req.provider
    }
    
    # Execute query if requested
    if req.execute and result.translated_query and result.confidence > 0.3:
        try:
            from app.domain.query import compile_and_run_query
            from app.shared.types import QueryRequest, DimensionRequest, MetricRequest
            from app.domain.sources import SOURCES
            
            # Build query request
            query_req = QueryRequest(
                dataset=req.dataset,
                dimensions=[DimensionRequest(name=d) for d in result.translated_query.get("dimensions", [])],
                metrics=[MetricRequest(name=m) for m in result.translated_query.get("metrics", [])],
                limit=result.translated_query.get("limit", 100)
            )
            
            engine, conn = get_engine_and_conn(dataset["source"], SOURCES)
            columns, rows, stats = compile_and_run_query(
                dataset, query_req, conn,
                engine=engine,
                tenant=ctx.tenant,
                role=ctx.role
            )
            
            response["results"] = {
                "columns": [{"name": c.name, "type": c.type} for c in columns],
                "data": rows,
                "rowCount": len(rows)
            }
        except Exception as e:
            response["executionError"] = str(e)
    
    return response


# =============================================================================
# PROTECTED QUERY ENDPOINT
# =============================================================================

@app.post("/v1/query", response_model=QueryResponse, tags=["Query"])
@limit_query
def run_query(
    request: Request,
    req: QueryRequest,
    ctx: TenantContext = Depends(require_api_key)
):
    """
    Execute a semantic query against a dataset.
    
    **Authentication Required**: This endpoint requires an API key.
    Create one at: POST /v1/api-keys
    Then use: Header: X-API-Key: <your-api-key>
    
    Example:
        POST /v1/query
        Headers: X-API-Key: your-api-key
        Body: {
            "dataset": "orders",
            "dimensions": [{"name": "city"}],
            "metrics": [{"name": "total_revenue"}],
            "limit": 100
        }
    
    Applies:
    - Row-Level Security (automatic tenant filtering)
    - Safety Guards (limit validation)
    - Query Caching (tenant-scoped)
    """
    from app.domain.query import compile_and_run_query
    from app.infrastructure.cache import execute_with_cache, build_cache_components_from_request
    from app.guards import validate_query_request, QueryValidationError, check_result_size
    
    request_id = getattr(request.state, "request_id", None)
    
    # Structured logging
    logger.info(f"Query: dataset={req.dataset} tenant={ctx.tenant} dims={len(req.dimensions)} metrics={len(req.metrics)}")
    
    # Safety guards - validate request
    try:
        req = validate_query_request(req)
    except QueryValidationError as e:
        from app.shared.exceptions.errors import query_validation_error
        error_dict = e.to_dict()
        raise query_validation_error(
            message=error_dict.get("message", str(e)),
            field=error_dict.get("field"),
            limit=error_dict.get("limit"),
            actual=error_dict.get("actual"),
            request_id=request_id
        )
    
    # Load dataset
    catalog = load_catalog()
    try:
        dataset = get_dataset(catalog, req.dataset)
    except KeyError:
        datasets = catalog.get("datasets", {})
        if isinstance(datasets, dict):
            available = list(datasets.keys())
        else:
            available = [ds.get("id", "unknown") for ds in datasets]
        raise dataset_not_found(
            dataset=req.dataset,
            available_datasets=available,
            request_id=request_id
        )
    
    try:
        from app.domain.sources import SOURCES
        
        # Get source config - handle both string reference and object
        source_ref = dataset.get("source", {})
        if isinstance(source_ref, str):
            # String reference to a source in catalog
            catalog_sources = catalog.get("sources", {})
            if source_ref in catalog_sources:
                source_config = catalog_sources[source_ref]
                # Ensure we have engine type from source definition
                source_config = {"engine": source_config.get("type", "duckdb"), **source_config}
            else:
                source_config = {"sourceId": source_ref}
        else:
            source_config = source_ref
        
        # Get engine and connection (may be adapter or legacy connection)
        engine, conn = get_engine_and_conn(source_config, SOURCES)
        
        # Ensure adapter is connected if it's an adapter
        from app.infrastructure.adapters.base import BaseAdapter
        if isinstance(conn, BaseAdapter) and not conn.is_connected():
            conn.connect()
        
        # Build cache components
        cache_components = build_cache_components_from_request(
            req, dataset, engine, ctx.tenant, ctx.role
        )
        
        # Track query start time
        query_start_time = time.perf_counter()
        query_success = False
        query_error = None
        
        # Execute with caching
        def execute_query():
            return compile_and_run_query(
                dataset, req, conn,
                engine=engine,
                tenant=ctx.tenant,
                role=ctx.role
            )
        
        try:
            columns, rows, stats = execute_with_cache(
                execute_fn=execute_query,
                cache_components=cache_components
            )
            
            # Log result size
            check_result_size(rows)
            
            query_success = True
            query_duration_ms = (time.perf_counter() - query_start_time) * 1000
            
            # Record query analytics
            try:
                from app.infrastructure.observability import get_analytics, QueryRecord
                analytics = get_analytics()
                if analytics is None:
                    logger.warning("⚠ Analytics module not initialized - call init_observability() first")
                elif not analytics.config.analytics_enabled:
                    logger.debug("Analytics disabled in config")
                else:
                    cache_hit = stats.get("cache_hit", False) if stats else False
                    # Extract dimension and metric names (handle both dict and object)
                    def get_name(item):
                        if isinstance(item, dict):
                            return item.get("name", "")
                        elif hasattr(item, "name"):
                            return item.name
                        elif hasattr(item, "__dict__"):
                            return item.__dict__.get("name", "")
                        return str(item)
                    
                    record = QueryRecord(
                        query_id=str(request_id) if request_id else str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        dataset=req.dataset,
                        tenant_id=ctx.tenant,
                        dimensions=[get_name(d) for d in req.dimensions],
                        metrics=[get_name(m) for m in req.metrics],
                        filters=req.filters if hasattr(req, 'filters') else None,
                        duration_ms=query_duration_ms,
                        rows_returned=len(rows),
                        bytes_scanned=0,
                        cache_hit=cache_hit,
                        success=True,
                        error_code=None,
                        error_message=None,
                        api_key_hash=None,
                        user_id=None,
                        source_ip=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
                    analytics.record_query(record)
                    storage_type = "DuckDB" if (hasattr(analytics, '_use_storage') and analytics._use_storage) else "in-memory"
                    logger.info(f"✓ Recorded query analytics: dataset={req.dataset}, duration={query_duration_ms:.2f}ms, storage={storage_type}")
            except Exception as e:
                logger.error(f"✗ Failed to record query analytics: {e}", exc_info=True)
            
            return QueryResponse(dataset=req.dataset, columns=columns, rows=rows, stats=stats)
        
        except Exception as query_err:
            query_duration_ms = (time.perf_counter() - query_start_time) * 1000
            query_error = str(query_err)
            
            # Record failed query analytics
            try:
                from app.infrastructure.observability import get_analytics, QueryRecord
                analytics = get_analytics()
                if analytics:
                    # Extract dimension and metric names (handle both dict and object)
                    def get_name(item):
                        if isinstance(item, dict):
                            return item.get("name", "")
                        elif hasattr(item, "name"):
                            return item.name
                        elif hasattr(item, "__dict__"):
                            return item.__dict__.get("name", "")
                        return str(item)
                    
                    record = QueryRecord(
                        query_id=str(request_id) if request_id else str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        dataset=req.dataset,
                        tenant_id=ctx.tenant,
                        dimensions=[get_name(d) for d in req.dimensions],
                        metrics=[get_name(m) for m in req.metrics],
                        filters=req.filters if hasattr(req, 'filters') else None,
                        duration_ms=query_duration_ms,
                        rows_returned=0,
                        bytes_scanned=0,
                        cache_hit=False,
                        success=False,
                        error_code="QUERY_ERROR",
                        error_message=query_error,
                        api_key_hash=None,
                        user_id=None,
                        source_ip=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
                    analytics.record_query(record)
                    logger.debug(f"Recorded failed query analytics: dataset={req.dataset}, error={query_error}")
            except Exception as e:
                logger.warning(f"Failed to record failed query analytics: {e}", exc_info=True)
            
            raise
    
    except SetuPranaliError:
        raise
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise internal_error(
            message=f"Query execution failed: {str(e)}",
            details={"dataset": req.dataset},
            request_id=request_id
        )


# =============================================================================
# SOURCE MANAGEMENT ENDPOINTS
# =============================================================================

@app.post("/v1/sources", tags=["Sources"])
def create_source(request: Request, payload: dict):
    """Register a new data source."""
    request_id = getattr(request.state, "request_id", None)
    try:
        return register_source(payload)
    except SetuPranaliError:
        raise
    except Exception as e:
        from app.shared.exceptions.errors import ErrorCode
        raise SetuPranaliError(
            code=ErrorCode.ERR_SOURCE_INVALID,
            message=f"Failed to register source: {str(e)}",
            status_code=400,
            details={"source_name": payload.get("name")},
            suggestion="Check that all required fields are provided and credentials are valid",
            request_id=request_id
        )


@app.get("/v1/sources", tags=["Sources"])
def get_sources():
    """List all registered sources."""
    return {"items": list_sources()}


@app.put("/v1/sources/{sourceId}", tags=["Sources"])
def update_source_endpoint(request: Request, sourceId: str, payload: dict = Body(...)):
    """Update a data source."""
    from app.domain.sources import update_source, get_source
    
    request_id = getattr(request.state, "request_id", None)
    
    try:
        # Verify source exists
        source = get_source(sourceId)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {sourceId} not found")
        
        # Build updates dict
        updates = {}
        if "name" in payload:
            updates["name"] = payload["name"]
        if "type" in payload:
            updates["type"] = payload["type"]
        if "config" in payload:
            updates["config"] = payload["config"]
        if "status" in payload:
            updates["status"] = payload["status"]
        
        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        updated_source = update_source(sourceId, updates)
        return updated_source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Failed to update source {sourceId}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update source: {str(e)}")


@app.get("/v1/sources/{sourceId}", tags=["Sources"])
def get_source_endpoint(request: Request, sourceId: str):
    """Get a single data source by ID."""
    from app.domain.sources import get_source
    
    request_id = getattr(request.state, "request_id", None)
    
    try:
        source = get_source(sourceId)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {sourceId} not found")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Failed to get source {sourceId}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get source: {str(e)}")


@app.delete("/v1/sources/{sourceId}", tags=["Sources"])
def remove_source(request: Request, sourceId: str):
    """Delete a data source."""
    from app.domain.sources import delete_source, get_source
    
    request_id = getattr(request.state, "request_id", None)
    
    try:
        # Verify source exists
        source = get_source(sourceId)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {sourceId} not found")
        
        deleted = delete_source(sourceId)
        if deleted:
            return {"deleted": True, "id": sourceId}
        else:
            raise HTTPException(status_code=404, detail=f"Source {sourceId} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Failed to delete source {sourceId}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete source: {str(e)}")


@app.post("/v1/sources/{sourceId}/test", tags=["Sources"])
def test_source(request: Request, sourceId: str):
    """Test connection to a data source."""
    import time
    
    request_id = getattr(request.state, "request_id", None)
    
    try:
        from app.domain.sources import get_source_with_config
        source = get_source_with_config(sourceId)
        start_time = time.time()

        if source["type"] == "postgres":
            import psycopg2
            cfg = source["config"]

            conn = psycopg2.connect(
                host=cfg["host"],
                port=cfg.get("port", 5432),
                dbname=cfg["database"],
                user=cfg["user"],
                password=cfg["password"],
                connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            conn.close()
            
            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "message": f"Postgres source '{source['name']}' connected successfully",
                "latencyMs": latency_ms
            }
        else:
            return {
                "success": False,
                "message": f"Source type '{source['type']}' not supported for testing yet"
            }

    except KeyError:
        available = [s["name"] for s in list_sources()]
        raise source_not_found(
            source=sourceId,
            available_sources=available,
            request_id=request_id
        )
    except ValueError as e:
        raise decryption_failed(
            source=sourceId,
            request_id=request_id
        )
    except SetuPranaliError:
        raise
    except Exception as e:
        raise connection_failed(
            source=sourceId,
            reason=str(e),
            engine="postgres",
            request_id=request_id
        )


# =============================================================================
# INTERNAL ADMIN ENDPOINTS
# =============================================================================

@app.get("/internal/status", tags=["Internal"])
def internal_status(ctx: TenantContext = Depends(require_internal_admin)):
    """
    Detailed system status for operations.
    
    Requires internal admin API key.
    Returns comprehensive health information.
    """
    from app.infrastructure.cache.redis_cache import get_cache_stats
    from app.rate_limit import get_rate_limit_status
    from app.guards import get_safety_status
    from app.core.security import get_security_status
    from app.shared.utils.crypto import is_encryption_configured
    
    # Database connectivity check
    db_status = {"duckdb": False, "sources_db": False}
    try:
        adapter = get_shared_duckdb()
        adapter.execute("SELECT 1")
        db_status["duckdb"] = True
    except Exception:
        pass
    
    try:
        from app.domain.sources.manager import list_sources
        list_sources()
        db_status["sources_db"] = True
    except Exception:
        pass
    
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": {
            "encryption_configured": is_encryption_configured(),
            "redis_url_set": os.environ.get("REDIS_URL") is not None
        },
        "cache": get_cache_stats(),
        "rate_limiting": get_rate_limit_status(),
        "safety_guards": get_safety_status(),
        "security": get_security_status(),
        "database": db_status
    }


# =============================================================================
# ANALYTICS ENDPOINT
# =============================================================================

# Analytics endpoints are now in app/api/v1/analytics.py
# Registered via app.include_router(analytics_router) above
