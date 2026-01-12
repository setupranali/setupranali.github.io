"""
Query Planner

Generates SQL queries using:
- ERD model (join paths)
- Semantic model (dimensions, measures)
- Query request (selected fields)

Features:
- Automatic join resolution
- Aggregation handling
- Filter application
- Sort and pagination
- Query optimization hints
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from .erd_manager import ERDModel, TableNode, RelationshipEdge, JoinType
from .semantic_model import (
    SemanticModel, Dimension, Measure, CalculatedField,
    AggregationType, ExpressionValidator
)

logger = logging.getLogger(__name__)


class FilterOperator(str, Enum):
    """Filter comparison operators."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUALS = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUALS = "<="
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    IN = "IN"
    NOT_IN = "NOT IN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    BETWEEN = "BETWEEN"


class SortDirection(str, Enum):
    """Sort directions."""
    ASC = "ASC"
    DESC = "DESC"


@dataclass
class QueryFilter:
    """A filter condition for the query."""
    field: str  # Dimension or measure name
    operator: FilterOperator
    value: Any
    second_value: Any = None  # For BETWEEN
    
    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "secondValue": self.second_value,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "QueryFilter":
        return cls(
            field=data["field"],
            operator=FilterOperator(data["operator"]),
            value=data["value"],
            second_value=data.get("secondValue"),
        )


@dataclass
class QuerySort:
    """A sort specification."""
    field: str
    direction: SortDirection = SortDirection.ASC
    
    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "direction": self.direction.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "QuerySort":
        return cls(
            field=data["field"],
            direction=SortDirection(data.get("direction", "ASC")),
        )


@dataclass
class SemanticQuery:
    """
    A semantic query request.
    
    Attributes:
        dimensions: List of dimension names to include
        measures: List of measure names to include
        filters: Filter conditions
        sorts: Sort specifications
        limit: Max rows to return
        offset: Rows to skip
    """
    dimensions: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    filters: List[QueryFilter] = field(default_factory=list)
    sorts: List[QuerySort] = field(default_factory=list)
    limit: Optional[int] = None
    offset: int = 0
    
    def to_dict(self) -> dict:
        return {
            "dimensions": self.dimensions,
            "measures": self.measures,
            "filters": [f.to_dict() for f in self.filters],
            "sorts": [s.to_dict() for s in self.sorts],
            "limit": self.limit,
            "offset": self.offset,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SemanticQuery":
        return cls(
            dimensions=data.get("dimensions", []),
            measures=data.get("measures", []),
            filters=[QueryFilter.from_dict(f) for f in data.get("filters", [])],
            sorts=[QuerySort.from_dict(s) for s in data.get("sorts", [])],
            limit=data.get("limit"),
            offset=data.get("offset", 0),
        )


@dataclass
class GeneratedSQL:
    """Result of query planning."""
    sql: str
    params: List[Any] = field(default_factory=list)
    tables_used: List[str] = field(default_factory=list)
    joins_used: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "sql": self.sql,
            "params": self.params,
            "tablesUsed": self.tables_used,
            "joinsUsed": self.joins_used,
            "warnings": self.warnings,
        }


