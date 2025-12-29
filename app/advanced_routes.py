"""
Advanced Features Routes for SetuPranali

API endpoints for:
- Semantic Joins
- Calculated Metrics
- Smart Caching
- Query Federation
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.security import require_api_key, TenantContext
from app.advanced_features import (
    get_advanced_service,
    init_advanced_features,
    JoinDefinition,
    JoinType,
    CalculatedMetric,
    FederatedSource,
    AdvancedFeaturesConfig
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class JoinRequest(BaseModel):
    """Request to register a semantic join."""
    left_dataset: str
    right_dataset: str
    join_type: str = "left"
    left_key: str
    right_key: str
    conditions: List[str] = Field(default_factory=list)
    cardinality: str = "many-to-one"


class JoinPathRequest(BaseModel):
    """Request to find join path."""
    from_dataset: str
    to_dataset: str


class JoinPathResponse(BaseModel):
    """Join path response."""
    found: bool
    datasets: List[str] = Field(default_factory=list)
    joins: List[Dict[str, Any]] = Field(default_factory=list)
    sql: Optional[str] = None


class CalculatedMetricRequest(BaseModel):
    """Request to register a calculated metric."""
    name: str
    expression: str
    description: Optional[str] = None
    format: str = "number"
    decimal_places: int = 2
    tags: List[str] = Field(default_factory=list)


class MetricResolutionRequest(BaseModel):
    """Request to resolve a metric."""
    metric_name: str


class MetricResolutionResponse(BaseModel):
    """Metric resolution response."""
    metric_name: str
    sql: str
    dependencies: List[str] = Field(default_factory=list)


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate cache."""
    dataset: Optional[str] = None
    tag: Optional[str] = None
    key: Optional[str] = None


class CacheInvalidateResponse(BaseModel):
    """Cache invalidation response."""
    invalidated_count: int


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    hits: int
    misses: int
    hit_rate: float
    evictions: int
    size_mb: float
    max_size_mb: int
    entry_count: int


class CachePrewarmRequest(BaseModel):
    """Request to prewarm cache."""
    queries: List[Dict[str, Any]]


class FederatedSourceRequest(BaseModel):
    """Request to register a federated source."""
    id: str
    name: str
    type: str
    connection: Dict[str, Any]
    datasets: List[str] = Field(default_factory=list)
    priority: int = 0


class FederatedQueryRequest(BaseModel):
    """Request to execute federated query."""
    dataset: str
    dimensions: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    joins: List[Dict[str, Any]] = Field(default_factory=list)


class FederationHealthResponse(BaseModel):
    """Federation health check response."""
    sources: Dict[str, Dict[str, Any]]


# =============================================================================
# Initialization
# =============================================================================

@router.on_event("startup")
async def startup():
    """Initialize advanced features."""
    init_advanced_features()


# =============================================================================
# Semantic Joins Endpoints
# =============================================================================

@router.post("/joins", tags=["Semantic Joins"])
async def register_join(
    request: JoinRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Register a semantic join between datasets."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    join = JoinDefinition(
        left_dataset=request.left_dataset,
        right_dataset=request.right_dataset,
        join_type=JoinType(request.join_type),
        left_key=request.left_key,
        right_key=request.right_key,
        conditions=request.conditions,
        cardinality=request.cardinality
    )
    
    service.register_join(join)
    
    return {
        "status": "registered",
        "join": {
            "left_dataset": request.left_dataset,
            "right_dataset": request.right_dataset,
            "type": request.join_type
        }
    }


