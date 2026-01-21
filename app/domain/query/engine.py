import duckdb
from typing import Any, Dict, List, Tuple, Optional, Union
from datetime import date, datetime, timedelta
from app.shared.types.models import QueryRequest, ResultColumn, FilterCondition, IncrementalConfig
from app.rls import build_rls_filter, apply_rls_to_filters, get_rls_stats, RLSResult
from app.domain.query.builder import SQLBuilder, SQLBuilderError

def _quote_ident(name: str) -> str:
    # very small identifier quote; safe for demo
    return '"' + name.replace('"','""') + '"'


def _compile_filter(node) -> Tuple[str, List[Any]]:
    if not node:
        return "", []

    # Convert Pydantic models to dict for consistent access
    if hasattr(node, "model_dump"):
        node = node.model_dump(by_alias=True, exclude_none=True)

    # AND
    if "and" in node:
        parts, args = [], []
        for n in node["and"]:
            sql, a = _compile_filter(n)
            if sql:
                parts.append(f"({sql})")
                args.extend(a)
        return " AND ".join(parts), args

    # OR
    if "or" in node:
        parts, args = [], []
        for n in node["or"]:
            sql, a = _compile_filter(n)
            if sql:
                parts.append(f"({sql})")
                args.extend(a)
        return " OR ".join(parts), args

    # NOT
    if "not" in node:
        sql, args = _compile_filter(node["not"])
        return f"NOT ({sql})", args

    # CONDITION
    if "field" in node and "op" in node:
        field = _quote_ident(node["field"])
        op = node["op"]
        args: List[Any] = []

        if op == "eq":
            args.append(node["value"])
            return f"{field} = ?", args

        if op == "ne":
            args.append(node["value"])
            return f"{field} <> ?", args

        if op == "gt":
            args.append(node["value"])
            return f"{field} > ?", args

        if op == "gte":
            args.append(node["value"])
            return f"{field} >= ?", args

        if op == "lt":
            args.append(node["value"])
            return f"{field} < ?", args

        if op == "lte":
            args.append(node["value"])
            return f"{field} <= ?", args

        if op == "between":
            args.extend([node.get("from"), node.get("to")])
            return f"{field} BETWEEN ? AND ?", args

        if op == "in":
            vals = node.get("values", [])
            args.extend(vals)
            ph = ",".join(["?"] * len(vals)) if vals else "NULL"
            return f"{field} IN ({ph})", args

        if op == "not_in":
            vals = node.get("values", [])
            args.extend(vals)
            ph = ",".join(["?"] * len(vals)) if vals else "NULL"
            return f"{field} NOT IN ({ph})", args

        if op == "contains":
            args.append(f"%{node['value']}%")
            return f"{field} LIKE ?", args

        if op == "starts_with":
            args.append(f"{node['value']}%")
            return f"{field} LIKE ?", args

        if op == "ends_with":
            args.append(f"%{node['value']}")
            return f"{field} LIKE ?", args

        if op == "is_null":
            return f"{field} IS NULL", []

        if op == "is_not_null":
            return f"{field} IS NOT NULL", []

        raise ValueError(f"Unsupported filter op: {op}")

    raise ValueError("Invalid filter structure")


# =============================================================================
# INCREMENTAL REFRESH HELPERS
# =============================================================================

def _get_incremental_config(dataset: dict) -> Optional[Dict]:
    """
    Extract incremental config from dataset definition.
    Returns None if incremental is not enabled.
    """
    inc = dataset.get("incremental", {})
    if not inc.get("enabled", False):
        return None
    
    return {
        "column": inc.get("column"),
        "type": inc.get("type", "datetime"),
        "mode": inc.get("mode", "append"),
        "maxWindowDays": inc.get("maxWindowDays", 90)
    }