class QueryPlanner:
    """
    Plans and generates SQL from semantic queries.
    
    Usage:
        planner = QueryPlanner(erd_model, semantic_model)
        query = SemanticQuery(
            dimensions=["Region", "Product Category"],
            measures=["Total Revenue", "Order Count"]
        )
        result = planner.plan(query)
        print(result.sql)
    """
    
    def __init__(
        self,
        erd_model: ERDModel,
        semantic_model: SemanticModel,
        quote_char: str = '"'
    ):
        """
        Initialize query planner.
        
        Args:
            erd_model: ERD model with table nodes and relationships
            semantic_model: Semantic model with dimensions and measures
            quote_char: Identifier quote character (", `, [)
        """
        self.erd = erd_model
        self.semantic = semantic_model
        self.quote_char = quote_char
        
        # Build lookup maps
        self._build_lookups()
    
    def _build_lookups(self):
        """Build lookup maps for quick access."""
        # Node ID to table name
        self.node_to_table: Dict[str, str] = {}
        self.table_to_node: Dict[str, str] = {}
        
        for node in self.erd.nodes:
            self.node_to_table[node.id] = node.full_name
            self.table_to_node[node.full_name] = node.id
        
        # Build adjacency list for join graph
        self.join_graph: Dict[str, List[Tuple[str, RelationshipEdge]]] = {}
        for node in self.erd.nodes:
            self.join_graph[node.id] = []
        
        for edge in self.erd.edges:
            if edge.is_active:
                self.join_graph[edge.source_node_id].append((edge.target_node_id, edge))
                self.join_graph[edge.target_node_id].append((edge.source_node_id, edge))
    
    def plan(self, query: SemanticQuery) -> GeneratedSQL:
        """
        Generate SQL for a semantic query.
        
        Args:
            query: Semantic query specification
        
        Returns:
            GeneratedSQL with query and metadata
        """
        warnings = []
        params = []
        
        # 1. Resolve dimensions and measures
        select_parts = []
        group_by_parts = []
        tables_needed: Set[str] = set()
        
        # Process dimensions
        for dim_name in query.dimensions:
            dim = self.semantic.get_dimension(dim_name)
            if not dim:
                warnings.append(f"Unknown dimension: {dim_name}")
                continue
            
            col_expr = self._quote_identifier(dim.source_column)
            alias = self._quote_identifier(dim_name)
            select_parts.append(f"{dim.source_table}.{col_expr} AS {alias}")
            group_by_parts.append(f"{dim.source_table}.{col_expr}")
            tables_needed.add(dim.source_table)
        
        # Process measures
        for measure_name in query.measures:
            measure = self.semantic.get_measure(measure_name)
            if not measure:
                # Check calculated fields
                calc = self.semantic.get_calculated_field(measure_name)
                if calc:
                    expr = self._resolve_calculated_field(calc)
                    alias = self._quote_identifier(measure_name)
                    select_parts.append(f"{expr} AS {alias}")
                    continue
                warnings.append(f"Unknown measure: {measure_name}")
                continue
            
            alias = self._quote_identifier(measure_name)
            # Build measure expression with table-qualified column reference
            measure_expr = self._build_measure_expression(measure)
            select_parts.append(f"{measure_expr} AS {alias}")
            if measure.source_table:
                tables_needed.add(measure.source_table)
        
        if not select_parts:
            return GeneratedSQL(
                sql="SELECT 1",
                warnings=["No valid dimensions or measures specified"]
            )
        
        # 2. Determine join path
        tables_list = list(tables_needed)
        from_clause, joins_used = self._build_from_clause(tables_list)
        
        # 3. Build WHERE clause
        where_parts = []
        for f in query.filters:
            filter_sql, filter_params = self._build_filter(f)
            if filter_sql:
                where_parts.append(filter_sql)
                params.extend(filter_params)
        
        # 4. Build ORDER BY clause
        order_parts = []
        for sort in query.sorts:
            # Check if it's a dimension or measure
            if sort.field in query.dimensions:
                dim = self.semantic.get_dimension(sort.field)
                if dim:
                    order_parts.append(f"{dim.source_table}.{self._quote_identifier(dim.source_column)} {sort.direction.value}")
            else:
                # Use alias
                order_parts.append(f"{self._quote_identifier(sort.field)} {sort.direction.value}")
        
        # 5. Assemble SQL
        sql_parts = [
            "SELECT",
            "    " + ",\n    ".join(select_parts),
            from_clause,
        ]
        
        if where_parts:
            sql_parts.append("WHERE " + " AND ".join(where_parts))
        
        if group_by_parts:
            sql_parts.append("GROUP BY " + ", ".join(group_by_parts))
        
        if order_parts:
            sql_parts.append("ORDER BY " + ", ".join(order_parts))
        
        if query.limit:
            sql_parts.append(f"LIMIT {query.limit}")
            if query.offset > 0:
                sql_parts.append(f"OFFSET {query.offset}")
        
        sql = "\n".join(sql_parts)
        
        return GeneratedSQL(
            sql=sql,
            params=params,
            tables_used=list(tables_needed),
            joins_used=joins_used,
            warnings=warnings,
        )
    
    def _build_from_clause(self, tables: List[str]) -> Tuple[str, List[str]]:
        """
        Build FROM clause with necessary JOINs.
        
        Uses BFS to find shortest join paths between tables.
        """
        if not tables:
            return "FROM dual", []
        
        if len(tables) == 1:
            return f"FROM {tables[0]}", []
        
        # Start with first table
        base_table = tables[0]
        from_parts = [f"FROM {base_table}"]
        joins_used = []
        visited = {base_table}
        
        # Find paths to other tables
        for target_table in tables[1:]:
            if target_table in visited:
                continue
            
            # Find join path using BFS
            path = self._find_join_path(base_table, target_table)
            if path:
                for edge in path:
                    source_table = self.node_to_table.get(edge.source_node_id, "")
                    target_table_name = self.node_to_table.get(edge.target_node_id, "")
                    
                    # Determine which table to join
                    if source_table in visited and target_table_name not in visited:
                        join_table = target_table_name
                        join_col = edge.target_column
                        base_col = edge.source_column
                        base = source_table
                    elif target_table_name in visited and source_table not in visited:
                        join_table = source_table
                        join_col = edge.source_column
                        base_col = edge.target_column
                        base = target_table_name
                    else:
                        continue
                    
                    join_type = edge.join_type.value.upper()
                    from_parts.append(
                        f"{join_type} JOIN {join_table} ON "
                        f"{base}.{self._quote_identifier(base_col)} = "
                        f"{join_table}.{self._quote_identifier(join_col)}"
                    )
                    joins_used.append(f"{base} -> {join_table}")
                    visited.add(join_table)
        
        return "\n".join(from_parts), joins_used
    
    def _find_join_path(
        self, 
        source_table: str, 
        target_table: str
    ) -> List[RelationshipEdge]:
        """
        Find the shortest join path between two tables using BFS.
        """
        source_node = self.table_to_node.get(source_table)
        target_node = self.table_to_node.get(target_table)
        
        if not source_node or not target_node:
            return []
        
        from collections import deque
        
        # BFS
        queue = deque([(source_node, [])])
        visited = {source_node}
        
        while queue:
            current, path = queue.popleft()
            
            if current == target_node:
                return path
            
            for neighbor, edge in self.join_graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [edge]))
        
        return []
    
    def _build_filter(self, f: QueryFilter) -> Tuple[str, List[Any]]:
        """Build SQL WHERE clause part for a filter."""
        # Resolve field to column
        dim = self.semantic.get_dimension(f.field)
        measure = self.semantic.get_measure(f.field)
        
        if dim:
            col = f"{dim.source_table}.{self._quote_identifier(dim.source_column)}"
        elif measure:
            col = measure.to_sql()
        else:
            col = self._quote_identifier(f.field)
        
        params = []
        
        if f.operator == FilterOperator.IS_NULL:
            return f"{col} IS NULL", []
        elif f.operator == FilterOperator.IS_NOT_NULL:
            return f"{col} IS NOT NULL", []
        elif f.operator in (FilterOperator.IN, FilterOperator.NOT_IN):
            if isinstance(f.value, list):
                placeholders = ", ".join(["?" for _ in f.value])
                params.extend(f.value)
                return f"{col} {f.operator.value} ({placeholders})", params
            return f"{col} {f.operator.value} (?)", [f.value]
        elif f.operator == FilterOperator.BETWEEN:
            return f"{col} BETWEEN ? AND ?", [f.value, f.second_value]
        else:
            return f"{col} {f.operator.value} ?", [f.value]
    
    def _resolve_calculated_field(self, calc: CalculatedField) -> str:
        """Resolve calculated field expression to SQL."""
        expression = calc.expression
        
        # Build field map
        field_map = {}
        for ref in calc.referenced_fields:
            dim = self.semantic.get_dimension(ref)
            if dim:
                field_map[ref] = f"{dim.source_table}.{dim.source_column}"
                continue
            
            measure = self.semantic.get_measure(ref)
            if measure:
                field_map[ref] = measure.to_sql()
        
        return ExpressionValidator.substitute_fields(expression, field_map)
    
    def _quote_identifier(self, identifier: str) -> str:
        """Quote an identifier."""
        q = self.quote_char
        if q == "[":
            return f"[{identifier}]"
        return f"{q}{identifier}{q}"
    
    def _build_measure_expression(self, measure: Measure) -> str:
        """
        Build a measure expression with table-qualified column reference.
        
        Parses the measure expression and adds table prefix to column references.
        E.g., SUM(amount) -> SUM(schema.table.`amount`)
        """
        expr = measure.expression
        
        # If expression already contains the table reference, use as-is
        if measure.source_table and measure.source_table in expr:
            return expr
        
        # For simple expressions like "SUM(column_name)", add table prefix
        agg = measure.aggregation.value
        
        # Try to extract the column name from the expression
        # Handle patterns like: AGG(column), AGG(DISTINCT column), column
        import re
        
        # Pattern: AGG(column) or AGG(DISTINCT column)
        pattern = rf'^({agg})\s*\(\s*(DISTINCT\s+)?(.+?)\s*\)$'
        match = re.match(pattern, expr, re.IGNORECASE)
        
        if match:
            agg_func = match.group(1)
            distinct = match.group(2) or ''
            column = match.group(3).strip()
            
            # Only add table prefix if column is a simple name (no dots, no functions)
            if '.' not in column and '(' not in column and measure.source_table:
                qualified_col = f"{measure.source_table}.{self._quote_identifier(column)}"
                return f"{agg_func}({distinct}{qualified_col})"
        
        # For COUNT(*) or other special cases
        if agg == 'COUNT' and '*' in expr:
            return expr
        
        # If we can't parse, check if it's a simple column reference
        if measure.source_table and '(' not in expr and '.' not in expr:
            # Simple expression - just a column name
            return f"{agg}({measure.source_table}.{self._quote_identifier(expr)})"
        
        # Fall back to original expression
        return expr
    
    def explain(self, query: SemanticQuery) -> Dict[str, Any]:
        """
        Explain the query plan without executing.
        
        Returns details about:
        - Tables used
        - Join paths
        - Aggregations applied
        - Filters interpreted
        """
        result = self.plan(query)
        
        return {
            "sql": result.sql,
            "tablesUsed": result.tables_used,
            "joinsUsed": result.joins_used,
            "warnings": result.warnings,
            "dimensions": [
                {
                    "name": d,
                    "resolved": self.semantic.get_dimension(d) is not None
                }
                for d in query.dimensions
            ],
            "measures": [
                {
                    "name": m,
                    "resolved": self.semantic.get_measure(m) is not None
                }
                for m in query.measures
            ],
            "filterCount": len(query.filters),
            "hasLimit": query.limit is not None,
        }


