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
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.catalog import load_catalog, get_dataset
from app.models import QueryRequest, QueryResponse, ResultColumn
from app.sources import (
    register_source, list_sources, get_source, get_source_with_config,
    init_database as init_sources_db
)
from app.connection_manager import get_engine_and_conn
from app.adapters.duckdb_adapter import get_shared_duckdb
from app.odata import router as odata_router
from app.graphql_api import graphql_router
from app.security import require_api_key, require_internal_admin, TenantContext
from app.crypto import is_encryption_configured
from app.rate_limit import limit_query, limit_odata, limit_sources


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


# =============================================================================
# STARTUP & SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize databases, check configuration, and log warnings."""
    warnings_logged = []
    
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
    from app.cache import get_cache_config
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
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*", "X-API-Key"],
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


# =============================================================================
# DEMO DATA
# =============================================================================

def seed_demo_data():
    """Seed demo data with multi-tenant data for RLS testing."""
    adapter = get_shared_duckdb()
    adapter.execute_script("""
      CREATE TABLE IF NOT EXISTS orders AS
      SELECT * FROM (VALUES
        ('o1', 'tenantA', DATE '2025-12-01', 'Indore', 1000.0, 2),
        ('o2', 'tenantA', DATE '2025-12-01', 'Bhopal', 500.0, 1),
        ('o3', 'tenantB', DATE '2025-12-02', 'Indore', 250.0, 1),
        ('o4', 'tenantB', DATE '2025-12-03', 'Delhi', 1200.0, 3),
        ('o5', 'default', DATE '2025-12-02', 'Mumbai', 800.0, 2),
        ('o6', 'default', DATE '2025-12-03', 'Chennai', 600.0, 1)
      ) t(order_id, tenant_id, order_date, city, revenue, qty);
    """)

seed_demo_data()


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@app.get("/v1/health", tags=["Health"])
def health():
    """Public health check endpoint."""
    from app.cache import get_cache_stats
    
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
def list_datasets():
    """List available datasets."""
    catalog = load_catalog()
    items = []
    for d in catalog.get("datasets", []):
        items.append({
            "id": d["id"],
            "name": d.get("name", d["id"]),
            "description": d.get("description"),
            "tags": d.get("tags", []),
            "defaultTimezone": d.get("defaultTimezone", "UTC")
        })
    return {"items": items}


@app.get("/v1/datasets/{datasetId}", tags=["Datasets"])
def get_dataset_detail(datasetId: str):
    """Get dataset details."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return d
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")


@app.get("/v1/datasets/{datasetId}/schema", tags=["Datasets"])
def get_schema(datasetId: str):
    """Get dataset schema."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return {"datasetId": datasetId, "fields": d.get("fields", [])}
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")


