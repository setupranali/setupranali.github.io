"""
Ecosystem Integration Routes for SetuPranali

API endpoints for:
- dbt integration
- Cube.js compatibility
- LookML import
- Power BI sync
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.core.security import require_api_key, TenantContext
from app.ecosystem.dbt_integration import get_dbt_sync_service
from app.ecosystem.cube_compatibility import get_cube_service
from app.ecosystem.lookml_import import get_lookml_service
from app.ecosystem.powerbi_sync import get_powerbi_service

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class DbtLocalImportRequest(BaseModel):
    """Request to import from local dbt manifest."""
    manifest_path: str
    output_path: str = "catalog.yaml"
    include_models: Optional[List[str]] = None
    exclude_models: Optional[List[str]] = None
    include_tags: Optional[List[str]] = None


class DbtCloudImportRequest(BaseModel):
    """Request to import from dbt Cloud."""
    account_id: str
    api_token: str
    job_id: int
    output_path: str = "catalog.yaml"


class CubeImportRequest(BaseModel):
    """Request to import Cube.js schema."""
    schema_path: str
    output_path: str = "catalog.yaml"


class CubeExportRequest(BaseModel):
    """Request to export to Cube.js schema."""
    catalog_path: str = "catalog.yaml"
    output_dir: str = "cube_schema"


class LookMLImportRequest(BaseModel):
    """Request to import LookML project."""
    project_path: str
    output_path: str = "catalog.yaml"


class PowerBIConfigRequest(BaseModel):
    """Request to configure Power BI connection."""
    client_id: str
    client_secret: str
    tenant_id: str
    workspace_id: Optional[str] = None


class PowerBISyncRequest(BaseModel):
    """Request to sync with Power BI."""
    catalog_path: str = "catalog.yaml"
    dataset_name: Optional[str] = None
    replace_existing: bool = False


class PowerBIPushDataRequest(BaseModel):
    """Request to push data to Power BI."""
    dataset_id: str
    table_name: str
    data: List[Dict[str, Any]]


# =============================================================================
# dbt Integration Endpoints
# =============================================================================

@router.post("/dbt/import/local", tags=["dbt"])
async def import_dbt_local(
    request: DbtLocalImportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Import catalog from local dbt manifest.json."""
    service = get_dbt_sync_service()
    
    try:
        service.configure_local(request.manifest_path)
        result = service.sync(
            output_path=request.output_path,
            include_models=request.include_models,
            exclude_models=request.exclude_models,
            include_tags=request.include_tags
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Import failed: {e}")


@router.post("/dbt/import/cloud", tags=["dbt"])
async def import_dbt_cloud(
    request: DbtCloudImportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Import catalog from dbt Cloud."""
    service = get_dbt_sync_service()
    
    try:
        service.configure_cloud(
            account_id=request.account_id,
            api_token=request.api_token,
            job_id=request.job_id
        )
        result = service.sync(output_path=request.output_path)
        return result
    except Exception as e:
        raise HTTPException(500, f"Import failed: {e}")


@router.get("/dbt/models", tags=["dbt"])
async def list_dbt_models(
    tenant: TenantContext = Depends(require_api_key)
):
    """List available dbt models (after import)."""
    service = get_dbt_sync_service()
    return {"models": service.get_models()}


@router.get("/dbt/metrics", tags=["dbt"])
async def list_dbt_metrics(
    tenant: TenantContext = Depends(require_api_key)
):
    """List available dbt metrics (after import)."""
    service = get_dbt_sync_service()
    return {"metrics": service.get_metrics()}


# =============================================================================
# Cube.js Compatibility Endpoints
# =============================================================================

@router.post("/cube/import", tags=["Cube.js"])
async def import_cube_schema(
    request: CubeImportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Import Cube.js schema to SetuPranali catalog."""
    service = get_cube_service()
    
    try:
        result = service.import_cube_schema(request.schema_path)
        
        # Save catalog
        from app.ecosystem.cube_compatibility import CubeToSetuPranaliConverter
        converter = CubeToSetuPranaliConverter(service.parser)
        converter.save_catalog(request.output_path)
        
        result["output_path"] = request.output_path
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Import failed: {e}")


@router.post("/cube/export", tags=["Cube.js"])
async def export_to_cube_schema(
    request: CubeExportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Export SetuPranali catalog to Cube.js schema."""
    service = get_cube_service()
    
    try:
        result = service.export_to_cube(
            catalog_path=request.catalog_path,
            output_dir=request.output_dir
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


@router.get("/cube/meta", tags=["Cube.js"])
async def get_cube_meta(
    tenant: TenantContext = Depends(require_api_key)
):
    """Get Cube.js compatible meta response (for compatibility)."""
    from app.domain.sources import load_catalog
    
    try:
        catalog = load_catalog()
        service = get_cube_service()
        return service.get_cube_meta(catalog)
    except Exception as e:
        raise HTTPException(500, f"Failed to generate meta: {e}")


# =============================================================================
# LookML Import Endpoints
# =============================================================================

@router.post("/lookml/import", tags=["LookML"])
async def import_lookml_project(
    request: LookMLImportRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Import LookML project to SetuPranali catalog."""
    service = get_lookml_service()
    
    try:
        result = service.import_project(
            project_path=request.project_path,
            output_path=request.output_path
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Import failed: {e}")


@router.get("/lookml/views", tags=["LookML"])
async def list_lookml_views(
    tenant: TenantContext = Depends(require_api_key)
):
    """List available LookML views (after import)."""
    service = get_lookml_service()
    return {"views": service.get_views()}


@router.get("/lookml/explores", tags=["LookML"])
async def list_lookml_explores(
    tenant: TenantContext = Depends(require_api_key)
):
    """List available LookML explores (after import)."""
    service = get_lookml_service()
    return {"explores": service.get_explores()}


# =============================================================================
# Power BI Sync Endpoints
# =============================================================================

@router.post("/powerbi/configure", tags=["Power BI"])
async def configure_powerbi(
    request: PowerBIConfigRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Configure Power BI connection."""
    service = get_powerbi_service()
    
    try:
        service.configure(
            client_id=request.client_id,
            client_secret=request.client_secret,
            tenant_id=request.tenant_id,
            workspace_id=request.workspace_id
        )
        return {"status": "configured"}
    except Exception as e:
        raise HTTPException(500, f"Configuration failed: {e}")


@router.get("/powerbi/workspaces", tags=["Power BI"])
async def list_powerbi_workspaces(
    tenant: TenantContext = Depends(require_api_key)
):
    """List available Power BI workspaces."""
    service = get_powerbi_service()
    
    try:
        workspaces = service.get_workspaces()
        return {"workspaces": workspaces}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to list workspaces: {e}")


@router.get("/powerbi/datasets", tags=["Power BI"])
async def list_powerbi_datasets(
    tenant: TenantContext = Depends(require_api_key)
):
    """List Power BI datasets in workspace."""
    service = get_powerbi_service()
    
    try:
        datasets = service.get_datasets()
        return {"datasets": datasets}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to list datasets: {e}")


@router.post("/powerbi/sync", tags=["Power BI"])
async def sync_powerbi(
    request: PowerBISyncRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Sync SetuPranali catalog to Power BI Service."""
    service = get_powerbi_service()
    
    try:
        result = service.sync_catalog(
            catalog_path=request.catalog_path,
            dataset_name=request.dataset_name,
            replace_existing=request.replace_existing
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Sync failed: {e}")


@router.post("/powerbi/push", tags=["Power BI"])
async def push_data_to_powerbi(
    request: PowerBIPushDataRequest,
    tenant: TenantContext = Depends(require_api_key)
):
    """Push data to Power BI dataset."""
    service = get_powerbi_service()
    
    try:
        result = service.push_data(
            dataset_id=request.dataset_id,
            table_name=request.table_name,
            data=request.data
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Push failed: {e}")


@router.post("/powerbi/refresh/{dataset_id}", tags=["Power BI"])
async def refresh_powerbi_dataset(
    dataset_id: str,
    tenant: TenantContext = Depends(require_api_key)
):
    """Trigger Power BI dataset refresh."""
    service = get_powerbi_service()
    
    try:
        result = service.refresh_dataset(dataset_id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Refresh failed: {e}")

