"""
OData Interface for Power BI Connectivity

This module provides a minimal OData v4 interface that allows Power BI
to connect via "Get Data → OData Feed". It acts as a transport layer
on top of the existing query engine - NO new SQL logic.

Supported OData features (Power BI subset):
- $select: Choose columns (maps to dimensions + metrics)
- $filter: Basic predicates (eq, ne, gt, ge, lt, le, in)
- $top/$skip: Pagination
- $orderby: Sorting

INCREMENTAL REFRESH (Power BI):
Power BI sends $filter expressions using ge/lt on the incremental column.
Example: "order_date ge 2025-01-01 and order_date lt 2025-02-01"

This module detects these patterns and converts them to incrementalFrom/To
parameters for the QueryRequest, enabling efficient incremental refresh.

All queries internally route to compile_and_run_query().
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import Response
from typing import Any, Dict, List, Optional, Tuple
import re
import xml.etree.ElementTree as ET

from app.domain.sources.catalog import load_catalog, get_dataset
from app.shared.types.models import QueryRequest, QueryDimension, QueryMetric, OrderBy
from app.domain.query.engine import compile_and_run_query
from app.domain.sources.manager import SOURCES
from app.connection_manager import get_engine_and_conn
from app.core.security import require_api_key, TenantContext
from app.infrastructure.cache.redis_cache import execute_with_cache, build_cache_components_from_request
from app.shared.exceptions.errors import dataset_not_found, internal_error, SetuPranaliError

router = APIRouter()

# =============================================================================
# TYPE MAPPING: Catalog types → OData EDM types
# =============================================================================

EDM_TYPE_MAP = {
    "string": "Edm.String",
    "int32": "Edm.Int32",
    "int64": "Edm.Int64",
    "float": "Edm.Double",
    "double": "Edm.Double",
    "decimal": "Edm.Decimal",
    "boolean": "Edm.Boolean",
    "date": "Edm.Date",
    "datetime": "Edm.DateTimeOffset",
    "timestamp": "Edm.DateTimeOffset",
    "json": "Edm.String",
    "bytes": "Edm.Binary",
}


def _get_edm_type(catalog_type: str) -> str:
    """Map catalog field type to OData EDM type."""
    return EDM_TYPE_MAP.get(catalog_type, "Edm.String")


# =============================================================================
# EDMX METADATA GENERATION
# =============================================================================

def generate_edmx(datasets: List[dict], service_root: str) -> str:
    """
    Generate minimal EDMX XML for Power BI.
    
    Creates one EntityType per dataset with properties derived from:
    - Dataset fields (raw columns)
    - Dimension names
    - Metric names
    
    Power BI uses this to build the field picker in the query editor.
    """
    # XML namespaces for OData v4
    ns_edmx = "http://docs.oasis-open.org/odata/ns/edmx"
    ns_edm = "http://docs.oasis-open.org/odata/ns/edm"
    
    # Root EDMX element
    root = ET.Element("edmx:Edmx", {
        "xmlns:edmx": ns_edmx,
        "Version": "4.0"
    })
    
    data_services = ET.SubElement(root, "edmx:DataServices")
    
    # Single schema containing all entity types
    schema = ET.SubElement(data_services, "Schema", {
        "xmlns": ns_edm,
        "Namespace": "SetuPranali"
    })
    
    # Entity container (lists all entity sets)
    container = ET.SubElement(schema, "EntityContainer", {"Name": "Default"})
    
    for ds in datasets:
        dataset_id = ds["id"]
        entity_type_name = _to_pascal_case(dataset_id)
        
        # Create EntityType with properties
        entity_type = ET.SubElement(schema, "EntityType", {"Name": entity_type_name})
        
        # Collect all available properties (fields + dimensions + metrics)
        properties = _collect_odata_properties(ds)
        
        for prop_name, prop_type in properties.items():
            ET.SubElement(entity_type, "Property", {
                "Name": prop_name,
                "Type": prop_type,
                "Nullable": "true"
            })
        
        # Register as EntitySet in container
        ET.SubElement(container, "EntitySet", {
            "Name": dataset_id,
            "EntityType": f"SetuPranali.{entity_type_name}"
        })
    
    # Serialize to XML string
    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=True)
    return xml_str


def _collect_odata_properties(dataset: dict) -> Dict[str, str]:
    """
    Collect all queryable properties from a dataset.
    
    Returns dict of {property_name: edm_type}
    
    Sources:
    1. Fields (raw table columns)
    2. Dimensions (may overlap with fields)
    3. Metrics (aggregated measures)
    """
    properties = {}
    
    # Add all fields
    for field in dataset.get("fields", []):
        name = field["name"]
        properties[name] = _get_edm_type(field.get("type", "string"))
    
    # Add dimensions (uses field type if it maps to a field)
    field_types = {f["name"]: f.get("type", "string") for f in dataset.get("fields", [])}
    for dim in dataset.get("dimensions", []):
        name = dim["name"]
        field_ref = dim.get("field", name)
        if name not in properties:
            properties[name] = _get_edm_type(field_types.get(field_ref, "string"))
    
    # Add metrics (return types from metric definition)
    for metric in dataset.get("metrics", []):
        name = metric["name"]
        return_type = metric.get("returnType", "double")
        properties[name] = _get_edm_type(return_type)
    
    return properties


def _to_pascal_case(s: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    return "".join(word.capitalize() for word in re.split(r"[-_]", s))


# =============================================================================
# ODATA FILTER PARSING
# =============================================================================

def parse_odata_filter(filter_str: str) -> Optional[dict]:
    """
    Parse OData $filter string into our FilterGroup structure.
    
    Supported operators (Power BI subset):
    - eq, ne, gt, ge, lt, le
    - in (values in parentheses)
    - and, or (combinators)
    
    Examples:
    - "city eq 'Indore'" → {"field": "city", "op": "eq", "value": "Indore"}
    - "revenue gt 500 and city eq 'Delhi'" → {"and": [...]}
    - "city in ('Indore', 'Delhi')" → {"field": "city", "op": "in", "values": [...]}
    
    NOTE: This is a minimal parser for Power BI compatibility.
    Complex nested expressions may not be fully supported.
    """
    if not filter_str or not filter_str.strip():
        return None
    
    filter_str = filter_str.strip()
    
    # Handle 'and' combinator (split on ' and ' at top level)
    # Simple approach: split by ' and ' (case-insensitive)
    and_parts = _split_top_level(filter_str, " and ")
    if len(and_parts) > 1:
        conditions = [parse_odata_filter(part) for part in and_parts]
        conditions = [c for c in conditions if c is not None]
        if len(conditions) == 1:
            return conditions[0]
        return {"and": conditions} if conditions else None
    
    # Handle 'or' combinator
    or_parts = _split_top_level(filter_str, " or ")
    if len(or_parts) > 1:
        conditions = [parse_odata_filter(part) for part in or_parts]
        conditions = [c for c in conditions if c is not None]
        if len(conditions) == 1:
            return conditions[0]
        return {"or": conditions} if conditions else None
    
    # Parse single condition
    return _parse_single_condition(filter_str)


def _split_top_level(s: str, delimiter: str) -> List[str]:
    """
    Split string by delimiter, but only at top level (not inside parentheses).
    Case-insensitive for the delimiter.
    """
    result = []
    current = []
    depth = 0
    i = 0
    delim_lower = delimiter.lower()
    
    while i < len(s):
        char = s[i]
        
        if char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            depth -= 1
            current.append(char)
        elif depth == 0 and s[i:i+len(delimiter)].lower() == delim_lower:
            result.append("".join(current).strip())
            current = []
            i += len(delimiter)
            continue
        else:
            current.append(char)
        
        i += 1
    
    if current:
        result.append("".join(current).strip())
    
    return result


def _parse_single_condition(cond_str: str) -> Optional[dict]:
    """
    Parse a single OData filter condition.
    
    Patterns:
    - field eq 'value'
    - field eq 123
    - field gt 100
    - field in ('a', 'b', 'c')
    """
    cond_str = cond_str.strip()
    
    # Remove surrounding parentheses if present
    if cond_str.startswith("(") and cond_str.endswith(")"):
        cond_str = cond_str[1:-1].strip()
    
    # Match 'in' operator: field in ('val1', 'val2')
    in_match = re.match(r"(\w+)\s+in\s*\((.+)\)", cond_str, re.IGNORECASE)
    if in_match:
        field = in_match.group(1)
        values_str = in_match.group(2)
        values = _parse_in_values(values_str)
        return {"field": field, "op": "in", "values": values}
    
    # Match comparison operators: field op value
    # Operators: eq, ne, gt, ge, lt, le
    comp_match = re.match(r"(\w+)\s+(eq|ne|gt|ge|lt|le)\s+(.+)", cond_str, re.IGNORECASE)
    if comp_match:
        field = comp_match.group(1)
        op_str = comp_match.group(2).lower()
        value_str = comp_match.group(3).strip()
        
        # Map OData operators to our internal operators
        op_map = {
            "eq": "eq",
            "ne": "ne",
            "gt": "gt",
            "ge": "gte",  # OData 'ge' → our 'gte'
            "lt": "lt",
            "le": "lte",  # OData 'le' → our 'lte'
        }
        op = op_map[op_str]
        value = _parse_value(value_str)
        
        return {"field": field, "op": op, "value": value}
    
    return None


def _parse_in_values(values_str: str) -> List[Any]:
    """Parse comma-separated values from IN clause."""
    values = []
    # Split by comma, handling quoted strings
    parts = re.split(r",\s*", values_str)
    for part in parts:
        values.append(_parse_value(part.strip()))
    return values


def _parse_value(value_str: str) -> Any:
    """
    Parse an OData literal value.
    
    - 'string' or "string" → string
    - 123 → int
    - 123.45 → float
    - true/false → bool
    - null → None
    """
    value_str = value_str.strip()
    
    # String literals (single or double quotes)
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1]
    
    # Boolean
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    
    # Null
    if value_str.lower() == "null":
        return None
    
    # Numbers
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        pass
    
    # Fallback: return as string
    return value_str


# =============================================================================
# ODATA $orderby PARSING
# =============================================================================

def parse_odata_orderby(orderby_str: str) -> List[OrderBy]:
    """
    Parse OData $orderby string into list of OrderBy.
    
    Examples:
    - "revenue desc" → [OrderBy(field="revenue", direction="desc")]
    - "city asc, revenue desc" → [OrderBy(...), OrderBy(...)]
    """
    if not orderby_str or not orderby_str.strip():
        return []
    
    result = []
    parts = orderby_str.split(",")
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        tokens = part.split()
        if len(tokens) >= 2:
            field = tokens[0]
            direction = tokens[1].lower()
            if direction not in ("asc", "desc"):
                direction = "asc"
        else:
            field = tokens[0]
            direction = "asc"
        
        result.append(OrderBy(field=field, direction=direction))
    
    return result


# =============================================================================
# INCREMENTAL REFRESH DETECTION (Power BI)
# =============================================================================
# Power BI sends incremental refresh as OData $filter expressions.
# Example: "order_date ge 2025-01-01T00:00:00Z and order_date lt 2025-02-01T00:00:00Z"
#
# This section detects these patterns and extracts incrementalFrom/To values.

def detect_incremental_from_odata_filter(
    filter_str: str,
    inc_column: Optional[str]
) -> Tuple[Optional[Any], Optional[Any], Optional[dict]]:
    """
    Detect incremental refresh pattern in OData $filter.
    
    PATTERN DETECTION:
    - ge/gt on inc_column → incrementalFrom
    - le/lt on inc_column → incrementalTo
    - Other filters → passed through as regular filters
    
    Returns:
        (incrementalFrom, incrementalTo, remaining_filters)
    
    Example:
        Input: "order_date ge 2025-01-01 and city eq 'Delhi'"
        Output: ("2025-01-01", None, {"field": "city", "op": "eq", "value": "Delhi"})
    """
    if not filter_str or not inc_column:
        return None, None, parse_odata_filter(filter_str)
    
    inc_from = None
    inc_to = None
    remaining_conditions = []
    
    # Parse the filter into conditions
    filter_str = filter_str.strip()
    
    # Split by 'and' at top level
    and_parts = _split_top_level(filter_str, " and ")
    
    for part in and_parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if this is an incremental condition
        inc_match = _match_incremental_condition(part, inc_column)
        
        if inc_match:
            op, value = inc_match
            # ge/gt → incrementalFrom (inclusive for ge)
            if op in ("ge", "gt"):
                inc_from = value
            # le/lt → incrementalTo (exclusive for lt)
            elif op in ("le", "lt"):
                inc_to = value
        else:
            # Not an incremental condition - keep it
            remaining_conditions.append(part)
    
    # Rebuild remaining filters
    remaining_filter = None
    if remaining_conditions:
        if len(remaining_conditions) == 1:
            remaining_filter = parse_odata_filter(remaining_conditions[0])
        else:
            # Rejoin with AND
            remaining_filter = parse_odata_filter(" and ".join(remaining_conditions))
    
    return inc_from, inc_to, remaining_filter


def _match_incremental_condition(
    cond_str: str,
    inc_column: str
) -> Optional[Tuple[str, Any]]:
    """
    Check if condition matches incremental pattern.
    
    Returns (operator, value) if matches, None otherwise.
    
    Matches:
    - "column ge value"
    - "column gt value"
    - "column le value"
    - "column lt value"
    """
    cond_str = cond_str.strip()
    
    # Remove surrounding parentheses
    if cond_str.startswith("(") and cond_str.endswith(")"):
        cond_str = cond_str[1:-1].strip()
    
    # Match pattern: field op value
    match = re.match(r"(\w+)\s+(ge|gt|le|lt)\s+(.+)", cond_str, re.IGNORECASE)
    if not match:
        return None
    
    field = match.group(1)
    op = match.group(2).lower()
    value_str = match.group(3).strip()
    
    # Check if this is the incremental column
    if field.lower() != inc_column.lower():
        return None
    
    # Parse the value
    value = _parse_value(value_str)
    
    return op, value


# =============================================================================
# ODATA $select PARSING → dimensions + metrics
# =============================================================================

def parse_odata_select(
    select_str: str,
    dataset: dict
) -> Tuple[List[QueryDimension], List[QueryMetric]]:
    """
    Parse OData $select and split into dimensions and metrics.
    
    Logic:
    - If field name is a known metric → QueryMetric
    - Otherwise → QueryDimension
    
    This allows Power BI to select any combination of columns.
    """
    if not select_str or not select_str.strip():
        # No $select = return default dimensions + metrics
        return _get_default_selections(dataset)
    
    # Get known metrics and dimensions from dataset
    metric_names = {m["name"] for m in dataset.get("metrics", [])}
    dim_names = {d["name"] for d in dataset.get("dimensions", [])}
    
    # Parse comma-separated field names
    fields = [f.strip() for f in select_str.split(",") if f.strip()]
    
    dimensions = []
    metrics = []
    
    for field in fields:
        if field in metric_names:
            metrics.append(QueryMetric(name=field))
        elif field in dim_names:
            dimensions.append(QueryDimension(name=field))
        else:
            # Unknown field - treat as dimension (raw column)
            dimensions.append(QueryDimension(name=field))
    
    return dimensions, metrics


def _get_default_selections(dataset: dict) -> Tuple[List[QueryDimension], List[QueryMetric]]:
    """Return all dimensions and metrics as default selection."""
    dimensions = [QueryDimension(name=d["name"]) for d in dataset.get("dimensions", [])]
    metrics = [QueryMetric(name=m["name"]) for m in dataset.get("metrics", [])]
    return dimensions, metrics


# =============================================================================
# ODATA ENDPOINTS
# =============================================================================

@router.get("")
@router.get("/")
def odata_service_document(request: Request):
    """
    OData Service Document (root).
    
    Lists all available entity sets (datasets) that Power BI can browse.
    This is the entry point for "Get Data → OData Feed".
    """
    catalog = load_catalog()
    datasets = catalog.get("datasets", [])
    
    # Build service root URL
    service_root = str(request.url).rstrip("/")
    
    # OData service document format
    entity_sets = [
        {
            "name": ds["id"],
            "kind": "EntitySet",
            "url": ds["id"]
        }
        for ds in datasets
    ]
    
    return {
        "@odata.context": f"{service_root}/$metadata",
        "value": entity_sets
    }


@router.get("/$metadata")
def odata_metadata(request: Request):
    """
    OData EDMX Metadata Document.
    
    Returns XML describing all entity types and their properties.
    Power BI uses this to build the schema for the data source.
    """
    catalog = load_catalog()
    datasets = catalog.get("datasets", [])
    
    service_root = str(request.url).replace("/$metadata", "")
    edmx_xml = generate_edmx(datasets, service_root)
    
    return Response(
        content=edmx_xml,
        media_type="application/xml"
    )


@router.get("/{datasetId}")
def odata_query_entity_set(
    datasetId: str,
    request: Request,
    ctx: TenantContext = Depends(require_api_key)
):
    """
    Query an OData Entity Set (dataset).
    
    Accepts standard OData query parameters:
    - $select: Columns to return
    - $filter: Row filter predicates
    - $top: Max rows (limit)
    - $skip: Rows to skip (offset)
    - $orderby: Sort order
    
    INCREMENTAL REFRESH (Power BI):
    When $filter contains ge/gt/le/lt on the dataset's incremental column,
    those conditions are detected and converted to incrementalFrom/To.
    This enables Power BI's incremental refresh policy to work seamlessly.
    
    ROW-LEVEL SECURITY (RLS):
    Tenant isolation is automatic based on the authenticated X-API-Key.
    RLS filter is injected transparently - Power BI doesn't need to know.
    
    Internally converts to QueryRequest and calls compile_and_run_query().
    """
    # Load dataset from catalog
    catalog = load_catalog()
    request_id = getattr(request.state, "request_id", None)
    try:
        dataset = get_dataset(catalog, datasetId)
    except KeyError:
        available = [ds["id"] for ds in catalog.get("datasets", [])]
        raise dataset_not_found(
            dataset=datasetId,
            available_datasets=available,
            request_id=request_id
        )
    
    # Extract OData query params
    params = dict(request.query_params)
    
    select_str = params.get("$select", "")
    filter_str = params.get("$filter", "")
    top_str = params.get("$top", "10000")
    skip_str = params.get("$skip", "0")
    orderby_str = params.get("$orderby", "")
    
    # Parse $select → dimensions + metrics
    dimensions, metrics = parse_odata_select(select_str, dataset)
    
    # =========================================================================
    # INCREMENTAL REFRESH DETECTION
    # =========================================================================
    # Check if dataset has incremental config and detect patterns in $filter.
    # Power BI sends: "order_date ge 2025-01-01 and order_date lt 2025-02-01"
    # We extract this as incrementalFrom/To and pass remaining filters through.
    
    inc_config = dataset.get("incremental", {})
    inc_enabled = inc_config.get("enabled", False)
    inc_column = inc_config.get("column")
    
    inc_from = None
    inc_to = None
    filters = None
    
    if inc_enabled and inc_column:
        # Try to detect incremental patterns in $filter
        inc_from, inc_to, filters = detect_incremental_from_odata_filter(
            filter_str, inc_column
        )
    else:
        # No incremental config - parse filters normally
        filters = parse_odata_filter(filter_str)
    
    # Parse $orderby → List[OrderBy]
    order_by = parse_odata_orderby(orderby_str)
    
    # Parse $top and $skip
    try:
        limit = int(top_str)
    except ValueError:
        limit = 10000
    
    try:
        offset = int(skip_str)
    except ValueError:
        offset = 0
    
    # Build QueryRequest (reusing existing model)
    # Include incremental params if detected from OData filter
    query_req = QueryRequest(
        dataset=datasetId,
        dimensions=dimensions,
        metrics=metrics,
        filters=filters,
        orderBy=order_by,
        limit=limit,
        offset=offset,
        # Incremental refresh params (detected from $filter)
        incremental=(inc_from is not None or inc_to is not None),
        incrementalFrom=inc_from,
        incrementalTo=inc_to
    )
    
    # Execute query using existing engine (NO new SQL logic!)
    # RLS is applied transparently based on authenticated tenant
    # Caching is automatic and tenant-scoped for security
    try:
        engine, conn = get_engine_and_conn(dataset["source"], SOURCES)
        
        # Build cache components (tenant-scoped for RLS safety)
        cache_components = build_cache_components_from_request(
            query_req, dataset, engine, ctx.tenant, ctx.role
        )
        
        # Execute with caching
        def execute_query():
            return compile_and_run_query(
                dataset, query_req, conn,
                engine=engine,
                tenant=ctx.tenant,
                role=ctx.role
            )
        
        columns, rows, stats = execute_with_cache(
            execute_fn=execute_query,
            cache_components=cache_components
        )
    except SetuPranaliError:
        raise
    except Exception as e:
        raise internal_error(
            message=f"OData query failed: {str(e)}",
            details={"dataset": datasetId},
            request_id=request_id
        )
    
    # Build OData response
    service_root = str(request.url).split("?")[0].rsplit("/", 1)[0]
    
    return {
        "@odata.context": f"{service_root}/$metadata#${datasetId}",
        "value": rows
    }

