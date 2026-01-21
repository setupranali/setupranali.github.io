"""
Modeling API Routes

REST API endpoints for the BI modeling UI:
- Source connections
- Schema introspection
- ERD management
- Semantic model management
- Query workbench
"""

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from pydantic import BaseModel, Field

from app.infrastructure.adapters.factory import get_adapter, list_adapters
from app.infrastructure.adapters.base import AdapterError
from app.domain.sources.manager import get_source_with_config
from .schema_introspection import SchemaIntrospector, SchemaInfo, TableInfo, ColumnInfo
from .erd_manager import (
    ERDManager, ERDModel, TableNode, RelationshipEdge,
    Position, Cardinality, JoinType, validate_join_types
)
from .semantic_model import (
    SemanticModelManager, SemanticModel, Dimension, Measure,
    CalculatedField, TimeIntelligence, AggregationType,
    DimensionType, FormatType, ExpressionValidator
)
from .query_planner import (
    QueryPlanner, SemanticQuery, QueryFilter, QuerySort,
    FilterOperator, SortDirection, SQLValidator
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/modeling", tags=["Modeling"])

# Managers (singleton instances)
erd_manager = ERDManager()
semantic_manager = SemanticModelManager()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ConnectionConfig(BaseModel):
    """Data source connection configuration."""
    engine: str = Field(..., description="Database engine type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    ssl: bool = Field(False, description="Use SSL")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional connection options")


class ConnectionTestRequest(BaseModel):
    """Request to test a connection."""
    config: ConnectionConfig


class ConnectionTestResponse(BaseModel):
    """Response from connection test."""
    success: bool
    message: str
    latencyMs: Optional[float] = None
    serverVersion: Optional[str] = None


class SourceCreate(BaseModel):
    """Create a new data source."""
    name: str
    description: Optional[str] = None
    config: ConnectionConfig


class SourceResponse(BaseModel):
    """Data source response."""
    id: str
    name: str
    description: Optional[str]
    engine: str
    status: str  # "active" | "inactive" | "error"
    createdAt: str
    updatedAt: str


class SchemaResponse(BaseModel):
    """Schema list response."""
    schemas: List[Dict[str, Any]]


class TableResponse(BaseModel):
    """Table list response."""
    tables: List[Dict[str, Any]]


class ColumnResponse(BaseModel):
    """Column list response."""
    columns: List[Dict[str, Any]]


class TableNodeRequest(BaseModel):
    """Add table to ERD request."""
    schemaName: str
    tableName: str
    position: Optional[Dict[str, float]] = None
    columns: Optional[List[str]] = None


class RelationshipRequest(BaseModel):
    """Create relationship request."""
    sourceNodeId: str
    sourceColumn: str
    targetNodeId: str
    targetColumn: str
    cardinality: str = "N:1"
    joinType: str = "left"
    name: Optional[str] = None


class DimensionRequest(BaseModel):
    """Create dimension request."""
    name: str
    sourceColumn: str
    sourceTable: str
    description: Optional[str] = None
    dimensionType: str = "categorical"
    format: str = "text"


class MeasureRequest(BaseModel):
    """Create measure request."""
    name: str
    expression: str
    aggregation: str = "SUM"
    sourceTable: Optional[str] = None
    description: Optional[str] = None
    formatString: str = "#,##0.00"


class CalculatedFieldRequest(BaseModel):
    """Create calculated field request."""
    name: str
    expression: str
    description: Optional[str] = None
    resultType: str = "number"


class SemanticQueryRequest(BaseModel):
    """Semantic query request."""
    dimensions: List[str] = Field(default_factory=list)
    measures: List[str] = Field(default_factory=list)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    sorts: List[Dict[str, Any]] = Field(default_factory=list)
    limit: Optional[int] = None
    offset: int = 0


class RawQueryRequest(BaseModel):
    """Raw SQL query request."""
    sql: str
    sourceId: str
    params: List[Any] = Field(default_factory=list)


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

@router.get("/engines")
async def list_supported_engines():
    """List all supported database engines."""
    engines = list_adapters()
    
    # Display name mapping for better UI presentation
    display_names = {
        "duckdb": "DuckDB",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "starrocks": "StarRocks",
        "doris": "Apache Doris",
        "snowflake": "Snowflake",
        "bigquery": "BigQuery",
        "bq": "BigQuery",
        "databricks": "Databricks",
        "dbx": "Databricks",
        "clickhouse": "ClickHouse",
        "ch": "ClickHouse",
        "redshift": "Redshift",
        "rs": "Redshift",
        "trino": "Trino",
        "presto": "Presto",
        "prestodb": "PrestoDB",
        "sqlite": "SQLite",
    }
    
    # Filter out aliases to avoid duplicates in the UI
    primary_engines = ["duckdb", "postgres", "mysql", "starrocks", "doris", 
                       "snowflake", "bigquery", "databricks", "clickhouse", 
                       "redshift", "trino", "presto", "mariadb"]
    
    return {
        "engines": [
            {
                "id": e,
                "name": display_names.get(e, e.replace("_", " ").title()),
                "supportsSchemas": e not in ["sqlite", "duckdb"],
            }
            for e in engines if e in primary_engines
        ]
    }


@router.post("/connections/test", response_model=ConnectionTestResponse)
async def test_connection(request: ConnectionTestRequest):
    """
    Test a database connection without saving.
    
    Validates credentials and connectivity.
    """
    config = request.config
    
    try:
        adapter = get_adapter(
            config.engine,
            {
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "user": config.username,
                "password": config.password,
                "ssl": config.ssl,
                **config.extra,
            }
        )
        
        # Connect and run health check
        import time
        start = time.time()
        adapter.connect()
        health = adapter.health_check()
        latency = (time.time() - start) * 1000
        
        # Get server version if possible
        version = None
        try:
            if config.engine == "postgres":
                result = adapter.execute("SELECT version()")
                version = result.rows[0].get("version", "")[:50] if result.rows else None
            elif config.engine == "mysql":
                result = adapter.execute("SELECT VERSION()")
                version = result.rows[0].get("VERSION()", "") if result.rows else None
        except Exception:
            pass
        
        adapter.disconnect()
        
        return ConnectionTestResponse(
            success=health,
            message="Connection successful" if health else "Health check failed",
            latencyMs=round(latency, 2),
            serverVersion=version,
        )
    
    except AdapterError as e:
        logger.warning(f"Connection test failed: {e}")
        return ConnectionTestResponse(
            success=False,
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
        )


# =============================================================================
# SCHEMA INTROSPECTION
# =============================================================================

def _get_adapter_for_source(source_id: str):
    """
    Get the appropriate adapter for a source.
    
    Falls back to demo DuckDB for 'demo' source.
    """
    if source_id == "demo":
        from app.infrastructure.adapters.duckdb_adapter import get_shared_duckdb
        return get_shared_duckdb()
    
    # Get source config from database
    from app.domain.sources.manager import get_source_with_config, get_source
    
    try:
        # First try to get source with config (includes decrypted credentials)
        source = get_source_with_config(source_id)
    except ValueError as decrypt_error:
        # If decryption fails, provide helpful error message
        logger.error(f"Failed to decrypt source {source_id}: {decrypt_error}")
        source_meta = get_source(source_id)  # This should work (no decryption needed)
        raise HTTPException(
            status_code=500, 
            detail=f"Source '{source_meta.get('name', source_id)}' credentials cannot be decrypted. This usually happens when the encryption key (UBI_SECRET_KEY) has changed. Please re-register the source at /v1/sources with the current encryption key."
        )
    except (KeyError, ValueError) as e:
        logger.warning(f"Source {source_id} not found: {e}")
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    
    source_type = source["type"]
    config = source["config"]
    
    # Create adapter based on source type
    adapter = get_adapter(source_type, config)
    adapter.connect()
    
    return adapter


def _get_source_type(source_id: str) -> str:
    """
    Get the source type for a given source ID.
    
    Returns the database type (e.g., 'starrocks', 'postgresql', 'duckdb').
    """
    if source_id == "demo":
        return "duckdb"
    
    from app.domain.sources.manager import get_source_with_config
    
    try:
        source = get_source_with_config(source_id)
        return source.get("type", "unknown").lower()
    except (KeyError, ValueError):
        return "unknown"


@router.get("/sources/{source_id}/schemas", response_model=SchemaResponse)
async def get_schemas(source_id: str):
    """
    Get list of schemas/databases for a source.
    
    Lazy-loads schema list for large databases.
    """
    try:
        adapter = _get_adapter_for_source(source_id)
        # Get source type to help with engine-specific queries
        source_type = _get_source_type(source_id)
        logger.info(f"Fetching schemas for source {source_id} (type: {source_type}, adapter engine: {adapter.ENGINE})")
        
        introspector = SchemaIntrospector(adapter)
        schemas = introspector.get_schemas()
        
        logger.info(f"Found {len(schemas)} schemas for source {source_id}")
        
        return SchemaResponse(
            schemas=[s.to_dict(include_tables=False) for s in schemas]
        )
    except HTTPException:
        raise
    except AdapterError as e:
        logger.error(f"Failed to get schemas for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to source: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/sources/{source_id}/schemas/{schema_name}/tables", response_model=TableResponse)
async def get_tables(source_id: str, schema_name: str):
    """
    Get list of tables in a schema.
    """
    try:
        adapter = _get_adapter_for_source(source_id)
        introspector = SchemaIntrospector(adapter)
        tables = introspector.get_tables(schema_name)
        
        return TableResponse(
            tables=[t.to_dict(include_columns=False) for t in tables]
        )
    except HTTPException:
        raise
    except AdapterError as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to source: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/sources/{source_id}/schemas/{schema_name}/tables/{table_name}/columns", response_model=ColumnResponse)
async def get_columns(source_id: str, schema_name: str, table_name: str):
    """
    Get columns for a specific table.
    
    Includes data types, nullability, keys.
    """
    try:
        adapter = _get_adapter_for_source(source_id)
        introspector = SchemaIntrospector(adapter)
        columns = introspector.get_columns(schema_name, table_name)
        
        return ColumnResponse(
            columns=[c.to_dict() for c in columns]
        )
    except HTTPException:
        raise
    except AdapterError as e:
        logger.error(f"Failed to get columns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to source: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting columns: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/sources/{source_id}/schemas/{schema_name}/tables/{table_name}/sample")
async def get_sample_data(
    source_id: str, 
    schema_name: str, 
    table_name: str,
    limit: int = Query(100, le=1000)
):
    """
    Get sample data from a table.
    """
    try:
        adapter = _get_adapter_for_source(source_id)
        introspector = SchemaIntrospector(adapter)
        data = introspector.get_sample_data(schema_name, table_name, limit)
        
        return {"rows": data, "count": len(data)}
    except HTTPException:
        raise
    except AdapterError as e:
        logger.error(f"Failed to get sample data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to source: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting sample data: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/sources/{source_id}/search")
async def search_tables(
    source_id: str,
    q: str = Query(..., min_length=1),
    schema_name: Optional[str] = None
):
    """
    Search for tables by name.
    """
    try:
        adapter = _get_adapter_for_source(source_id)
        introspector = SchemaIntrospector(adapter)
        results = introspector.search_tables(q, schema_name)
        
        return {"results": [t.to_dict(include_columns=False) for t in results]}
    except HTTPException:
        raise
    except AdapterError as e:
        logger.error(f"Failed to search tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to source: {str(e)}")
    except Exception as e:
        logger.error(f"Error searching tables: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# =============================================================================
# ERD MANAGEMENT
# =============================================================================

@router.post("/erd")
async def create_erd_model(
    name: str = Body(...),
    sourceId: str = Body(...),
    description: Optional[str] = Body(None)
):
    """Create a new ERD model."""
    model = ERDModel(
        id=str(uuid.uuid4()),
        name=name,
        source_id=sourceId,
        description=description,
    )
    created = erd_manager.create(model)
    return created.to_dict()


@router.get("/erd")
async def list_erd_models(source_id: Optional[str] = None):
    """List ERD models, optionally filtered by source."""
    if source_id:
        models = erd_manager.list_by_source(source_id)
    else:
        models = erd_manager.list_all()
    return {"models": [m.to_dict() for m in models]}


@router.get("/erd/{model_id}")
async def get_erd_model(model_id: str):
    """Get an ERD model by ID."""
    model = erd_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    return model.to_dict()


@router.put("/erd/{model_id}")
async def update_erd_model(model_id: str, data: Dict[str, Any] = Body(...)):
    """Update an ERD model."""
    existing = erd_manager.get(model_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    # Update fields
    if "name" in data:
        existing.name = data["name"]
    if "description" in data:
        existing.description = data["description"]
    if "nodes" in data:
        existing.nodes = [TableNode.from_dict(n) for n in data["nodes"]]
    if "edges" in data:
        existing.edges = [RelationshipEdge.from_dict(e) for e in data["edges"]]
    
    updated = erd_manager.update(existing)
    return updated.to_dict()


@router.delete("/erd/{model_id}")
async def delete_erd_model(model_id: str):
    """Delete an ERD model."""
    deleted = erd_manager.delete(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ERD model not found")
    return {"deleted": True}


@router.post("/erd/{model_id}/nodes")
async def add_table_node(model_id: str, request: TableNodeRequest):
    """Add a table node to the ERD canvas."""
    model = erd_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    node = TableNode(
        id=str(uuid.uuid4()),
        schema_name=request.schemaName,
        table_name=request.tableName,
        position=Position.from_dict(request.position or {"x": 100, "y": 100}),
        columns=request.columns or [],
    )
    
    model.add_node(node)
    erd_manager.update(model)
    
    return node.to_dict()


@router.delete("/erd/{model_id}/nodes/{node_id}")
async def remove_table_node(model_id: str, node_id: str):
    """Remove a table node from the ERD."""
    model = erd_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    model.remove_node(node_id)
    erd_manager.update(model)
    
    return {"deleted": True}


@router.post("/erd/{model_id}/edges")
async def add_relationship(model_id: str, request: RelationshipRequest):
    """Create a relationship between two tables."""
    model = erd_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    # Validate nodes exist
    source_node = model.get_node(request.sourceNodeId)
    target_node = model.get_node(request.targetNodeId)
    
    if not source_node:
        raise HTTPException(status_code=400, detail="Source node not found")
    if not target_node:
        raise HTTPException(status_code=400, detail="Target node not found")
    
    edge = RelationshipEdge(
        id=str(uuid.uuid4()),
        source_node_id=request.sourceNodeId,
        source_column=request.sourceColumn,
        target_node_id=request.targetNodeId,
        target_column=request.targetColumn,
        cardinality=Cardinality(request.cardinality),
        join_type=JoinType(request.joinType),
        name=request.name,
    )
    
    model.add_edge(edge)
    erd_manager.update(model)
    
    return edge.to_dict()


@router.delete("/erd/{model_id}/edges/{edge_id}")
async def remove_relationship(model_id: str, edge_id: str):
    """Remove a relationship from the ERD."""
    model = erd_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    model.remove_edge(edge_id)
    erd_manager.update(model)
    
    return {"deleted": True}


@router.post("/erd/{model_id}/validate")
async def validate_erd(model_id: str):
    """Validate an ERD model."""
    model = erd_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    errors = model.validate()
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


# =============================================================================
# SEMANTIC MODEL MANAGEMENT
# =============================================================================

@router.post("/semantic")
async def create_semantic_model(
    name: str = Body(...),
    sourceId: str = Body(...),
    erdModelId: Optional[str] = Body(None),
    description: Optional[str] = Body(None)
):
    """Create a new semantic model."""
    model = SemanticModel(
        id=str(uuid.uuid4()),
        name=name,
        source_id=sourceId,
        erd_model_id=erdModelId,
        description=description,
    )
    created = semantic_manager.create(model)
    return created.to_dict()


@router.get("/semantic")
async def list_semantic_models(source_id: Optional[str] = None):
    """List semantic models."""
    if source_id:
        models = semantic_manager.list_by_source(source_id)
    else:
        models = semantic_manager.list_all()
    return {"models": [m.to_dict() for m in models]}


@router.get("/semantic/{model_id}")
async def get_semantic_model(model_id: str):
    """Get a semantic model by ID."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    return model.to_dict()


@router.put("/semantic/{model_id}")
async def update_semantic_model(model_id: str, data: Dict[str, Any] = Body(...)):
    """Update a semantic model."""
    existing = semantic_manager.get(model_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    if "name" in data:
        existing.name = data["name"]
    if "description" in data:
        existing.description = data["description"]
    if "erdModelId" in data:
        existing.erd_model_id = data["erdModelId"]
    if "dimensions" in data:
        existing.dimensions = [Dimension.from_dict(d) for d in data["dimensions"]]
    if "measures" in data:
        existing.measures = [Measure.from_dict(m) for m in data["measures"]]
    if "calculatedFields" in data:
        existing.calculated_fields = [CalculatedField.from_dict(c) for c in data["calculatedFields"]]
    
    updated = semantic_manager.update(existing)
    return updated.to_dict()


@router.delete("/semantic/{model_id}")
async def delete_semantic_model(model_id: str):
    """Delete a semantic model."""
    deleted = semantic_manager.delete(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    return {"deleted": True}


@router.get("/semantic/{model_id}/yaml")
async def get_semantic_model_yaml(model_id: str):
    """Generate YAML contract content for a semantic model."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")

    yaml_content = _generate_semantic_model_yaml(model)
    return {
        "content": yaml_content,
        "lastModified": model.updated_at.isoformat() if model.updated_at else None,
    }


@router.put("/semantic/{model_id}/from-yaml")
async def update_semantic_model_from_yaml(model_id: str, content: str = Body(..., embed=True)):
    """
    Update a semantic model from YAML contract content.
    Parses the YAML and updates dimensions, measures, and calculated fields.
    """
    import yaml
    
    existing = semantic_manager.get(model_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    try:
        # Parse YAML content
        data = yaml.safe_load(content)
        if not data:
            raise HTTPException(status_code=400, detail="Empty or invalid YAML content")
        
        # Extract datasets from YAML
        datasets = data.get('datasets', [])
        if not datasets:
            raise HTTPException(status_code=400, detail="No datasets found in YAML")
        
        # Use the first dataset (assuming single model per contract)
        dataset = datasets[0]
        
        # Update model name and description if provided
        if 'name' in dataset:
            existing.name = dataset['name']
        if 'description' in dataset:
            existing.description = dataset['description']
        
        # Parse dimensions from YAML
        new_dimensions = []
        yaml_dimensions = dataset.get('dimensions', [])
        for dim in yaml_dimensions:
            # Find source field from fields section
            source_column = dim.get('field', dim.get('name', ''))
            dim_type = 'string'  # Default type
            
            # Try to find field type from fields section
            fields = dataset.get('fields', [])
            for field in fields:
                if field.get('name') == source_column:
                    semantic_type = field.get('semanticType', '')
                    data_type = field.get('type', 'string')
                    dim_type = _map_yaml_type_to_dimension_type(data_type, semantic_type)
                    break
            
            # Get source table from YAML - use dimension-specific sourceTable if available, otherwise fall back to dataset source
            source_table = dim.get('sourceTable') or dataset.get('source', {}).get('reference', '')
            if not source_table:
                source_table = ''
            
            # Convert dimension type string to DimensionType enum
            try:
                dimension_type_enum = DimensionType(dim_type.lower() if dim_type else 'categorical')
            except ValueError:
                dimension_type_enum = DimensionType.CATEGORICAL
            
            new_dimensions.append(Dimension(
                id=str(uuid.uuid4()),
                name=dim.get('label', dim.get('name', '')),
                dimension_type=dimension_type_enum,
                source_table=source_table,
                source_column=source_column,
            ))
        
        # Parse metrics (measures and calculated fields)
        new_measures = []
        new_calculated_fields = []
        yaml_metrics = dataset.get('metrics', [])
        
        for metric in yaml_metrics:
            expr = metric.get('expression', {})
            expr_type = expr.get('type', 'aggregation')
            
            if expr_type == 'calculated':
                # This is a calculated field
                new_calculated_fields.append(CalculatedField(
                    id=str(uuid.uuid4()),
                    name=metric.get('label', metric.get('name', '')),
                    expression=expr.get('formula', ''),
                    result_type=metric.get('returnType', 'number'),
                ))
            else:
                # This is a regular measure with aggregation
                # Use metric-specific sourceTable if available, otherwise fall back to dataset source
                source_table = metric.get('sourceTable') or dataset.get('source', {}).get('reference', '')
                if not source_table:
                    source_table = ''
                
                # Convert aggregation string to AggregationType enum
                agg_str = expr.get('agg', 'sum').upper()
                try:
                    agg_type = AggregationType(agg_str)
                except ValueError:
                    agg_type = AggregationType.SUM
                
                # Get field name from expression
                field_name = expr.get('field', '')
                if not field_name:
                    field_name = '*'
                
                new_measures.append(Measure(
                    id=str(uuid.uuid4()),
                    name=metric.get('label', metric.get('name', '')),
                    aggregation=agg_type,
                    source_table=source_table,
                    expression=f"{agg_str}({field_name})",
                ))
        
        # Update the model
        existing.dimensions = new_dimensions
        existing.measures = new_measures
        existing.calculated_fields = new_calculated_fields
        
        updated = semantic_manager.update(existing)
        
        return {
            "success": True,
            "message": f"Semantic model '{updated.name}' updated from YAML contract",
            "model": updated.to_dict(),
            "stats": {
                "dimensions": len(new_dimensions),
                "measures": len(new_measures),
                "calculatedFields": len(new_calculated_fields),
            }
        }
        
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML syntax: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating model from YAML: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update model from YAML: {str(e)}")


def _map_yaml_type_to_dimension_type(data_type: str, semantic_type: str) -> str:
    """Map YAML field types to DimensionType enum values (categorical, time, geo, hierarchical)."""
    # Check semantic type first
    if semantic_type in ('time', 'timestamp', 'datetime'):
        return 'time'
    if semantic_type in ('geo', 'geo_city', 'geo_country', 'geo_state'):
        return 'geo'
    if semantic_type in ('hierarchical', 'hierarchy'):
        return 'hierarchical'
    # Default to categorical for everything else
    if semantic_type in ('dimension', 'metric', ''):
        return 'categorical'
    
    # Fall back to data type - map to DimensionType values
    type_mapping = {
        'string': 'categorical',
        'varchar': 'categorical',
        'text': 'categorical',
        'integer': 'categorical',
        'int': 'categorical',
        'bigint': 'categorical',
        'double': 'categorical',
        'float': 'categorical',
        'decimal': 'categorical',
        'numeric': 'categorical',
        'timestamp': 'time',
        'datetime': 'time',
        'date': 'time',
        'boolean': 'categorical',
        'bool': 'categorical',
    }
    return type_mapping.get(data_type.lower(), 'categorical')


def _generate_semantic_model_yaml(model: SemanticModel) -> str:
    import yaml
    import logging
    logger = logging.getLogger(__name__)

    dataset_id = _slugify(model.name or "semantic_model")
    source_table = _infer_source_table(model)
    logger.debug(f"Generating YAML for model {model.id}, inferred source_table: {source_table}")
    fields = []
    dimensions = []
    metrics = []

    for dim in model.dimensions:
        field_name = dim.source_column or _slugify(dim.name)
        data_type, semantic_type = _map_dimension_to_yaml_types(dim.dimension_type)
        fields.append(
            {
                "name": field_name,
                "type": data_type,
                "semanticType": semantic_type,
            }
        )
        # Ensure sourceTable is always included (use individual or fallback)
        # Handle empty strings explicitly - empty string should use fallback
        dim_source_table = dim.source_table if dim.source_table and dim.source_table.strip() else (source_table if source_table and source_table.strip() else "unknown_table")
        logger.debug(f"Dimension {dim.name}: dim.source_table={dim.source_table!r}, inferred={source_table!r}, final={dim_source_table!r}")
        dim_dict = {
            "name": _slugify(dim.name),
            "field": field_name,
            "label": dim.name,
            "sourceTable": dim_source_table,  # Always include sourceTable
        }
        # Verify sourceTable is in dict
        if "sourceTable" not in dim_dict:
            logger.error(f"ERROR: sourceTable missing from dim_dict for {dim.name}!")
        dimensions.append(dim_dict)

    for measure in model.measures:
        # Extract column name from expression (e.g., "SUM(tax_amount)" -> "tax_amount")
        # or "COUNT(*)" -> "*", or just "column_name" -> "column_name"
        field_name = measure.expression.strip()
        import re
        # Remove aggregation function wrapper: SUM(...), COUNT(...), etc.
        match = re.match(r'^\w+\s*\((.*)\)$', field_name, re.IGNORECASE)
        if match:
            field_name = match.group(1).strip()
        # Remove any table prefixes: schema.table.column -> column
        if '.' in field_name:
            field_name = field_name.split('.')[-1]
        
        # Ensure sourceTable is always included (use individual or fallback)
        # Handle empty strings explicitly - empty string should use fallback
        measure_source_table = measure.source_table if measure.source_table and measure.source_table.strip() else (source_table if source_table and source_table.strip() else "unknown_table")
        logger.debug(f"Measure {measure.name}: measure.source_table={measure.source_table!r}, inferred={source_table!r}, final={measure_source_table!r}")
        metric_dict = {
            "name": _slugify(measure.name),
            "label": measure.name,
            "expression": {
                "type": "aggregation",
                "agg": measure.aggregation.value.lower(),
                "field": field_name,  # Just the column name, not the full expression
            },
            "returnType": "double",
            "sourceTable": measure_source_table,  # Always include sourceTable
        }
        # Verify sourceTable is in dict
        if "sourceTable" not in metric_dict:
            logger.error(f"ERROR: sourceTable missing from metric_dict for {measure.name}!")
        metrics.append(metric_dict)

    for calc in model.calculated_fields:
        metrics.append(
            {
                "name": _slugify(calc.name),
                "label": calc.name,
                "expression": {
                    "type": "calculated",
                    "formula": calc.expression,
                },
                "returnType": calc.result_type or "double",
            }
        )

    payload = {
        "datasets": [
            {
                "id": dataset_id,
                "name": model.name,
                "description": model.description or f"Semantic model for {model.name}",
                "tags": ["semantic-model", "auto-generated"],
                "defaultTimezone": "UTC",
                "source": {
                    "engine": "auto",
                    "type": "table",
                    "reference": source_table,
                },
                "rls": {"enabled": False},
                "incremental": {"enabled": False},
                "fields": fields,
                "dimensions": dimensions,
                "metrics": metrics,
            }
        ]
    }

    header = [
        f"# Data Contract: {model.name}",
        "# Auto-generated from Semantic Model",
        f"# Last updated: {model.updated_at.isoformat() if model.updated_at else ''}",
        "",
    ]
    # Debug: Check if sourceTable is in payload before YAML dump
    for dim in payload["datasets"][0].get("dimensions", []):
        if "sourceTable" not in dim:
            logger.error(f"ERROR: sourceTable missing from dimension {dim.get('name')} in payload before YAML dump!")
    for metric in payload["datasets"][0].get("metrics", []):
        if "sourceTable" not in metric:
            logger.error(f"ERROR: sourceTable missing from metric {metric.get('name')} in payload before YAML dump!")
    
    yaml_body = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False).rstrip()
    
    # Debug: Check if sourceTable appears in YAML output
    if "sourceTable" not in yaml_body:
        logger.error("ERROR: sourceTable not found in YAML output! This indicates YAML serialization issue.")
    else:
        logger.debug(f"✅ sourceTable found in YAML output. Count: {yaml_body.count('sourceTable')}")
    
    return "\n".join(header) + yaml_body + "\n"


def _map_dimension_to_yaml_types(dimension_type: DimensionType) -> tuple[str, str]:
    if dimension_type == DimensionType.TIME:
        return "timestamp", "time"
    if dimension_type == DimensionType.GEO:
        return "string", "geo_city"
    if dimension_type == DimensionType.HIERARCHICAL:
        return "string", "dimension"
    return "string", "dimension"


def _slugify(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return safe or "value"


def _infer_source_table(model: SemanticModel) -> str:
    for dim in model.dimensions:
        if dim.source_table:
            return dim.source_table
    for measure in model.measures:
        if measure.source_table:
            return measure.source_table
    return "unknown_table"


@router.post("/semantic/{model_id}/dimensions")
async def add_dimension(model_id: str, request: DimensionRequest):
    """Add a dimension to the semantic model."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    dimension = Dimension(
        id=str(uuid.uuid4()),
        name=request.name,
        source_column=request.sourceColumn,
        source_table=request.sourceTable,
        description=request.description,
        dimension_type=DimensionType(request.dimensionType),
        default_format=FormatType(request.format),
    )
    
    model.dimensions.append(dimension)
    semantic_manager.update(model)
    
    return dimension.to_dict()


@router.put("/semantic/{model_id}/dimensions/{dimension_id}")
async def update_dimension(model_id: str, dimension_id: str, request: DimensionRequest):
    """Update a dimension in the semantic model."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    # Find the dimension
    dimension_idx = None
    for i, d in enumerate(model.dimensions):
        if d.id == dimension_id:
            dimension_idx = i
            break
    
    if dimension_idx is None:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    # Update the dimension
    model.dimensions[dimension_idx].name = request.name
    model.dimensions[dimension_idx].source_column = request.sourceColumn
    model.dimensions[dimension_idx].source_table = request.sourceTable
    model.dimensions[dimension_idx].description = request.description
    model.dimensions[dimension_idx].dimension_type = DimensionType(request.dimensionType)
    if request.format:
        model.dimensions[dimension_idx].default_format = FormatType(request.format)
    
    semantic_manager.update(model)
    
    return model.dimensions[dimension_idx].to_dict()


@router.delete("/semantic/{model_id}/dimensions/{dimension_id}")
async def remove_dimension(model_id: str, dimension_id: str):
    """Remove a dimension from the semantic model."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    model.dimensions = [d for d in model.dimensions if d.id != dimension_id]
    semantic_manager.update(model)
    
    return {"deleted": True}


@router.post("/semantic/{model_id}/measures")
async def add_measure(model_id: str, request: MeasureRequest):
    """Add a measure to the semantic model."""
    try:
        model = semantic_manager.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Semantic model not found")
        
        # Validate expression
        is_valid, errors = ExpressionValidator.validate(request.expression)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
        
        # Convert aggregation to enum (handle case-insensitive and spaces)
        try:
            # Normalize: convert to uppercase and replace spaces with underscores
            agg_normalized = request.aggregation.upper().replace(" ", "_")
            aggregation = AggregationType(agg_normalized)
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid aggregation type: {request.aggregation}, normalized: {agg_normalized if 'agg_normalized' in locals() else 'N/A'}, error: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid aggregation type: {request.aggregation}. Must be one of: {[a.value for a in AggregationType]}"
            )
        
        measure = Measure(
            id=str(uuid.uuid4()),
            name=request.name,
            expression=request.expression,
            aggregation=aggregation,
            source_table=request.sourceTable,
            description=request.description,
            format_string=request.formatString,
        )
        
        model.measures.append(measure)
        semantic_manager.update(model)
        
        return measure.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding measure to model {model_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add measure: {str(e)}")


@router.put("/semantic/{model_id}/measures/{measure_id}")
async def update_measure(model_id: str, measure_id: str, request: MeasureRequest):
    """Update a measure in the semantic model."""
    try:
        logger.info(f"Updating measure {measure_id} in model {model_id}. Request: name={request.name}, aggregation={request.aggregation}, expression={request.expression}")
        
        model = semantic_manager.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Semantic model not found")
        
        # Find the measure
        measure_idx = None
        for i, m in enumerate(model.measures):
            if m.id == measure_id:
                measure_idx = i
                break
        
        if measure_idx is None:
            raise HTTPException(status_code=404, detail="Measure not found")
        
        # Validate expression
        is_valid, errors = ExpressionValidator.validate(request.expression)
        if not is_valid:
            logger.warning(f"Expression validation failed for measure {measure_id}: {errors}")
            raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
        
        # Convert aggregation to enum (handle case-insensitive and spaces)
        if not request.aggregation:
            logger.error(f"Missing aggregation type in request")
            raise HTTPException(status_code=400, detail="Aggregation type is required")
        
        try:
            # Normalize: convert to uppercase and replace spaces with underscores
            agg_normalized = str(request.aggregation).upper().replace(" ", "_")
            aggregation = AggregationType(agg_normalized)
            logger.debug(f"Aggregation normalized: {request.aggregation} -> {agg_normalized} -> {aggregation.value}")
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid aggregation type: {request.aggregation}, normalized: {agg_normalized if 'agg_normalized' in locals() else 'N/A'}, error: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid aggregation type: {request.aggregation}. Must be one of: {[a.value for a in AggregationType]}"
            )
        
        # Update the measure
        model.measures[measure_idx].name = request.name
        model.measures[measure_idx].expression = request.expression
        model.measures[measure_idx].aggregation = aggregation
        model.measures[measure_idx].source_table = request.sourceTable
        model.measures[measure_idx].description = request.description
        if request.formatString:
            model.measures[measure_idx].format_string = request.formatString
        
        try:
            updated_model = semantic_manager.update(model)
            logger.info(f"Successfully updated measure {measure_id} in model {model_id}")
        except Exception as update_error:
            logger.error(f"Failed to update semantic model {model_id}: {update_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save measure update: {str(update_error)}")
        
        return model.measures[measure_idx].to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating measure {measure_id} in model {model_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update measure: {str(e)}")


@router.delete("/semantic/{model_id}/measures/{measure_id}")
async def remove_measure(model_id: str, measure_id: str):
    """Remove a measure from the semantic model."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    model.measures = [m for m in model.measures if m.id != measure_id]
    semantic_manager.update(model)
    
    return {"deleted": True}


@router.post("/semantic/{model_id}/calculated")
async def add_calculated_field(model_id: str, request: CalculatedFieldRequest):
    """Add a calculated field."""
    try:
        logger.info(f"Adding calculated field to model {model_id}: name={request.name}, expression={request.expression}")
        
        model = semantic_manager.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Semantic model not found")
        
        # Validate expression
        is_valid, errors = ExpressionValidator.validate(request.expression)
        if not is_valid:
            logger.warning(f"Expression validation failed for calculated field '{request.name}': {errors}")
            raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
        
        # Extract referenced fields
        refs = ExpressionValidator.extract_field_references(request.expression)
        logger.debug(f"Extracted field references: {refs}")
        
        calc = CalculatedField(
            id=str(uuid.uuid4()),
            name=request.name,
            expression=request.expression,
            description=request.description,
            result_type=request.resultType or "number",
            referenced_fields=refs,
        )
        
        model.calculated_fields.append(calc)
        
        try:
            updated_model = semantic_manager.update(model)
            logger.info(f"Successfully added calculated field '{request.name}' to model {model_id}")
        except Exception as update_error:
            logger.error(f"Failed to update semantic model {model_id}: {update_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save calculated field: {str(update_error)}")
        
        return calc.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding calculated field to model {model_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add calculated field: {str(e)}")


@router.put("/semantic/{model_id}/calculated/{field_id}")
async def update_calculated_field(model_id: str, field_id: str, request: CalculatedFieldRequest):
    """Update a calculated field."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    # Find the calculated field
    field_idx = None
    for i, f in enumerate(model.calculated_fields):
        if f.id == field_id:
            field_idx = i
            break
    
    if field_idx is None:
        raise HTTPException(status_code=404, detail="Calculated field not found")
    
    # Validate expression
    is_valid, errors = ExpressionValidator.validate(request.expression)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
    
    # Extract referenced fields
    refs = ExpressionValidator.extract_field_references(request.expression)
    
    # Update the calculated field
    model.calculated_fields[field_idx].name = request.name
    model.calculated_fields[field_idx].expression = request.expression
    model.calculated_fields[field_idx].description = request.description
    model.calculated_fields[field_idx].result_type = request.resultType
    model.calculated_fields[field_idx].referenced_fields = refs
    
    semantic_manager.update(model)
    
    return model.calculated_fields[field_idx].to_dict()


@router.post("/semantic/{model_id}/validate")
async def validate_semantic_model(model_id: str):
    """Validate a semantic model."""
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    errors = model.validate()
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


# =============================================================================
# QUERY WORKBENCH
# =============================================================================

@router.post("/query/semantic")
async def execute_semantic_query(
    erdModelId: str = Body(...),
    semanticModelId: str = Body(...),
    query: SemanticQueryRequest = Body(...),
    http_request: Request = None
):
    """
    Execute a semantic query.
    
    Resolves dimensions and measures from the semantic model,
    builds joins from the ERD, and executes the query.
    """
    erd_model = erd_manager.get(erdModelId)
    if not erd_model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    semantic_model = semantic_manager.get(semanticModelId)
    if not semantic_model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    # Validation: Check if ERD has tables
    if not erd_model.nodes:
        raise HTTPException(
            status_code=400, 
            detail="ERD model has no tables. Please add tables to the ERD canvas first."
        )
    
    # Validation: Check if semantic model has any dimensions or measures
    if not semantic_model.dimensions and not semantic_model.measures:
        raise HTTPException(
            status_code=400, 
            detail="Semantic model has no dimensions or measures. Please add at least one dimension or measure."
        )
    
    # Validation: Check if requested dimensions exist
    missing_dims = []
    available_dim_names = [d.name for d in semantic_model.dimensions]
    for dim_name in query.dimensions:
        if not semantic_model.get_dimension(dim_name):
            missing_dims.append(dim_name)
    if missing_dims:
        # Provide helpful error message with available dimensions
        available_list = ', '.join(available_dim_names[:10])  # Show first 10
        if len(available_dim_names) > 10:
            available_list += f", ... (and {len(available_dim_names) - 10} more)"
        raise HTTPException(
            status_code=400, 
            detail=f"Dimensions not found in semantic model: {', '.join(missing_dims)}. "
                   f"Available dimensions: {available_list if available_list else 'none'}"
        )
    
    # Validation: Check if requested measures exist
    missing_measures = []
    for measure_name in query.measures:
        if not semantic_model.get_measure(measure_name) and not semantic_model.get_calculated_field(measure_name):
            missing_measures.append(measure_name)
    if missing_measures:
        raise HTTPException(
            status_code=400, 
            detail=f"Measures not found in semantic model: {', '.join(missing_measures)}"
        )
    
    # Validation: Check that dimension/measure source tables exist in ERD
    erd_table_names = {node.table_name for node in erd_model.nodes}
    invalid_dimensions = []
    invalid_measures = []
    
    for dim_name in query.dimensions:
        dim = semantic_model.get_dimension(dim_name)
        if dim and dim.source_table:
            # Check if source_table exists in ERD (handle schema.table format)
            table_name = dim.source_table.split('.')[-1] if '.' in dim.source_table else dim.source_table
            if table_name not in erd_table_names:
                invalid_dimensions.append(f"{dim_name} (source_table: {dim.source_table} not in ERD)")
    
    for measure_name in query.measures:
        measure = semantic_model.get_measure(measure_name)
        if measure and measure.source_table:
            # Check if source_table exists in ERD (handle schema.table format)
            table_name = measure.source_table.split('.')[-1] if '.' in measure.source_table else measure.source_table
            if table_name not in erd_table_names:
                invalid_measures.append(f"{measure_name} (source_table: {measure.source_table} not in ERD)")
    
    if invalid_dimensions or invalid_measures:
        error_parts = []
        if invalid_dimensions:
            error_parts.append(f"Dimensions with invalid source_table: {', '.join(invalid_dimensions)}")
        if invalid_measures:
            error_parts.append(f"Measures with invalid source_table: {', '.join(invalid_measures)}")
        error_parts.append(f"Available tables in ERD: {', '.join(sorted(erd_table_names))}")
        raise HTTPException(
            status_code=400,
            detail=". ".join(error_parts) + ". Please update the source_table for these fields in the semantic model."
        )
    
    # Build semantic query
    sem_query = SemanticQuery(
        dimensions=query.dimensions,
        measures=query.measures,
        filters=[QueryFilter.from_dict(f) for f in query.filters],
        sorts=[QuerySort.from_dict(s) for s in query.sorts],
        limit=query.limit,
        offset=query.offset,
    )
    
    # Get the correct adapter for the ERD model's source
    try:
        adapter = _get_adapter_for_source(erd_model.source_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get adapter for source {erd_model.source_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to connect to data source: {str(e)}"
        )
    
    # Determine the appropriate quote character for the database type
    # MySQL/StarRocks/ClickHouse use backticks, PostgreSQL/DuckDB use double quotes
    source_type = _get_source_type(erd_model.source_id)
    if source_type in ('mysql', 'starrocks', 'clickhouse', 'mariadb'):
        quote_char = '`'
    elif source_type in ('mssql', 'sqlserver'):
        quote_char = '['
    else:
        # PostgreSQL, DuckDB, Snowflake, BigQuery use double quotes
        quote_char = '"'
    
    # Plan query with the appropriate quote character and dialect
    try:
        # Determine dialect from source type for SQLGlot conversion
        planner_dialect = source_type if source_type else "postgres"
        planner = QueryPlanner(erd_model, semantic_model, quote_char=quote_char, dialect=planner_dialect)
        result = planner.plan(sem_query)
    except Exception as e:
        logger.error(f"Query planning failed: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Query planning failed: {str(e)}. Check that dimension/measure source tables exist in the ERD."
        )
    
    import time
    from datetime import datetime, timezone
    from app.infrastructure.observability import get_analytics, QueryRecord
    
    query_start_time = time.perf_counter()
    query_id = str(uuid.uuid4())
    query_success = False
    query_error = None
    
    try:
        # Log the generated SQL for debugging
        logger.info(f"Executing semantic query SQL (dialect: {planner_dialect}): {result.sql}")
        exec_result = adapter.execute(result.sql, result.params)
        query_success = True
        query_duration_ms = (time.perf_counter() - query_start_time) * 1000
        
        # Record query analytics
        try:
            analytics = get_analytics()
            if analytics and analytics.config.analytics_enabled:
                # Extract dimensions and metrics from semantic query
                dimensions = [d.name if hasattr(d, 'name') else str(d) for d in query.dimensions] if query.dimensions else []
                metrics = [m.name if hasattr(m, 'name') else str(m) for m in query.measures] if query.measures else []
                
                # Get request context
                api_key_hash = None
                source_ip = None
                user_agent = None
                if http_request:
                    api_key = http_request.headers.get("X-API-Key")
                    if api_key:
                        # Hash API key for analytics (optional - don't fail if hashing unavailable)
                        try:
                            import hashlib
                            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        except Exception:
                            api_key_hash = None
                    source_ip = http_request.client.host if http_request.client else None
                    user_agent = http_request.headers.get("User-Agent")
                
                record = QueryRecord(
                    query_id=query_id,
                    timestamp=datetime.now(timezone.utc),
                    dataset=f"semantic:{semanticModelId}",
                    dimensions=dimensions,
                    metrics=metrics,
                    filters={f.field: f.value for f in query.filters} if query.filters else None,
                    duration_ms=query_duration_ms,
                    rows_returned=exec_result.row_count,
                    bytes_scanned=0,
                    cache_hit=False,
                    api_key_hash=api_key_hash,
                    tenant_id=None,
                    user_id=None,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    success=True,
                    error_code=None,
                    error_message=None,
                )
                analytics.record_query(record)
                logger.debug(f"Semantic query recorded in analytics: {query_id}, model={semanticModelId}")
        except Exception as e:
            logger.warning(f"Failed to record semantic query analytics: {e}")
        
        return {
            "rows": exec_result.rows,
            "columns": exec_result.columns,
            "rowCount": exec_result.row_count,
            "executionTimeMs": exec_result.execution_time_ms,
            "sql": result.sql,
            "tablesUsed": result.tables_used,
            "warnings": result.warnings,
        }
    except Exception as e:
        query_error = str(e)
        query_duration_ms = (time.perf_counter() - query_start_time) * 1000
        
        # Record failed query analytics
        try:
            analytics = get_analytics()
            if analytics and analytics.config.analytics_enabled:
                api_key_hash = None
                source_ip = None
                user_agent = None
                if http_request:
                    api_key = http_request.headers.get("X-API-Key")
                    if api_key:
                        # Hash API key for analytics (optional - don't fail if hashing unavailable)
                        try:
                            import hashlib
                            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        except Exception:
                            api_key_hash = None
                    source_ip = http_request.client.host if http_request.client else None
                    user_agent = http_request.headers.get("User-Agent")
                
                record = QueryRecord(
                    query_id=query_id,
                    timestamp=datetime.now(timezone.utc),
                    dataset=f"semantic:{semanticModelId}",
                    dimensions=[],
                    metrics=[],
                    filters=None,
                    duration_ms=query_duration_ms,
                    rows_returned=0,
                    bytes_scanned=0,
                    cache_hit=False,
                    api_key_hash=api_key_hash,
                    tenant_id=None,
                    user_id=None,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    success=False,
                    error_code="EXECUTION_ERROR",
                    error_message=query_error,
                )
                analytics.record_query(record)
        except Exception as analytics_error:
            logger.warning(f"Failed to record failed query analytics: {analytics_error}")
        
        logger.error(f"Query execution failed. SQL: {result.sql}, Error: {e}", exc_info=True)
        error_msg = str(e)
        # Provide more helpful error messages for column not found errors
        if "Unknown column" in error_msg or "does not exist" in error_msg.lower() or "column" in error_msg.lower():
            error_msg += ". This usually means a dimension or measure has an incorrect source_table. Please check that each field's source_table matches the table where the column actually exists."
        raise HTTPException(status_code=400, detail=f"Query execution failed: {error_msg}")


@router.post("/query/sql")
async def execute_raw_sql(request: RawQueryRequest, http_request: Request = None):
    """
    Execute a raw SQL query.
    
    Validates SQL for safety before execution.
    """
    import time
    import uuid
    from datetime import datetime, timezone
    from app.infrastructure.observability import get_analytics, QueryRecord
    
    query_start_time = time.perf_counter()
    query_id = str(uuid.uuid4())
    
    # Validate SQL
    is_safe, issues = SQLValidator.validate(request.sql)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"SQL validation failed: {issues}")
    
    if not SQLValidator.is_select_only(request.sql):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    # Get the correct adapter for the source
    try:
        adapter = _get_adapter_for_source(request.sourceId)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get adapter for source {request.sourceId}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to connect to data source: {str(e)}"
        )
    
    query_success = False
    query_error = None
    
    try:
        result = adapter.execute(request.sql, request.params if request.params else None)
        query_success = True
        query_duration_ms = (time.perf_counter() - query_start_time) * 1000
        
        # Record query analytics
        try:
            analytics = get_analytics()
            if analytics and analytics.config.analytics_enabled:
                # Extract dimensions and metrics from SQL (basic parsing)
                dimensions = []
                metrics = []
                sql_upper = request.sql.upper()
                
                # Try to extract column names from SELECT clause
                if "SELECT" in sql_upper:
                    select_part = request.sql.split("SELECT")[1].split("FROM")[0] if "FROM" in sql_upper else ""
                    # Simple extraction - could be improved
                    columns = [col.strip().split()[0].strip() for col in select_part.split(",") if col.strip()]
                    dimensions = columns  # Treat all as dimensions for now
                
                # Get request context
                api_key_hash = None
                source_ip = None
                user_agent = None
                if http_request:
                    api_key = http_request.headers.get("X-API-Key")
                    if api_key:
                        # Hash API key for analytics (optional - don't fail if hashing unavailable)
                        try:
                            import hashlib
                            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        except Exception:
                            api_key_hash = None
                    source_ip = http_request.client.host if http_request.client else None
                    user_agent = http_request.headers.get("User-Agent")
                
                record = QueryRecord(
                    query_id=query_id,
                    timestamp=datetime.now(timezone.utc),
                    dataset=f"source:{request.sourceId}",  # Use source ID as dataset identifier
                    dimensions=dimensions,
                    metrics=metrics,
                    filters=None,
                    duration_ms=query_duration_ms,
                    rows_returned=result.row_count,
                    bytes_scanned=0,
                    cache_hit=False,
                    api_key_hash=api_key_hash,
                    tenant_id=None,
                    user_id=None,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    success=True,
                    error_code=None,
                    error_message=None,
                )
                analytics.record_query(record)
                logger.debug(f"Query recorded in analytics: {query_id}, source={request.sourceId}")
        except Exception as e:
            logger.warning(f"Failed to record query analytics: {e}")
        
        return {
            "rows": result.rows,
            "columns": result.columns,
            "rowCount": result.row_count,
            "executionTimeMs": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        error_msg = str(e)
        # Provide more helpful error messages for column not found errors
        if "Unknown column" in error_msg or "does not exist" in error_msg.lower() or "column" in error_msg.lower():
            error_msg += ". This usually means a dimension or measure has an incorrect source_table. Please check that each field's source_table matches the table where the column actually exists."
        raise HTTPException(status_code=400, detail=f"Query execution failed: {error_msg}")


@router.post("/query/explain")
async def explain_semantic_query(
    erdModelId: str = Body(...),
    semanticModelId: str = Body(...),
    query: SemanticQueryRequest = Body(...)
):
    """
    Explain a semantic query without executing.
    
    Returns the generated SQL and query plan details.
    """
    erd_model = erd_manager.get(erdModelId)
    if not erd_model:
        raise HTTPException(status_code=404, detail="ERD model not found")
    
    semantic_model = semantic_manager.get(semanticModelId)
    if not semantic_model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    sem_query = SemanticQuery(
        dimensions=query.dimensions,
        measures=query.measures,
        filters=[QueryFilter.from_dict(f) for f in query.filters],
        sorts=[QuerySort.from_dict(s) for s in query.sorts],
        limit=query.limit,
        offset=query.offset,
    )
    
    planner = QueryPlanner(erd_model, semantic_model)
    explanation = planner.explain(sem_query)
    
    return explanation


@router.post("/query/validate-expression")
async def validate_expression(expression: str = Body(..., embed=True)):
    """Validate a measure or calculated field expression."""
    is_valid, errors = ExpressionValidator.validate(expression)
    refs = ExpressionValidator.extract_field_references(expression)
    
    return {
        "valid": is_valid,
        "errors": errors,
        "referencedFields": refs,
    }


class SourceQueryRequest(BaseModel):
    """Request to execute SQL against a specific source."""
    sql: str
    source_id: str
    params: Optional[dict] = None


@router.post("/sources/{source_id}/query")
async def execute_source_query(source_id: str, request: SourceQueryRequest, http_request: Request):
    """
    Execute a SQL query directly against a connected data source.
    
    This allows querying tables, views, and materialized views from any
    connected source (MySQL, PostgreSQL, etc.)
    
    Only SELECT queries are allowed for safety.
    """
    import time
    import uuid
    from datetime import datetime, timezone
    from app.infrastructure.observability import get_analytics, QueryRecord
    from fastapi import Request
    
    start_time = time.perf_counter()
    query_id = str(uuid.uuid4())
    
    # Get source configuration
    source = get_source_with_config(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Validate SQL - only SELECT allowed
    sql_upper = request.sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    # Check for dangerous patterns
    dangerous_patterns = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE']
    for pattern in dangerous_patterns:
        if pattern in sql_upper:
            raise HTTPException(status_code=400, detail=f"Query contains disallowed operation: {pattern}")
    
    query_success = False
    query_error = None
    
    try:
        # Get adapter for source
        adapter = get_adapter(source["type"], source["config"])
        
        # Execute query
        result = adapter.execute(request.sql, request.params)
        
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        query_success = True
        
        # Record query analytics
        try:
            analytics = get_analytics()
            if analytics and analytics.config.analytics_enabled:
                # For direct source queries, extract columns from SQL
                # These are raw SQL queries, not semantic queries, so they may not have metrics
                # They might only have columns (which we'll treat as dimensions)
                dimensions = []
                metrics = []  # Source queries typically don't have semantic metrics
                sql_upper = request.sql.upper()
                
                # Try to extract column names from SELECT clause
                if "SELECT" in sql_upper:
                    select_part = request.sql.split("SELECT")[1].split("FROM")[0] if "FROM" in sql_upper else ""
                    # Extract column names (handle aliases, functions, etc.)
                    columns = []
                    for col in select_part.split(","):
                        col = col.strip()
                        if col:
                            # Get the base column name (before AS or space)
                            # Handle: "column_name", "table.column", "COUNT(*) as cnt", etc.
                            if " AS " in col.upper():
                                col = col.split(" AS ")[-1].strip()
                            elif " " in col and not col.startswith("("):
                                # If it's not a function, might be "table.column alias"
                                parts = col.split()
                                col = parts[-1] if len(parts) > 1 else parts[0]
                            # Remove quotes and get base name
                            col = col.strip('"').strip("'").strip("`")
                            if col:
                                columns.append(col)
                    dimensions = columns  # Source query columns are treated as dimensions
                
                # Get request context
                api_key_hash = None
                source_ip = None
                user_agent = None
                if http_request:
                    api_key = http_request.headers.get("X-API-Key")
                    if api_key:
                        # Hash API key for analytics (optional - don't fail if hashing unavailable)
                        try:
                            import hashlib
                            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        except Exception:
                            api_key_hash = None
                    source_ip = http_request.client.host if http_request.client else None
                    user_agent = http_request.headers.get("User-Agent")
                
                record = QueryRecord(
                    query_id=query_id,
                    timestamp=datetime.now(timezone.utc),
                    dataset=f"source:{source_id}",
                    dimensions=dimensions,
                    metrics=metrics,
                    filters=None,
                    duration_ms=execution_time_ms,
                    rows_returned=result.row_count,
                    bytes_scanned=0,
                    cache_hit=False,
                    api_key_hash=api_key_hash,
                    tenant_id=None,
                    user_id=None,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    success=True,
                    error_code=None,
                    error_message=None,
                )
                analytics.record_query(record)
                logger.info(f"✅ Source query recorded in analytics: {query_id}, source={source_id}, dataset={record.dataset}, duration={execution_time_ms}ms, rows={result.row_count}, dimensions={dimensions}")
            else:
                if analytics is None:
                    logger.warning(f"⚠️ Analytics module not initialized - cannot record source query")
                elif not analytics.config.analytics_enabled:
                    logger.debug(f"Analytics disabled - skipping source query recording")
                else:
                    logger.warning(f"⚠️ Analytics condition failed: analytics={analytics is not None}, enabled={analytics.config.analytics_enabled if analytics else 'N/A'}")
        except Exception as e:
            logger.error(f"❌ Failed to record source query analytics: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "data": result.rows,
            "columns": [{"name": col, "type": "string"} for col in result.columns],
            "rowCount": result.row_count,
            "executionTimeMs": execution_time_ms,
            "source": source["name"],
            "sourceType": source["type"],
        }
    except Exception as e:
        query_error = str(e)
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Record failed query analytics
        try:
            analytics = get_analytics()
            if analytics and analytics.config.analytics_enabled:
                # For failed source queries, we don't have column info, so dimensions/metrics are empty
                api_key_hash = None
                source_ip = None
                user_agent = None
                if http_request:
                    api_key = http_request.headers.get("X-API-Key")
                    if api_key:
                        # Hash API key for analytics (optional - don't fail if hashing unavailable)
                        try:
                            import hashlib
                            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        except Exception:
                            api_key_hash = None
                    source_ip = http_request.client.host if http_request.client else None
                    user_agent = http_request.headers.get("User-Agent")
                
                record = QueryRecord(
                    query_id=query_id,
                    timestamp=datetime.now(timezone.utc),
                    dataset=f"source:{source_id}",
                    dimensions=[],  # No dimensions for failed queries
                    metrics=[],     # Source queries don't have semantic metrics
                    filters=None,
                    duration_ms=execution_time_ms,
                    rows_returned=0,
                    bytes_scanned=0,
                    cache_hit=False,
                    api_key_hash=api_key_hash,
                    tenant_id=None,
                    user_id=None,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    success=False,
                    error_code="EXECUTION_ERROR",
                    error_message=query_error,
                )
                analytics.record_query(record)
        except Exception as analytics_error:
            logger.warning(f"Failed to record failed source query analytics: {analytics_error}")
        
        logger.error(f"Source query execution failed: {e}")
        error_msg = str(e)
        # Provide more helpful error messages for column not found errors
        if "Unknown column" in error_msg or "does not exist" in error_msg.lower() or "column" in error_msg.lower():
            error_msg += ". This usually means a dimension or measure has an incorrect source_table. Please check that each field's source_table matches the table where the column actually exists."
        raise HTTPException(status_code=400, detail=f"Query execution failed: {error_msg}")
