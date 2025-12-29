"""
Enterprise Features Routes for SetuPranali

API endpoints for enterprise capabilities:
- Tableau Hyper export
- Embedded analytics
- White-label support
- Multi-region deployment
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.security import require_api_key, TenantContext
from app.enterprise.tableau_hyper import get_hyper_service
from app.enterprise.embedded_analytics import get_embed_service, EmbedConfig
from app.enterprise.white_label import get_white_label_service
from app.enterprise.multi_region import get_multi_region_service

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

# Hyper Export
class HyperExportRequest(BaseModel):
    """Request to export data to Hyper file."""
    dataset_id: str
    output_path: str
    data: Optional[List[Dict[str, Any]]] = None


class HyperQueryExportRequest(BaseModel):
    """Request to export query results to Hyper."""
    output_path: str
    table_name: str = "QueryResult"
    data: List[Dict[str, Any]]


class HyperMultiExportRequest(BaseModel):
    """Request to export multiple datasets."""
    output_path: str
    datasets: Dict[str, List[Dict[str, Any]]]


# Embedded Analytics
class EmbedTokenRequest(BaseModel):
    """Request to create embed token."""
    datasets: List[str]
    permissions: List[str] = Field(default=["query", "filter"])
    filters: Optional[Dict[str, Any]] = None
    rls_context: Optional[Dict[str, Any]] = None
    expiry_hours: int = 24
    max_rows: int = 10000
    allowed_dimensions: Optional[List[str]] = None
    allowed_metrics: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbedCodeRequest(BaseModel):
    """Request for embed code."""
    token: str
    format: str = "iframe"  # iframe, js, url
    config: Optional[Dict[str, Any]] = None


class EmbedQueryRequest(BaseModel):
    """Request for embedded query."""
    token: str
    query: Dict[str, Any]


# White-Label
class BrandingRequest(BaseModel):
    """Request to set branding."""
    colors: Optional[Dict[str, str]] = None
    assets: Optional[Dict[str, str]] = None
    text: Optional[Dict[str, str]] = None
    custom_domain: Optional[str] = None
    features: Optional[Dict[str, bool]] = None


# Multi-Region
class RegionRegistrationRequest(BaseModel):
    """Request to register a region."""
    region_id: str
    name: str
    endpoint: str
    cache_endpoint: Optional[str] = None
    database_endpoint: Optional[str] = None
    priority: int = 0
    weight: int = 100
    data_residency: List[str] = Field(default_factory=list)
    is_primary: bool = False
    latitude: float = 0.0
    longitude: float = 0.0


class RegionSelectionRequest(BaseModel):
    """Request for region selection."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country_code: Optional[str] = None


class CacheSyncRequest(BaseModel):
    """Request to sync cache between regions."""
    from_region: str
    to_region: str
    keys: Optional[List[str]] = None


# =============================================================================
# Tableau Hyper Endpoints
# =============================================================================