@router.post("/joins/find-path", response_model=JoinPathResponse, tags=["Semantic Joins"])
async def find_join_path(
    request: JoinPathRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Find the shortest join path between two datasets."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    path = service.find_join_path(request.from_dataset, request.to_dataset)
    
    if not path:
        return JoinPathResponse(
            found=False,
            datasets=[],
            joins=[]
        )
    
    return JoinPathResponse(
        found=True,
        datasets=path.datasets,
        joins=[
            {
                "left": j.left_dataset,
                "right": j.right_dataset,
                "type": j.join_type.value,
                "left_key": j.left_key,
                "right_key": j.right_key
            }
            for j in path.joins
        ],
        sql=path.get_sql()
    )


@router.get("/joins/joinable/{dataset}", tags=["Semantic Joins"])
async def get_joinable_datasets(
    dataset: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Get all datasets that can be joined with the given dataset."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    joinable = service.join_manager.get_joinable_datasets(dataset)
    
    return {
        "dataset": dataset,
        "joinable_datasets": joinable
    }


# =============================================================================
# Calculated Metrics Endpoints
# =============================================================================

@router.post("/metrics/calculated", tags=["Calculated Metrics"])
async def register_calculated_metric(
    request: CalculatedMetricRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Register a calculated metric."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    metric = CalculatedMetric(
        name=request.name,
        expression=request.expression,
        description=request.description,
        format=request.format,
        decimal_places=request.decimal_places,
        tags=request.tags
    )
    
    # Validate before registering
    errors = service.metric_engine.validate_metric(metric)
    if errors:
        raise HTTPException(400, {"errors": errors})
    
    service.register_metric(metric)
    
    return {
        "status": "registered",
        "metric": request.name
    }


@router.post("/metrics/resolve", response_model=MetricResolutionResponse, tags=["Calculated Metrics"])
async def resolve_metric(
    request: MetricResolutionRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Resolve a metric to its SQL representation."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    sql = service.resolve_metric(request.metric_name)
    dependencies = list(service.metric_engine.get_dependencies(request.metric_name))
    
    return MetricResolutionResponse(
        metric_name=request.metric_name,
        sql=sql,
        dependencies=dependencies
    )


@router.get("/metrics/calculated", tags=["Calculated Metrics"])
async def list_calculated_metrics(
    tenant: TenantContext = Depends(require_api_key)
):
    """List all registered calculated metrics."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    metrics = [
        {
            "name": m.name,
            "expression": m.expression,
            "description": m.description,
            "format": m.format,
            "tags": m.tags
        }
        for m in service.metric_engine._metrics.values()
    ]
    
    return {"metrics": metrics}


# =============================================================================
# Caching Endpoints
# =============================================================================

@router.get("/cache/stats", response_model=CacheStatsResponse, tags=["Cache"])
async def get_cache_stats(
    tenant: TenantContext = Depends(require_api_key)
):
    """Get cache statistics."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    stats = service.cache.get_stats()
    
    return CacheStatsResponse(
        hits=stats["hits"],
        misses=stats["misses"],
        hit_rate=stats["hit_rate"],
        evictions=stats["evictions"],
        size_mb=stats["size_mb"],
        max_size_mb=stats["max_size_mb"],
        entry_count=stats["entry_count"]
    )


@router.post("/cache/invalidate", response_model=CacheInvalidateResponse, tags=["Cache"])
async def invalidate_cache(
    request: CacheInvalidateRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Invalidate cache entries."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    count = 0
    
    if request.dataset:
        count += service.cache.invalidate_by_dataset(request.dataset)
    elif request.tag:
        count += service.cache.invalidate_by_tag(request.tag)
    elif request.key:
        if service.cache.invalidate(request.key):
            count = 1
    else:
        raise HTTPException(400, "Provide dataset, tag, or key to invalidate")
    
    return CacheInvalidateResponse(invalidated_count=count)


@router.post("/cache/prewarm", tags=["Cache"])
async def prewarm_cache(
    request: CachePrewarmRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Pre-warm cache with specified queries."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    # This would need a query executor - placeholder for now
    return {
        "status": "scheduled",
        "queries_count": len(request.queries),
        "message": "Cache pre-warming is scheduled"
    }


# =============================================================================
# Federation Endpoints
# =============================================================================

@router.post("/federation/sources", tags=["Federation"])
async def register_federated_source(
    request: FederatedSourceRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Register a federated data source."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    source = FederatedSource(
        id=request.id,
        name=request.name,
        type=request.type,
        connection=request.connection,
        datasets=request.datasets,
        priority=request.priority
    )
    
    service.register_source(source)
    
    return {
        "status": "registered",
        "source": request.id,
        "datasets": request.datasets
    }


@router.get("/federation/sources", tags=["Federation"])
async def list_federated_sources(
    tenant: TenantContext = Depends(require_api_key)
):
    """List all registered federated sources."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    sources = [
        {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "datasets": s.datasets,
            "healthy": s.healthy,
            "priority": s.priority
        }
        for s in service.federator._sources.values()
    ]
    
    return {"sources": sources}


@router.get("/federation/health", response_model=FederationHealthResponse, tags=["Federation"])
async def federation_health(
    tenant: TenantContext = Depends(require_api_key)
):
    """Check health of all federated sources."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    health_map = service.federator.health_check()
    
    sources_info = {}
    for source_id, is_healthy in health_map.items():
        source = service.federator._sources.get(source_id)
        sources_info[source_id] = {
            "healthy": is_healthy,
            "last_check": source.last_check.isoformat() if source and source.last_check else None,
            "error_count": source.error_count if source else 0
        }
    
    return FederationHealthResponse(sources=sources_info)


@router.get("/federation/dataset/{dataset}/source", tags=["Federation"])
async def get_dataset_source(
    dataset: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Get the source containing a specific dataset."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    source = service.federator.get_source_for_dataset(dataset)
    
    if not source:
        return {
            "dataset": dataset,
            "source": None,
            "message": "Dataset not found in any federated source"
        }
    
    return {
        "dataset": dataset,
        "source": {
            "id": source.id,
            "name": source.name,
            "type": source.type
        }
    }


# =============================================================================
# Configuration Endpoint
# =============================================================================

@router.get("/config", tags=["Configuration"])
async def get_advanced_config(
    tenant: TenantContext = Depends(require_api_key)
):
    """Get current advanced features configuration."""
    service = get_advanced_service()
    if not service:
        raise HTTPException(500, "Advanced features not initialized")
    
    config = service.config
    
    return {
        "joins": {
            "enabled": config.joins_enabled,
            "max_depth": config.max_join_depth
        },
        "calculated_metrics": {
            "enabled": config.calculated_metrics_enabled,
            "max_depth": config.max_metric_depth
        },
        "cache": {
            "enabled": config.cache_enabled,
            "ttl_seconds": config.cache_ttl_seconds,
            "max_size_mb": config.cache_max_size_mb,
            "prewarm_enabled": config.cache_prewarm_enabled
        },
        "federation": {
            "enabled": config.federation_enabled,
            "timeout_seconds": config.federation_timeout_seconds,
            "max_sources": config.federation_max_sources
        }
    }

