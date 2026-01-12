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
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from app.adapters import get_adapter, list_adapters
from app.adapters.base import AdapterError
from app.sources import get_source_with_config
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
        from app.adapters.duckdb_adapter import get_shared_duckdb
        return get_shared_duckdb()
    
    # Get source config from database
    from app.sources import get_source_with_config
    
    try:
        source = get_source_with_config(source_id)
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
    
    from app.sources import get_source_with_config
    
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
        introspector = SchemaIntrospector(adapter)
        schemas = introspector.get_schemas()
        
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
            
            # Get source table from YAML
            source_ref = dataset.get('source', {}).get('reference', '')
            source_table = source_ref if isinstance(source_ref, str) else ''
            
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
                source_ref = dataset.get('source', {}).get('reference', '')
                source_table = source_ref if isinstance(source_ref, str) else ''
                
                # Convert aggregation string to AggregationType enum
                agg_str = expr.get('agg', 'sum').upper()
                try:
                    agg_type = AggregationType(agg_str)
                except ValueError:
                    agg_type = AggregationType.SUM
                
                new_measures.append(Measure(
                    id=str(uuid.uuid4()),
                    name=metric.get('label', metric.get('name', '')),
                    aggregation=agg_type,
                    source_table=source_table,
                    expression=f"{agg_str}({expr.get('field', '')})",
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
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    # Validate expression
    is_valid, errors = ExpressionValidator.validate(request.expression)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
    
    measure = Measure(
        id=str(uuid.uuid4()),
        name=request.name,
        expression=request.expression,
        aggregation=AggregationType(request.aggregation),
        source_table=request.sourceTable,
        description=request.description,
        format_string=request.formatString,
    )
    
    model.measures.append(measure)
    semantic_manager.update(model)
    
    return measure.to_dict()


@router.put("/semantic/{model_id}/measures/{measure_id}")
async def update_measure(model_id: str, measure_id: str, request: MeasureRequest):
    """Update a measure in the semantic model."""
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
        raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
    
    # Update the measure
    model.measures[measure_idx].name = request.name
    model.measures[measure_idx].expression = request.expression
    model.measures[measure_idx].aggregation = AggregationType(request.aggregation)
    model.measures[measure_idx].source_table = request.sourceTable
    model.measures[measure_idx].description = request.description
    if request.formatString:
        model.measures[measure_idx].format_string = request.formatString
    
    semantic_manager.update(model)
    
    return model.measures[measure_idx].to_dict()


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
    model = semantic_manager.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Semantic model not found")
    
    # Validate expression
    is_valid, errors = ExpressionValidator.validate(request.expression)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {errors}")
    
    # Extract referenced fields
    refs = ExpressionValidator.extract_field_references(request.expression)
    
    calc = CalculatedField(
        id=str(uuid.uuid4()),
        name=request.name,
        expression=request.expression,
        description=request.description,
        result_type=request.resultType,
        referenced_fields=refs,
    )
    
    model.calculated_fields.append(calc)
    semantic_manager.update(model)
    
    return calc.to_dict()


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
    query: SemanticQueryRequest = Body(...)
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
    for dim_name in query.dimensions:
        if not semantic_model.get_dimension(dim_name):
            missing_dims.append(dim_name)
    if missing_dims:
        raise HTTPException(
            status_code=400, 
            detail=f"Dimensions not found in semantic model: {', '.join(missing_dims)}"
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
    
    # Plan query with the appropriate quote character
    try:
        planner = QueryPlanner(erd_model, semantic_model, quote_char=quote_char)
        result = planner.plan(sem_query)
    except Exception as e:
        logger.error(f"Query planning failed: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Query planning failed: {str(e)}. Check that dimension/measure source tables exist in the ERD."
        )
    
    try:
        exec_result = adapter.execute(result.sql, result.params)
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
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")


@router.post("/query/sql")
async def execute_raw_sql(request: RawQueryRequest):
    """
    Execute a raw SQL query.
    
    Validates SQL for safety before execution.
    """
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
    
    try:
        result = adapter.execute(request.sql, request.params if request.params else None)
        return {
            "rows": result.rows,
            "columns": result.columns,
            "rowCount": result.row_count,
            "executionTimeMs": result.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")


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
async def execute_source_query(source_id: str, request: SourceQueryRequest):
    """
    Execute a SQL query directly against a connected data source.
    
    This allows querying tables, views, and materialized views from any
    connected source (MySQL, PostgreSQL, etc.)
    
    Only SELECT queries are allowed for safety.
    """
    import time
    start_time = time.time()
    
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
    
    try:
        # Get adapter for source
        adapter = get_adapter(source["type"], source["config"])
        
        # Execute query
        result = adapter.execute(request.sql, request.params)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "data": result.rows,
            "columns": [{"name": col, "type": "string"} for col in result.columns],
            "rowCount": result.row_count,
            "executionTimeMs": execution_time_ms,
            "source": source["name"],
            "sourceType": source["type"],
        }
    except Exception as e:
        logger.error(f"Source query execution failed: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")

