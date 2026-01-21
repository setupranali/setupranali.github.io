"""
SQL Builder using SQLGlot

Provides dialect-aware SQL generation for the UBI Connector.
Replaces manual string concatenation with programmatic SQL building.

Usage:
    builder = SQLBuilder(dialect="postgres")
    sql = builder.build_query(
        dimensions=["city", "region"],
        metrics=["SUM(revenue)", "COUNT(*)"],
        source_table="orders",
        filters={"order_date": {"gte": "2024-01-01"}},
        group_by=["city", "region"],
        order_by=[{"field": "revenue", "direction": "desc"}],
        limit=100
    )
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import date, datetime

import sqlglot
from sqlglot import expressions as exp
from sqlglot.errors import ParseError

logger = logging.getLogger(__name__)


class SQLBuilderError(Exception):
    """Base exception for SQL builder errors."""
    pass


class SQLBuilder:
    """
    Dialect-aware SQL query builder using SQLGlot.
    
    Supports:
    - Automatic dialect conversion (PostgreSQL, Snowflake, BigQuery, etc.)
    - SQL validation
    - Parameter placeholder handling
    - RLS filter injection
    - Query optimization
    """
    
    # Map of engine names to SQLGlot dialects
    DIALECT_MAP = {
        "postgres": "postgres",
        "postgresql": "postgres",
        "mysql": "mysql",
        "snowflake": "snowflake",
        "bigquery": "bigquery",
        "databricks": "spark",
        "spark": "spark",
        "redshift": "redshift",
        "clickhouse": "clickhouse",
        "duckdb": "duckdb",
        "trino": "trino",
        "presto": "presto",
        "sqlserver": "tsql",
        "mssql": "tsql",
        "oracle": "oracle",
        "sqlite": "sqlite",
        "timescaledb": "postgres",  # TimescaleDB uses PostgreSQL syntax
        "cockroachdb": "postgres",  # CockroachDB uses PostgreSQL syntax
    }
    
    def __init__(self, dialect: str = "postgres"):
        """
        Initialize SQL builder with target dialect.
        
        Args:
            dialect: Target SQL dialect (e.g., "postgres", "snowflake", "bigquery")
        """
        self.dialect = self._normalize_dialect(dialect)
        self.target_dialect = self.DIALECT_MAP.get(self.dialect, "postgres")
    
    def _normalize_dialect(self, dialect: str) -> str:
        """Normalize dialect name to standard form."""
        return dialect.lower().replace("_", "").replace("-", "")
    
    def build_query(
        self,
        dimensions: List[str],
        metrics: List[str],
        source_table: str,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[List[str]] = None,
        order_by: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        having: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Any]]:
        """
        Build a SQL SELECT query.
        
        Args:
            dimensions: List of dimension column names
            metrics: List of metric expressions (e.g., ["SUM(revenue)", "COUNT(*)"])
            source_table: Source table name (can be schema.table)
            filters: WHERE clause filters (dict format)
            group_by: GROUP BY columns (if None, inferred from dimensions)
            order_by: ORDER BY clauses [{"field": "col", "direction": "asc|desc"}]
            limit: LIMIT value
            offset: OFFSET value
            having: HAVING clause filters
        
        Returns:
            Tuple of (SQL string, parameter values)
        """
        params: List[Any] = []
        
        try:
            # Parse source table
            table_expr = self._parse_table(source_table)
            
            # Build SELECT expressions
            select_exprs = []
            
            # Add dimensions
            for dim in dimensions:
                select_exprs.append(self._parse_column(dim))
            
            # Add metrics
            for metric in metrics:
                metric_expr = self._parse_expression(metric)
                select_exprs.append(metric_expr)
            
            if not select_exprs:
                # Default to SELECT *
                select_exprs = [exp.Star()]
            
            # Build base query
            query = exp.Select().select(*select_exprs).from_(table_expr)
            
            # Add WHERE clause
            if filters:
                where_expr, where_params = self._build_filter_expression(filters)
                if where_expr:
                    query = query.where(where_expr)
                    params.extend(where_params)
            
            # Add GROUP BY
            if group_by is None:
                group_by = dimensions  # Default to dimensions
            
            if group_by and metrics:  # Only group if we have aggregations
                group_exprs = [self._parse_column(col) for col in group_by]
                query = query.group_by(*group_exprs)
            
            # Add HAVING clause
            if having:
                having_expr, having_params = self._build_filter_expression(having)
                if having_expr:
                    query = query.having(having_expr)
                    params.extend(having_params)
            
            # Add ORDER BY
            if order_by:
                order_exprs = []
                for ob in order_by:
                    col = self._parse_column(ob["field"])
                    direction = ob.get("direction", "asc").upper()
                    order_exprs.append(exp.Order(expression=col, desc=(direction == "DESC")))
                query = query.order_by(*order_exprs)
            
            # Add LIMIT
            if limit is not None:
                query = query.limit(limit)
            
            # Add OFFSET
            if offset is not None:
                query = query.offset(offset)
            
            # Convert to SQL string
            sql = query.sql(dialect=self.target_dialect, pretty=False)
            
            return sql, params
            
        except Exception as e:
            logger.error(f"SQL building failed: {e}")
            raise SQLBuilderError(f"Failed to build SQL query: {e}") from e
    
    def _parse_table(self, table_name: str) -> exp.Table:
        """Parse table name (supports schema.table format)."""
        parts = table_name.split(".", 1)
        if len(parts) == 2:
            return exp.Table(this=exp.Identifier(this=parts[1], quoted=True), db=parts[0])
        else:
            return exp.Table(this=exp.Identifier(this=table_name, quoted=True))
    
    def _parse_column(self, column_name: str) -> exp.Column:
        """Parse column name (supports table.column format)."""
        parts = column_name.split(".", 1)
        if len(parts) == 2:
            return exp.Column(this=exp.Identifier(this=parts[1], quoted=True), table=parts[0])
        else:
            return exp.Column(this=exp.Identifier(this=column_name, quoted=True))
    
    def _parse_expression(self, expression: str) -> exp.Expression:
        """Parse SQL expression (e.g., "SUM(revenue)", "COUNT(*)")."""
        try:
            # Try to parse as SQL expression
            parsed = sqlglot.parse_one(expression, read=self.target_dialect)
            return parsed
        except ParseError:
            # If parsing fails, treat as column reference
            return self._parse_column(expression)
    
    def _build_filter_expression(
        self, filters: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Tuple[Optional[exp.Expression], List[Any]]:
        """
        Build WHERE/HAVING filter expression from dict.
        
        Supports multiple formats:
        1. Query engine format: {"field": "...", "op": "...", "value": ...}
        2. Simple: {"field": "value"} -> field = value
        3. Operators: {"field": {"gte": value}} -> field >= value
        4. Complex: {"and": [...], "or": [...]}
        """
        params: List[Any] = []
        
        if not filters:
            return None, []
        
        # Handle list of conditions (implicit AND)
        if isinstance(filters, list):
            conditions = []
            for condition in filters:
                expr, p = self._build_filter_expression(condition)
                if expr:
                    conditions.append(expr)
                    params.extend(p)
            if conditions:
                return exp.And(expressions=conditions), params
            return None, []
        
        # Handle AND/OR logic
        if "and" in filters:
            conditions = []
            for condition in filters["and"]:
                expr, p = self._build_filter_expression(condition)
                if expr:
                    conditions.append(expr)
                    params.extend(p)
            if conditions:
                return exp.And(expressions=conditions), params
            return None, []
        
        if "or" in filters:
            conditions = []
            for condition in filters["or"]:
                expr, p = self._build_filter_expression(condition)
                if expr:
                    conditions.append(expr)
                    params.extend(p)
            if conditions:
                return exp.Or(expressions=conditions), params
            return None, []
        
        # Handle NOT
        if "not" in filters:
            expr, p = self._build_filter_expression(filters["not"])
            if expr:
                return exp.Not(this=expr), p
            return None, []
        
        # Handle query engine format: {"field": "...", "op": "...", "value": ...}
        if "field" in filters and "op" in filters:
            return self._build_query_engine_filter(filters, params)
        
        # Handle field operators
        for field, condition in filters.items():
            if isinstance(condition, dict):
                # Operator-based filter: {"field": {"gte": value}}
                return self._build_operator_filter(field, condition, params)
            else:
                # Simple equality: {"field": value}
                col = self._parse_column(field)
                params.append(condition)
                return exp.EQ(this=col, expression=exp.Placeholder()), params
        
        return None, []
    
    def _build_query_engine_filter(
        self, filter_dict: Dict[str, Any], params: List[Any]
    ) -> Tuple[exp.Expression, List[Any]]:
        """Build filter from query engine format: {"field": "...", "op": "...", "value": ...}"""
        field = filter_dict["field"]
        op = filter_dict["op"]
        value = filter_dict.get("value")
        col = self._parse_column(field)
        
        # Map operators
        if op == "eq":
            params.append(value)
            return exp.EQ(this=col, expression=exp.Placeholder()), params
        elif op == "ne":
            params.append(value)
            return exp.NEQ(this=col, expression=exp.Placeholder()), params
        elif op == "gt":
            params.append(value)
            return exp.GT(this=col, expression=exp.Placeholder()), params
        elif op == "gte":
            params.append(value)
            return exp.GTE(this=col, expression=exp.Placeholder()), params
        elif op == "lt":
            params.append(value)
            return exp.LT(this=col, expression=exp.Placeholder()), params
        elif op == "lte":
            params.append(value)
            return exp.LTE(this=col, expression=exp.Placeholder()), params
        elif op == "between":
            from_val = filter_dict.get("from")
            to_val = filter_dict.get("to")
            params.extend([from_val, to_val])
            return exp.Between(this=col, low=exp.Placeholder(), high=exp.Placeholder()), params
        elif op == "in":
            values = filter_dict.get("values", [value] if value is not None else [])
            params.extend(values)
            placeholders = [exp.Placeholder() for _ in values]
            return exp.In(this=col, expressions=placeholders), params
        elif op == "not_in":
            values = filter_dict.get("values", [value] if value is not None else [])
            params.extend(values)
            placeholders = [exp.Placeholder() for _ in values]
            return exp.Not(this=exp.In(this=col, expressions=placeholders)), params
        elif op == "contains":
            params.append(f"%{value}%")
            return exp.Like(this=col, expression=exp.Placeholder()), params
        elif op == "starts_with":
            params.append(f"{value}%")
            return exp.Like(this=col, expression=exp.Placeholder()), params
        elif op == "ends_with":
            params.append(f"%{value}")
            return exp.Like(this=col, expression=exp.Placeholder()), params
        elif op == "is_null":
            return exp.Is(this=col, expression=exp.Null()), params
        elif op == "is_not_null":
            return exp.IsNot(this=col, expression=exp.Null()), params
        else:
            # Default to equality
            params.append(value)
            return exp.EQ(this=col, expression=exp.Placeholder()), params
    
    def _build_operator_filter(
        self, field: str, operators: Dict[str, Any], params: List[Any]
    ) -> Tuple[exp.Expression, List[Any]]:
        """Build filter expression from operator dict."""
        col = self._parse_column(field)
        
        # Map operator names to SQLGlot expressions
        operator_map = {
            "eq": exp.EQ,
            "ne": exp.NEQ,
            "gt": exp.GT,
            "gte": exp.GTE,
            "lt": exp.LT,
            "lte": exp.LTE,
            "in": exp.In,
            "not_in": lambda this, expression: exp.Not(this=exp.In(this=this, expressions=expression)),
            "like": exp.Like,
            "not_like": lambda this, expression: exp.Not(this=exp.Like(this=this, expression=expression)),
            "is_null": lambda this, expression: exp.Is(this=this, expression=exp.Null()),
            "is_not_null": lambda this, expression: exp.IsNot(this=this, expression=exp.Null()),
        }
        
        # Handle BETWEEN
        if "between" in operators or ("from" in operators and "to" in operators):
            from_val = operators.get("from") or operators.get("between", [None])[0]
            to_val = operators.get("to") or operators.get("between", [None, None])[1]
            params.extend([from_val, to_val])
            return exp.Between(this=col, low=exp.Placeholder(), high=exp.Placeholder()), params
        
        # Handle IN / NOT IN
        if "in" in operators:
            values = operators["in"]
            if not isinstance(values, list):
                values = [values]
            params.extend(values)
            placeholders = [exp.Placeholder() for _ in values]
            return exp.In(this=col, expressions=placeholders), params
        
        if "not_in" in operators:
            values = operators["not_in"]
            if not isinstance(values, list):
                values = [values]
            params.extend(values)
            placeholders = [exp.Placeholder() for _ in values]
            return exp.Not(this=exp.In(this=col, expressions=placeholders)), params
        
        # Handle LIKE
        if "contains" in operators:
            params.append(f"%{operators['contains']}%")
            return exp.Like(this=col, expression=exp.Placeholder()), params
        
        if "starts_with" in operators:
            params.append(f"{operators['starts_with']}%")
            return exp.Like(this=col, expression=exp.Placeholder()), params
        
        if "ends_with" in operators:
            params.append(f"%{operators['ends_with']}")
            return exp.Like(this=col, expression=exp.Placeholder()), params
        
        # Handle standard operators
        for op_name, op_class in operator_map.items():
            if op_name in operators:
                value = operators[op_name]
                params.append(value)
                return op_class(this=col, expression=exp.Placeholder()), params
        
        # Default to equality
        if operators:
            value = list(operators.values())[0]
            params.append(value)
            return exp.EQ(this=col, expression=exp.Placeholder()), params
        
        return None, []
    
    def apply_rls_filter(
        self, sql: str, rls_filter: Dict[str, Any], read_dialect: Optional[str] = None
    ) -> Tuple[str, List[Any]]:
        """
        Apply Row-Level Security filter to existing SQL.
        
        Args:
            sql: Original SQL query
            rls_filter: RLS filter dict (same format as build_query filters)
            read_dialect: Dialect of input SQL (defaults to target_dialect)
        
        Returns:
            Tuple of (modified SQL, parameter values)
        """
        if not rls_filter:
            return sql, []
        
        read_dialect = read_dialect or self.target_dialect
        
        try:
            # Parse original SQL
            ast = sqlglot.parse_one(sql, read=read_dialect)
            
            # Build RLS filter expression
            rls_expr, rls_params = self._build_filter_expression(rls_filter)
            
            if not rls_expr:
                return sql, []
            
            # Add RLS filter to WHERE clause
            if ast.args.get("where"):
                # Combine with existing WHERE using AND
                existing_where = ast.args["where"]
                combined = exp.And(expressions=[existing_where, rls_expr])
                ast.set("where", combined)
            else:
                # Add new WHERE clause
                ast.set("where", rls_expr)
            
            # Convert back to SQL
            modified_sql = ast.sql(dialect=self.target_dialect, pretty=False)
            
            return modified_sql, rls_params
            
        except Exception as e:
            logger.error(f"RLS filter application failed: {e}")
            raise SQLBuilderError(f"Failed to apply RLS filter: {e}") from e
    
    def validate_sql(self, sql: str, dialect: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax.
        
        Args:
            sql: SQL query to validate
            dialect: SQL dialect (defaults to target_dialect)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        dialect = dialect or self.target_dialect
        
        try:
            sqlglot.parse_one(sql, read=dialect)
            return True, None
        except ParseError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def convert_sql(
        self, sql: str, source_dialect: str, target_dialect: Optional[str] = None
    ) -> str:
        """
        Convert SQL from one dialect to another.
        
        Args:
            sql: SQL query
            source_dialect: Source dialect
            target_dialect: Target dialect (defaults to self.target_dialect)
        
        Returns:
            Converted SQL string
        """
        target_dialect = target_dialect or self.target_dialect
        source = self.DIALECT_MAP.get(source_dialect.lower(), source_dialect)
        target = self.DIALECT_MAP.get(target_dialect.lower(), target_dialect)
        
        try:
            converted = sqlglot.transpile(sql, read=source, write=target)[0]
            return converted
        except Exception as e:
            logger.error(f"SQL conversion failed: {e}")
            raise SQLBuilderError(f"Failed to convert SQL: {e}") from e
    
    def optimize_query(self, sql: str, dialect: Optional[str] = None) -> str:
        """
        Optimize SQL query.
        
        Args:
            sql: SQL query to optimize
            dialect: SQL dialect (defaults to target_dialect)
        
        Returns:
            Optimized SQL string
        """
        dialect = dialect or self.target_dialect
        
        try:
            ast = sqlglot.parse_one(sql, read=dialect)
            optimized = sqlglot.optimize.optimize(ast)
            return optimized.sql(dialect=dialect, pretty=False)
        except Exception as e:
            logger.warning(f"Query optimization failed, returning original: {e}")
            return sql