@router.post("/hyper/export", tags=["Tableau Hyper"])
async def export_to_hyper(
    request: HyperExportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Export dataset to Tableau Hyper file."""
    service = get_hyper_service()
    
    # Set catalog if available
    try:
        from app.catalog import load_catalog
        catalog = load_catalog()
        service.set_catalog(catalog)
    except Exception:
        pass
    
    if not request.data:
        raise HTTPException(400, "Data is required")
    
    try:
        result = service.export_dataset(
            dataset_id=request.dataset_id,
            data=request.data,
            output_path=request.output_path
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


@router.post("/hyper/export-query", tags=["Tableau Hyper"])
async def export_query_to_hyper(
    request: HyperQueryExportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Export query results to Tableau Hyper file."""
    service = get_hyper_service()
    
    try:
        result = service.export_query_result(
            data=request.data,
            output_path=request.output_path,
            table_name=request.table_name
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


@router.post("/hyper/export-multiple", tags=["Tableau Hyper"])
async def export_multiple_to_hyper(
    request: HyperMultiExportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Export multiple datasets to a single Hyper file."""
    service = get_hyper_service()
    
    try:
        result = service.export_multiple_datasets(
            datasets=request.datasets,
            output_path=request.output_path
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


# =============================================================================
# Embedded Analytics Endpoints
# =============================================================================

@router.post("/embed/token", tags=["Embedded Analytics"])
async def create_embed_token(
    request: EmbedTokenRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Create an embed token for embedding analytics."""
    service = get_embed_service()
    
    try:
        result = service.create_embed_token(
            tenant_id=tenant.tenant_id,
            datasets=request.datasets,
            permissions=request.permissions,
            filters=request.filters,
            rls_context=request.rls_context,
            expiry_hours=request.expiry_hours,
            max_rows=request.max_rows,
            allowed_dimensions=request.allowed_dimensions,
            allowed_metrics=request.allowed_metrics,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Token creation failed: {e}")


@router.post("/embed/code", tags=["Embedded Analytics"])
async def get_embed_code(
    request: EmbedCodeRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Get embeddable code snippet."""
    service = get_embed_service()
    
    try:
        result = service.get_embed_code(
            token=request.token,
            format=request.format,
            config=request.config
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Code generation failed: {e}")


@router.post("/embed/query", tags=["Embedded Analytics"])
async def validate_embed_query(
    request: EmbedQueryRequest
):
    """Validate and process embedded query."""
    service = get_embed_service()
    
    result = service.validate_query(request.token, request.query)
    
    if "error" in result:
        raise HTTPException(403, result)
    
    return result


@router.get("/embed/tokens", tags=["Embedded Analytics"])
async def list_embed_tokens(
    tenant: TenantContext = Depends(require_api_key)
):
    """List active embed tokens for tenant."""
    service = get_embed_service()
    
    tokens = service.list_tokens(tenant.tenant_id)
    return {"tokens": tokens}


@router.delete("/embed/token/{token_id}", tags=["Embedded Analytics"])
async def revoke_embed_token(
    token_id: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Revoke an embed token."""
    service = get_embed_service()
    
    if service.revoke_token(token_id):
        return {"status": "revoked", "token_id": token_id}
    raise HTTPException(404, "Token not found")


# =============================================================================
# White-Label Endpoints
# =============================================================================

@router.get("/branding", tags=["White-Label"])
async def get_branding(
    tenant: TenantContext = Depends(require_api_key)
):
    """Get branding configuration for tenant."""
    service = get_white_label_service()
    return service.get_branding(tenant.tenant_id)


@router.get("/branding/domain/{domain}", tags=["White-Label"])
async def get_branding_by_domain(domain: str):
    """Get branding by custom domain."""
    service = get_white_label_service()
    
    branding = service.get_branding_by_domain(domain)
    if not branding:
        raise HTTPException(404, "No branding found for domain")
    
    return branding


@router.put("/branding", tags=["White-Label"])
async def set_branding(
    request: BrandingRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Set branding configuration."""
    service = get_white_label_service()
    
    return service.set_branding(
        tenant_id=tenant.tenant_id,
        colors=request.colors,
        assets=request.assets,
        text=request.text,
        custom_domain=request.custom_domain,
        features=request.features
    )


@router.get("/branding/css", tags=["White-Label"])
async def get_branding_css(
    tenant: TenantContext = Depends(require_api_key)
):
    """Get generated CSS for branding."""
    service = get_white_label_service()
    css = service.get_css(tenant.tenant_id)
    
    return Response(content=css, media_type="text/css")


@router.get("/branding/css-variables", tags=["White-Label"])
async def get_branding_css_variables(
    tenant: TenantContext = Depends(require_api_key)
):
    """Get CSS variables only."""
    service = get_white_label_service()
    css = service.get_css_variables(tenant.tenant_id)
    
    return Response(content=css, media_type="text/css")


@router.get("/branding/tenants", tags=["White-Label"])
async def list_white_label_tenants(
    tenant: TenantContext = Depends(require_api_key)
):
    """List all white-label tenants."""
    service = get_white_label_service()
    return {"tenants": service.list_tenants()}


@router.delete("/branding/{target_tenant_id}", tags=["White-Label"])
async def delete_branding(
    target_tenant_id: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Delete branding configuration."""
    service = get_white_label_service()
    
    if service.delete_branding(target_tenant_id):
        return {"status": "deleted", "tenant_id": target_tenant_id}
    raise HTTPException(404, "Branding not found")


# =============================================================================
# Multi-Region Endpoints
# =============================================================================

@router.post("/regions", tags=["Multi-Region"])
async def register_region(
    request: RegionRegistrationRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Register a new region."""
    service = get_multi_region_service()
    
    return service.register_region(
        region_id=request.region_id,
        name=request.name,
        endpoint=request.endpoint,
        cache_endpoint=request.cache_endpoint,
        database_endpoint=request.database_endpoint,
        priority=request.priority,
        weight=request.weight,
        data_residency=request.data_residency,
        is_primary=request.is_primary,
        latitude=request.latitude,
        longitude=request.longitude
    )


@router.delete("/regions/{region_id}", tags=["Multi-Region"])
async def unregister_region(
    region_id: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Unregister a region."""
    service = get_multi_region_service()
    return service.unregister_region(region_id)


@router.get("/regions", tags=["Multi-Region"])
async def list_regions(
    tenant: TenantContext = Depends(require_api_key)
):
    """List all regions with health status."""
    service = get_multi_region_service()
    return {"regions": service.get_regions()}


@router.get("/regions/{region_id}/health", tags=["Multi-Region"])
async def get_region_health(
    region_id: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Get detailed health for a region."""
    service = get_multi_region_service()
    
    health = service.get_region_health(region_id)
    if not health:
        raise HTTPException(404, "Region not found")
    
    return health


@router.post("/regions/select", tags=["Multi-Region"])
async def select_region(
    request: RegionSelectionRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Select optimal region for request."""
    service = get_multi_region_service()
    
    context = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "country_code": request.country_code
    }
    
    result = service.select_region(context)
    if not result:
        raise HTTPException(503, "No healthy regions available")
    
    return result


@router.put("/regions/strategy/{strategy}", tags=["Multi-Region"])
async def set_routing_strategy(
    strategy: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Set routing strategy."""
    service = get_multi_region_service()
    return service.set_routing_strategy(strategy)


@router.get("/regions/cache/stats", tags=["Multi-Region"])
async def get_cache_stats(
    region_id: Optional[str] = None,
    tenant: TenantContext = Depends(require_api_key)
):
    """Get distributed cache statistics."""
    service = get_multi_region_service()
    return service.get_cache_stats(region_id)


@router.post("/regions/cache/sync", tags=["Multi-Region"])
async def sync_cache(
    request: CacheSyncRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Sync cache between regions."""
    service = get_multi_region_service()
    
    return service.sync_cache(
        from_region=request.from_region,
        to_region=request.to_region,
        keys=request.keys
    )

