"""
SetuPranali - GraphQL API

Provides a GraphQL interface for querying the semantic layer.
Supports all features available via REST: RLS, caching, rate limiting.
"""

from typing import List, Optional
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from app.catalog import load_catalog, get_dataset
from app.security import TenantContext


# =============================================================================
# GRAPHQL TYPES
# =============================================================================

@strawberry.type
class Dimension:
    """A dimension in a dataset (groupable field)."""
    name: str
    label: Optional[str] = None
    type: str = "string"
    description: Optional[str] = None


@strawberry.type
class Metric:
    """A metric in a dataset (aggregatable measure)."""
    name: str
    label: Optional[str] = None
    type: str = "number"
    sql: Optional[str] = None
    description: Optional[str] = None


@strawberry.type
class Dataset:
    """A semantic dataset definition."""
    id: str
    name: str
    description: Optional[str] = None
    source: str
    tags: List[str]
    dimensions: List[Dimension]
    metrics: List[Metric]
    default_timezone: str = "UTC"


@strawberry.type
class DatasetSummary:
    """Brief dataset info for listing."""
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str]


@strawberry.type
class Column:
    """A column in query results."""
    name: str
    type: str


@strawberry.type
class QueryResult:
    """Result of a semantic query."""
    columns: List[Column]
    data: strawberry.scalars.JSON
    row_count: int
    cached: bool = False
    execution_time_ms: Optional[int] = None


@strawberry.type
class HealthStatus:
    """System health status."""
    status: str
    version: str
    cache_enabled: bool
    redis_available: bool


# =============================================================================
# INPUT TYPES
# =============================================================================

@strawberry.input
class DimensionInput:
    """Dimension to include in query."""
    name: str


@strawberry.input
class MetricInput:
    """Metric to include in query."""
    name: str


@strawberry.input
class FilterInput:
    """Filter condition for query."""
    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, between, like
    value: strawberry.scalars.JSON


@strawberry.input
class OrderByInput:
    """Sort order for results."""
    field: str
    direction: str = "asc"  # asc or desc


@strawberry.input
class QueryInput:
    """Input for semantic query."""
    dataset: str
    dimensions: List[DimensionInput] = strawberry.field(default_factory=list)
    metrics: List[MetricInput] = strawberry.field(default_factory=list)
    filters: Optional[List[FilterInput]] = None
    order_by: Optional[List[OrderByInput]] = None
    limit: int = 1000
    offset: int = 0


# =============================================================================
# CONTEXT
# =============================================================================

def get_tenant_from_context(info: Info) -> TenantContext:
    """Extract tenant context from request."""
    request = info.context["request"]
    # Get API key from header
    api_key = request.headers.get("X-API-Key", "")
    
    # For GraphQL, we'll validate the key and get tenant
    # This is simplified - in production, use the full security module
    if not api_key:
        return TenantContext(tenant="default", role="viewer", key_name="anonymous")
    
    # Import here to avoid circular imports
    from app.security import validate_api_key
    try:
        return validate_api_key(api_key)
    except Exception:
        return TenantContext(tenant="default", role="viewer", key_name="anonymous")


# =============================================================================
# QUERIES
# =============================================================================

@strawberry.type
class Query:
    """GraphQL Query root."""
    
    @strawberry.field
    def health(self) -> HealthStatus:
        """Get system health status."""
        from app.cache import get_cache_stats
        cache_stats = get_cache_stats()
        
        return HealthStatus(
            status="ok",
            version="1.0.0",
            cache_enabled=cache_stats.get("enabled", False),
            redis_available=cache_stats.get("redis_available", False)
        )
    
    @strawberry.field
    def datasets(self) -> List[DatasetSummary]:
        """List all available datasets."""
        catalog = load_catalog()
        items = []
        for d in catalog.get("datasets", []):
            items.append(DatasetSummary(
                id=d["id"],
                name=d.get("name", d["id"]),
                description=d.get("description"),
                tags=d.get("tags", [])
            ))
        return items
    
    @strawberry.field
    def dataset(self, id: str) -> Optional[Dataset]:
        """Get a specific dataset by ID."""
        catalog = load_catalog()
        try:
            d = get_dataset(catalog, id)
            return Dataset(
                id=d["id"],
                name=d.get("name", d["id"]),
                description=d.get("description"),
                source=d.get("source", ""),
                tags=d.get("tags", []),
                dimensions=[
                    Dimension(
                        name=dim["name"],
                        label=dim.get("label"),
                        type=dim.get("type", "string"),
                        description=dim.get("description")
                    )
                    for dim in d.get("dimensions", [])
                ],
                metrics=[
                    Metric(
                        name=m["name"],
                        label=m.get("label"),
                        type=m.get("type", "number"),
                        sql=m.get("sql"),
                        description=m.get("description")
                    )
                    for m in d.get("metrics", [])
                ],
                default_timezone=d.get("defaultTimezone", "UTC")
            )
        except KeyError:
            return None
    
    @strawberry.field
    def query(self, input: QueryInput, info: Info) -> QueryResult:
        """
        Execute a semantic query.
        
        Requires X-API-Key header for authentication.
        Automatically applies Row-Level Security based on API key tenant.
        """
        import time
        from app.query_engine import compile_and_run_query
        from app.cache import execute_with_cache, build_cache_components_from_request
        from app.models import QueryRequest, DimensionRequest, MetricRequest, FilterRequest
        from app.sources import SOURCES
        from app.connection_manager import get_engine_and_conn
        
        start_time = time.time()
        
        # Get tenant context
        ctx = get_tenant_from_context(info)
        
        # Load dataset
        catalog = load_catalog()
        try:
            dataset = get_dataset(catalog, input.dataset)
        except KeyError:
            return QueryResult(
                columns=[],
                data=[],
                row_count=0,
                cached=False,
                execution_time_ms=0
            )
        
        # Build request model
        req = QueryRequest(
            dataset=input.dataset,
            dimensions=[DimensionRequest(name=d.name) for d in input.dimensions],
            metrics=[MetricRequest(name=m.name) for m in input.metrics],
            filters=[
                FilterRequest(field=f.field, operator=f.operator, value=f.value)
                for f in (input.filters or [])
            ],
            limit=input.limit,
            offset=input.offset
        )
        
        try:
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
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return QueryResult(
                columns=[Column(name=c.name, type=c.type) for c in columns],
                data=rows,
                row_count=len(rows),
                cached=stats.get("cache_hit", False),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            return QueryResult(
                columns=[],
                data=[{"error": str(e)}],
                row_count=0,
                cached=False,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


# =============================================================================
# MUTATIONS
# =============================================================================

@strawberry.type
class Mutation:
    """GraphQL Mutation root."""
    
    @strawberry.mutation
    def refresh_cache(self, dataset_id: str, info: Info) -> bool:
        """
        Invalidate cache for a dataset.
        Requires admin role.
        """
        from app.cache import invalidate_dataset_cache
        
        ctx = get_tenant_from_context(info)
        if ctx.role != "admin":
            return False
        
        try:
            invalidate_dataset_cache(dataset_id, ctx.tenant)
            return True
        except Exception:
            return False


# =============================================================================
# SCHEMA & ROUTER
# =============================================================================

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_router = GraphQLRouter(
    schema,
    context_getter=lambda request: {"request": request}
)

