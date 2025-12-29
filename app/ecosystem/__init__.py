"""
SetuPranali Ecosystem Integrations

Provides interoperability with:
- dbt (metrics import)
- Cube.js (schema compatibility)
- LookML (model import)
- Power BI Service (dataset sync)
"""

from app.ecosystem.dbt_integration import (
    DbtManifestParser,
    DbtCatalogGenerator,
    DbtSyncService,
    get_dbt_sync_service
)

from app.ecosystem.cube_compatibility import (
    CubeSchemaParser,
    CubeToSetuPranaliConverter,
    SetuPranaliToCubeExporter,
    CubeCompatibilityService,
    get_cube_service
)

from app.ecosystem.lookml_import import (
    LookMLParser,
    LookMLToSetuPranaliConverter,
    LookMLImportService,
    get_lookml_service
)

from app.ecosystem.powerbi_sync import (
    PowerBIClient,
    PowerBIDataset,
    PowerBISyncService,
    get_powerbi_service
)

__all__ = [
    # dbt
    "DbtManifestParser",
    "DbtCatalogGenerator", 
    "DbtSyncService",
    "get_dbt_sync_service",
    
    # Cube.js
    "CubeSchemaParser",
    "CubeToSetuPranaliConverter",
    "SetuPranaliToCubeExporter",
    "CubeCompatibilityService",
    "get_cube_service",
    
    # LookML
    "LookMLParser",
    "LookMLToSetuPranaliConverter",
    "LookMLImportService",
    "get_lookml_service",
    
    # Power BI
    "PowerBIClient",
    "PowerBIDataset",
    "PowerBISyncService",
    "get_powerbi_service",
]