def _build_incremental_filter(
    inc_config: Dict,
    from_value: Optional[Union[str, int, float, date, datetime]],
    to_value: Optional[Union[str, int, float, date, datetime]]
) -> Optional[Dict]:
    """
    Build filter conditions for incremental refresh.
    
    CORE RULES:
    - If from_value provided: column >= from_value
    - If to_value provided: column < to_value
    - Both conditions combined with AND
    
    Returns a filter dict compatible with _compile_filter().
    """
    if not from_value and not to_value:
        return None
    
    column = inc_config["column"]
    conditions = []
    
    # Lower bound: column >= from_value (inclusive)
    if from_value is not None:
        conditions.append({
            "field": column,
            "op": "gte",
            "value": from_value
        })
    
    # Upper bound: column < to_value (exclusive)
    if to_value is not None:
        conditions.append({
            "field": column,
            "op": "lt",
            "value": to_value
        })
    
    # Return single condition or AND group
    if len(conditions) == 1:
        return conditions[0]
    
    return {"and": conditions}


def _validate_incremental_window(
    inc_config: Dict,
    from_value: Optional[Union[str, int, float, date, datetime]],
    to_value: Optional[Union[str, int, float, date, datetime]]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that incremental window doesn't exceed maxWindowDays.
    
    SAFETY: Prevents runaway scans from BI tools requesting too much data.
    
    Returns (is_valid, error_message).
    """
    max_days = inc_config.get("maxWindowDays", 90)
    col_type = inc_config.get("type", "datetime")
    
    # Only enforce window for date/datetime types
    if col_type not in ("date", "datetime"):
        return True, None
    
    if not from_value:
        # No lower bound - cannot validate window
        # This is allowed (full refresh behavior)
        return True, None
    
    # Parse from_value to date
    try:
        if isinstance(from_value, (date, datetime)):
            from_date = from_value if isinstance(from_value, date) else from_value.date()
        else:
            # Try parsing string
            from_str = str(from_value).split("T")[0]
            from_date = datetime.strptime(from_str, "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        # Can't parse - skip validation
        return True, None
    
    # Determine to_date (default: today)
    if to_value:
        try:
            if isinstance(to_value, (date, datetime)):
                to_date = to_value if isinstance(to_value, date) else to_value.date()
            else:
                to_str = str(to_value).split("T")[0]
                to_date = datetime.strptime(to_str, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            to_date = date.today()
    else:
        to_date = date.today()
    
    # Calculate window
    window_days = (to_date - from_date).days
    
    if window_days > max_days:
        return False, f"Incremental window ({window_days} days) exceeds max ({max_days} days)"
    
    return True, None


def _merge_filters(existing: Optional[Dict], incremental: Optional[Dict]) -> Optional[Dict]:
    """
    Merge existing filters with incremental filter using AND.
    
    - If no existing filter: return incremental
    - If no incremental filter: return existing
    - Otherwise: combine with AND
    """
    if not incremental:
        return existing
    
    if not existing:
        return incremental
    
    # Merge with AND
    return {"and": [existing, incremental]}


def compile_and_run_query(
    dataset: dict,
    req: QueryRequest,
    conn,
    engine: str = "duckdb",
    tenant: Optional[str] = None,
    role: Optional[str] = None
):
    """
    Compile and execute a semantic query.
    
    Args:
        dataset: Dataset definition from catalog
        req: Query request with dimensions, metrics, filters
        conn: Database connection (DuckDB or psycopg2)
        engine: Engine type ("duckdb" or "postgres")
        tenant: Authenticated tenant (for RLS)
        role: Authenticated role (for RLS admin bypass)
    
    Returns:
        (columns, rows, stats) tuple
    """
    source_ref = dataset["source"]["reference"]

    # =========================================================================
    # ROW-LEVEL SECURITY (RLS)
    # =========================================================================
    # RLS is applied FIRST, before incremental filters.
    # This ensures tenant isolation cannot be bypassed by incremental params.
    #
    # Flow:
    # 1. Evaluate RLS for dataset + tenant
    # 2. Merge RLS filter with user filters using AND
    # 3. Then apply incremental filter (also with AND)
    #
    # Final filter: (user_filters) AND (rls_filter) AND (incremental_filter)
    
    rls_result = RLSResult(applied=False)
    rls_stats = {}
    
    if tenant and role:
        try:
            rls_result = build_rls_filter(dataset, tenant, role)
            rls_stats = get_rls_stats(rls_result, tenant, role)
        except ValueError as e:
            # RLS validation error - propagate as clear error
            raise ValueError(f"RLS error: {str(e)}")
    
    # Start with user's original filters
    merged_filters = req.filters
    
    # Apply RLS filter (if any)
    if rls_result.applied and rls_result.filter:
        # Convert existing filters to dict if needed
        existing_dict = None
        if merged_filters:
            if hasattr(merged_filters, "model_dump"):
                existing_dict = merged_filters.model_dump(by_alias=True, exclude_none=True)
            else:
                existing_dict = merged_filters
        
        merged_filters = apply_rls_to_filters(existing_dict, rls_result)
    
    # =========================================================================
    # INCREMENTAL REFRESH HANDLING
    # =========================================================================
    # If dataset supports incremental and request has incremental params,
    # inject appropriate filters. Uses existing filter system - NO new SQL.
    
    inc_config = _get_incremental_config(dataset)
    inc_filter = None
    inc_stats = {"incremental": False}
    
    if inc_config and req.incremental and (req.incrementalFrom or req.incrementalTo):
        # Validate column exists
        column = inc_config["column"]
        field_names = {f["name"] for f in dataset.get("fields", [])}
        
        if column not in field_names:
            raise ValueError(f"Incremental column '{column}' not found in dataset fields")
        
        # Validate window size (safety limit)
        is_valid, error_msg = _validate_incremental_window(
            inc_config, req.incrementalFrom, req.incrementalTo
        )
        if not is_valid:
            raise ValueError(error_msg)
        
        # Build incremental filter
        inc_filter = _build_incremental_filter(
            inc_config, req.incrementalFrom, req.incrementalTo
        )
        
        # Track in stats for audit/debugging
        inc_stats = {
            "incremental": True,
            "incrementalColumn": column,
            "incrementalFrom": str(req.incrementalFrom) if req.incrementalFrom else None,
            "incrementalTo": str(req.incrementalTo) if req.incrementalTo else None,
            "incrementalMode": inc_config["mode"]
        }
    
    # Merge incremental filter with existing filters (including RLS)
    if inc_filter:
        # Convert merged_filters to dict if needed
        existing_dict = None
        if merged_filters:
            if hasattr(merged_filters, "model_dump"):
                existing_dict = merged_filters.model_dump(by_alias=True, exclude_none=True)
            else:
                existing_dict = merged_filters
        
        merged_filters = _merge_filters(existing_dict, inc_filter)
    
    # =========================================================================
    # SQL GENERATION USING SQLGLOT
    # =========================================================================
    
    # Initialize SQL builder with target dialect
    try:
        builder = SQLBuilder(dialect=engine)
    except Exception as e:
        # Fallback to manual SQL building if SQLGlot fails
        logger.warning(f"SQLGlot initialization failed, using fallback: {e}")
        builder = None
    
    columns: List[ResultColumn] = []
    
    # Build a quick lookup for field types
    field_types = {f["name"]: f.get("type","string") for f in dataset.get("fields", [])}
    field_sem = {f["name"]: f.get("semanticType") for f in dataset.get("fields", [])}
    
    # Prepare dimensions and metrics
    dimension_names = [d.name for d in req.dimensions]
    metric_expressions = []
    
    # Build metric expressions
    metrics_def = {m["name"]: m for m in dataset.get("metrics", [])}
    for m in req.metrics:
        md = metrics_def[m.name]
        expr = md["expression"]
        if expr["type"] == "aggregation":
            agg = expr["agg"].upper()
            field = expr["field"]
            if agg == "COUNT_DISTINCT":
                metric_expr = f"COUNT(DISTINCT {field})"
            else:
                metric_expr = f"{agg}({field})"
        else:
            raise ValueError("Derived metrics not supported in MVP")
        metric_expressions.append(metric_expr)
        columns.append(ResultColumn(
            name=m.alias or m.name,
            type=md.get("returnType","double"),
            semanticType="metric"
        ))
    
    # Build dimension columns
    for d in req.dimensions:
        columns.append(ResultColumn(
            name=d.alias or d.name,
            type=field_types.get(d.name,"string"),
            semanticType=field_sem.get(d.name)
        ))
    
    # Convert filters to dict format for SQLBuilder
    filter_dict = None
    if merged_filters:
        if hasattr(merged_filters, "model_dump"):
            filter_dict = merged_filters.model_dump(by_alias=True, exclude_none=True)
        else:
            filter_dict = merged_filters
    
    # Convert order_by to dict format
    order_by_list = None
    if req.orderBy:
        order_by_list = [
            {"field": o.field, "direction": o.direction.lower()}
            for o in req.orderBy
        ]
    
    # Generate SQL using SQLGlot if available, otherwise fallback
    if builder:
        try:
            sql, args = builder.build_query(
                dimensions=dimension_names,
                metrics=metric_expressions,
                source_table=source_ref,
                filters=filter_dict,
                group_by=dimension_names if req.metrics else None,
                order_by=order_by_list,
                limit=int(req.limit),
                offset=int(req.offset)
            )
        except SQLBuilderError as e:
            logger.warning(f"SQLGlot query building failed, using fallback: {e}")
            builder = None  # Fall through to manual building
    
    # Fallback to manual SQL building
    if not builder:
        # dimensions
        select_parts: List[str] = []
        group_by: List[str] = []
        
        for d in req.dimensions:
            col = _quote_ident(d.name)
            alias = d.alias or d.name
            select_parts.append(f"{col} AS {_quote_ident(alias)}")
            group_by.append(col)
        
        # metrics
        for m in req.metrics:
            md = metrics_def[m.name]
            expr = md["expression"]
            alias = m.alias or m.name
            if expr["type"] == "aggregation":
                agg = expr["agg"].upper()
                field = _quote_ident(expr["field"])
                if agg == "COUNT_DISTINCT":
                    sql_expr = f"COUNT(DISTINCT {field})"
                else:
                    sql_expr = f"{agg}({field})"
            else:
                raise ValueError("Derived metrics not supported in MVP")
            select_parts.append(f"{sql_expr} AS {_quote_ident(alias)}")
        
        if not select_parts:
            select_parts = ["*"]
        
        # Use merged filters (original + incremental)
        where_sql, args = _compile_filter(merged_filters) if merged_filters else ("", [])
        
        sql = f"SELECT {', '.join(select_parts)} FROM {source_ref}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if group_by and req.metrics:
            sql += f" GROUP BY {', '.join(group_by)}"
        if req.orderBy:
            ob = []
            for o in req.orderBy:
                ob.append(f"{_quote_ident(o.field)} {o.direction.upper()}")
            sql += " ORDER BY " + ", ".join(ob)
        sql += f" LIMIT {int(req.limit)} OFFSET {int(req.offset)}"

    # =========================
    # EXECUTION (ENGINE SAFE)
    # =========================
    # Supports both new adapter interface and legacy connections

    # =========================
    # BUILD STATS (RLS + INCREMENTAL)
    # =========================
    base_stats = {
        "cached": False,
        **rls_stats,      # Include RLS audit info
        **inc_stats       # Include incremental refresh stats
    }

    # Check if conn is a new-style adapter
    from app.infrastructure.adapters.base import BaseAdapter
    if isinstance(conn, BaseAdapter):
        # New adapter interface
        try:
            result = conn.execute(sql, args)
            return columns, result.rows, {
                "engine": result.engine,
                "sql": result.sql,
                **base_stats
            }
        except Exception as e:
            logger.error(f"Adapter query execution failed: {e}")
            raise

    # Legacy: DuckDB connection has `.execute` that returns result with fetchdf()
    if hasattr(conn, "execute") and hasattr(conn, "cursor") is False:
        try:
            rows = conn.execute(sql, args).fetchdf().to_dict(orient="records")
            return columns, rows, {
                "engine": engine,
                "sql": sql,
                **base_stats
            }
        except Exception as e:
            logger.error(f"DuckDB query execution failed: {e}")
            raise

    # Legacy: psycopg2 Postgres connection (NO direct `.execute`)
    try:
        pg_sql = sql.replace("?", "%s")

        cur = conn.cursor()
        cur.execute(pg_sql, args)

        colnames = [desc[0] for desc in cur.description]
        data = cur.fetchall()

        cur.close()

        rows = [dict(zip(colnames, row)) for row in data]

        return columns, rows, {
            "engine": engine,
            "sql": pg_sql,
            **base_stats
        }
    except Exception as e:
        logger.error(f"Postgres query execution failed: {e}")
        raise