@app.get("/v1/datasets/{datasetId}/dimensions", tags=["Datasets"])
def get_dimensions(datasetId: str):
    """Get dataset dimensions."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return {"items": d.get("dimensions", [])}
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")


@app.get("/v1/datasets/{datasetId}/metrics", tags=["Datasets"])
def get_metrics(datasetId: str):
    """Get dataset metrics."""
    catalog = load_catalog()
    try:
        d = get_dataset(catalog, datasetId)
        return {"items": d.get("metrics", [])}
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")


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
    
    Example:
        POST /v1/sql
        {
            "sql": "SELECT city, SUM(revenue) as total FROM orders GROUP BY city",
            "dataset": "orders"
        }
    
    Security:
        - RLS is automatically applied based on your API key
        - Only SELECT queries are allowed
        - Dangerous operations (DROP, DELETE, etc.) are blocked
    """
    import time
    import re
    
    start_time = time.time()
    
    # Security: Only allow SELECT queries
    sql_upper = req.sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400, 
            detail="Only SELECT queries are allowed"
        )
    
    # Security: Block dangerous operations
    dangerous_patterns = [
        r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b', r'\bINSERT\b',
        r'\bUPDATE\b', r'\bALTER\b', r'\bCREATE\b', r'\bGRANT\b',
        r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b', r'--', r'/\*'
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, req.sql, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail=f"Query contains disallowed operation"
            )
    
    # Load dataset for RLS context
    catalog = load_catalog()
    try:
        dataset = get_dataset(catalog, req.dataset)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get RLS configuration
    rls_config = dataset.get("rls", {})
    rls_field = rls_config.get("field", "tenant_id")
    
    # Wrap query with RLS
    # This creates a CTE that filters the base data
    rls_sql = f"""
    WITH rls_filtered AS (
        SELECT * FROM ({req.sql}) AS user_query
        WHERE {rls_field} = '{ctx.tenant}'
    )
    SELECT * FROM rls_filtered
    """
    
    # If tenant is 'default' or admin role, don't apply RLS
    if ctx.tenant == "default" or ctx.role == "admin":
        rls_sql = req.sql
    
    try:
        from app.sources import SOURCES
        engine, conn = get_engine_and_conn(dataset["source"], SOURCES)
        
        # Execute query
        result = conn.execute(rls_sql)
        
        if hasattr(result, 'fetchall'):
            rows = result.fetchall()
            columns = [{"name": str(col), "type": "string"} for col in result.keys()]
        else:
            rows = list(result)
            columns = [{"name": f"col_{i}", "type": "string"} for i in range(len(rows[0]) if rows else 0)]
        
        # Convert rows to dicts
        data = []
        for row in rows:
            if hasattr(row, '_asdict'):
                data.append(row._asdict())
            elif hasattr(row, 'keys'):
                data.append(dict(row))
            else:
                data.append({columns[i]["name"]: v for i, v in enumerate(row)})
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            "columns": columns,
            "data": data,
            "rowCount": len(data),
            "executionTimeMs": execution_time,
            "rlsApplied": ctx.tenant != "default" and ctx.role != "admin",
            "tenant": ctx.tenant
        }
        
    except Exception as e:
        logger.error(f"SQL query error: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")


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
    
    # Load dataset schema
    catalog = load_catalog()
    try:
        dataset = get_dataset(catalog, req.dataset)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
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
            config = NLQConfig(
                provider=req.provider,
                model=req.model,
                api_key=os.getenv(f"{req.provider.upper()}_API_KEY")
            )
            result = translate_question(req.question, dataset_schema, config)
    except ImportError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{req.provider}' requires additional packages: {e}"
        )
    except Exception as e:
        logger.error(f"NLQ translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
    
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
            from app.query_engine import compile_and_run_query
            from app.models import QueryRequest, DimensionRequest, MetricRequest
            from app.sources import SOURCES
            
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
    
    Requires X-API-Key header for authentication.
    Applies:
    - Row-Level Security (automatic tenant filtering)
    - Safety Guards (limit validation)
    - Query Caching (tenant-scoped)
    """
    from app.query_engine import compile_and_run_query
    from app.cache import execute_with_cache, build_cache_components_from_request
    from app.guards import validate_query_request, QueryValidationError, check_result_size
    
    # Structured logging
    logger.info(f"Query: dataset={req.dataset} tenant={ctx.tenant} dims={len(req.dimensions)} metrics={len(req.metrics)}")
    
    # Safety guards - validate request
    try:
        req = validate_query_request(req)
    except QueryValidationError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    
    # Load dataset
    catalog = load_catalog()
    try:
        dataset = get_dataset(catalog, req.dataset)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    try:
        from app.sources import SOURCES
        engine, conn = get_engine_and_conn(dataset["source"], SOURCES)
        
        # Build cache components
        cache_components = build_cache_components_from_request(
            req, dataset, engine, ctx.tenant, ctx.role
        )
        
        # Execute with caching
        def execute_query():
            return compile_and_run_query(
                dataset, req, conn,
                engine=engine,
                tenant=ctx.tenant,
                role=ctx.role
            )
        
        columns, rows, stats = execute_with_cache(
            execute_fn=execute_query,
            cache_components=cache_components
        )
        
        # Log result size
        check_result_size(rows)
        
        return QueryResponse(dataset=req.dataset, columns=columns, rows=rows, stats=stats)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# SOURCE MANAGEMENT ENDPOINTS
# =============================================================================

@app.post("/v1/sources", tags=["Sources"])
def create_source(payload: dict):
    """Register a new data source."""
    try:
        return register_source(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/sources", tags=["Sources"])
def get_sources():
    """List all registered sources."""
    return {"items": list_sources()}


@app.post("/v1/sources/{sourceId}/test", tags=["Sources"])
def test_source(sourceId: str):
    """Test connection to a data source."""
    import time
    
    try:
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
        raise HTTPException(status_code=404, detail="Source not found")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")


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
    from app.cache import get_cache_stats
    from app.rate_limit import get_rate_limit_status
    from app.guards import get_safety_status
    from app.security import get_security_status
    from app.crypto import is_encryption_configured
    
    # Database connectivity check
    db_status = {"duckdb": False, "sources_db": False}
    try:
        adapter = get_shared_duckdb()
        adapter.execute("SELECT 1")
        db_status["duckdb"] = True
    except Exception:
        pass
    
    try:
        from app.sources import list_sources
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