class SQLValidator:
    """
    Validates raw SQL queries for safety.
    """
    
    DANGEROUS_KEYWORDS = {
        "DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
        "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
        "MERGE", "CALL", "BACKUP", "RESTORE", "SHUTDOWN"
    }
    
    @classmethod
    def validate(cls, sql: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL for safety.
        
        Returns:
            (is_safe, list of issues)
        """
        issues = []
        sql_upper = sql.upper()
        
        # Check for dangerous keywords
        for keyword in cls.DANGEROUS_KEYWORDS:
            # Match word boundaries to avoid false positives
            import re
            if re.search(rf"\b{keyword}\b", sql_upper):
                issues.append(f"Dangerous keyword detected: {keyword}")
        
        # Check for multiple statements
        if sql.count(";") > 1 or (sql.count(";") == 1 and not sql.strip().endswith(";")):
            issues.append("Multiple statements not allowed")
        
        # Check for comments (could hide malicious code)
        if "--" in sql or "/*" in sql:
            issues.append("SQL comments not allowed")
        
        return len(issues) == 0, issues
    
    @classmethod
    def is_select_only(cls, sql: str) -> bool:
        """Check if SQL is a SELECT query only."""
        sql_trimmed = sql.strip().upper()
        return (
            sql_trimmed.startswith("SELECT") or
            sql_trimmed.startswith("WITH") or
            sql_trimmed.startswith("(SELECT")
        )

