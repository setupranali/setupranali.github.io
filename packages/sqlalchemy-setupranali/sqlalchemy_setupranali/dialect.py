"""
SQLAlchemy Dialect for SetuPranali

This module implements a SQLAlchemy dialect that allows connecting
to SetuPranali via its SQL API endpoint.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from sqlalchemy import types, util
from sqlalchemy.engine import default
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import compiler

from sqlalchemy_setupranali.base import (
    SetuPranaliConnection,
    SetuPranaliDBAPI,
    ProgrammingError,
)

logger = logging.getLogger(__name__)


class SetuPranaliIdentifierPreparer(compiler.IdentifierPreparer):
    """Identifier preparer for SetuPranali."""
    
    reserved_words = set([
        "select", "from", "where", "and", "or", "not", "in", "is", "null",
        "true", "false", "like", "between", "case", "when", "then", "else",
        "end", "as", "order", "by", "group", "having", "limit", "offset",
        "join", "left", "right", "inner", "outer", "full", "cross", "on",
        "union", "intersect", "except", "all", "distinct", "asc", "desc",
    ])
    
    def __init__(self, dialect):
        super().__init__(
            dialect,
            initial_quote='"',
            final_quote='"',
        )


class SetuPranaliCompiler(compiler.SQLCompiler):
    """SQL Compiler for SetuPranali."""
    
    def limit_clause(self, select, **kw):
        """Generate LIMIT clause."""
        text = ""
        if select._limit_clause is not None:
            text += " \n LIMIT " + self.process(select._limit_clause, **kw)
        if select._offset_clause is not None:
            text += " \n OFFSET " + self.process(select._offset_clause, **kw)
        return text
    
    def visit_now_func(self, fn, **kw):
        """Handle NOW() function."""
        return "CURRENT_TIMESTAMP"


class SetuPranaliTypeCompiler(compiler.GenericTypeCompiler):
    """Type compiler for SetuPranali."""
    
    def visit_FLOAT(self, type_, **kw):
        return "DOUBLE"
    
    def visit_REAL(self, type_, **kw):
        return "DOUBLE"
    
    def visit_NUMERIC(self, type_, **kw):
        return "DECIMAL"
    
    def visit_DECIMAL(self, type_, **kw):
        return "DECIMAL"
    
    def visit_INTEGER(self, type_, **kw):
        return "INTEGER"
    
    def visit_SMALLINT(self, type_, **kw):
        return "INTEGER"
    
    def visit_BIGINT(self, type_, **kw):
        return "BIGINT"
    
    def visit_BOOLEAN(self, type_, **kw):
        return "BOOLEAN"
    
    def visit_TIMESTAMP(self, type_, **kw):
        return "TIMESTAMP"
    
    def visit_DATE(self, type_, **kw):
        return "DATE"
    
    def visit_TIME(self, type_, **kw):
        return "TIME"
    
    def visit_CLOB(self, type_, **kw):
        return "TEXT"
    
    def visit_VARCHAR(self, type_, **kw):
        return "VARCHAR"
    
    def visit_CHAR(self, type_, **kw):
        return "CHAR"
    
    def visit_TEXT(self, type_, **kw):
        return "TEXT"


class SetuPranaliDialect(default.DefaultDialect):
    """
    SQLAlchemy Dialect for SetuPranali.
    
    Connection URL format:
        setupranali+http://host:port?api_key=key&database=dataset
        setupranali+https://host:port?api_key=key&database=dataset
    
    Examples:
        # Local development
        setupranali+http://localhost:8080?api_key=my-key
        
        # Production with HTTPS
        setupranali+https://bi-api.company.com?api_key=my-key&database=orders
        
        # With default dataset
        setupranali+http://localhost:8080?api_key=my-key&database=orders
    """
    
    name = "setupranali"
    driver = "http"
    
    # Dialect features
    supports_alter = False
    supports_pk_autoincrement = False
    supports_default_values = False
    supports_empty_insert = False
    supports_unicode_statements = True
    supports_unicode_binds = True
    supports_statement_cache = True
    returns_unicode_strings = True
    supports_native_boolean = True
    supports_simple_order_by_label = True
    
    # No transactions (read-only)
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False
    
    # Identifiers
    max_identifier_length = 255
    
    # Compiler classes
    statement_compiler = SetuPranaliCompiler
    type_compiler = SetuPranaliTypeCompiler
    preparer = SetuPranaliIdentifierPreparer
    
    # Type mapping
    colspecs = {}
    ischema_names = {
        "STRING": types.String,
        "VARCHAR": types.String,
        "TEXT": types.Text,
        "INTEGER": types.Integer,
        "INT": types.Integer,
        "BIGINT": types.BigInteger,
        "FLOAT": types.Float,
        "DOUBLE": types.Float,
        "DECIMAL": types.Numeric,
        "NUMBER": types.Numeric,
        "BOOLEAN": types.Boolean,
        "DATE": types.Date,
        "TIMESTAMP": types.DateTime,
        "DATETIME": types.DateTime,
        "TIME": types.Time,
    }
    
    @classmethod
    def dbapi(cls):
        """Return the DBAPI module."""
        return SetuPranaliDBAPI
    
    @classmethod
    def import_dbapi(cls):
        """Import and return the DBAPI module."""
        return SetuPranaliDBAPI
    
    def create_connect_args(self, url: URL) -> Tuple[List, Dict]:
        """
        Build connection arguments from URL.
        
        URL format: setupranali+http://host:port?api_key=key&database=dataset
        """
        # Parse URL
        host = url.host or "localhost"
        port = url.port or 8080
        
        # Determine scheme from driver
        scheme = "https" if "https" in (url.drivername or "") else "http"
        
        # Parse query parameters
        query = dict(url.query) if url.query else {}
        
        # Get API key from query or password
        api_key = query.pop("api_key", None) or url.password or ""
        
        # Get default database/dataset
        database = query.pop("database", None) or url.database or ""
        
        # Get timeout
        timeout = int(query.pop("timeout", 30))
        
        kwargs = {
            "host": host,
            "port": port,
            "api_key": api_key,
            "scheme": scheme,
            "database": database,
            "timeout": timeout,
        }
        
        return [], kwargs
    
    def do_ping(self, dbapi_connection) -> bool:
        """Check if connection is alive."""
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False
    
    def get_schema_names(self, connection, **kw) -> List[str]:
        """Get schema names (returns empty list - SetuPranali uses flat namespace)."""
        return []
    
    def get_table_names(self, connection, schema=None, **kw) -> List[str]:
        """Get table (dataset) names."""
        try:
            return connection.connection._get_tables()
        except Exception as e:
            logger.warning(f"Failed to get table names: {e}")
            return []
    
    def get_view_names(self, connection, schema=None, **kw) -> List[str]:
        """Get view names (SetuPranali doesn't distinguish views)."""
        return []
    
    def has_table(self, connection, table_name, schema=None, **kw) -> bool:
        """Check if table exists."""
        tables = self.get_table_names(connection, schema)
        return table_name in tables
    
    def get_columns(self, connection, table_name, schema=None, **kw) -> List[Dict]:
        """Get column information for a table."""
        try:
            raw_columns = connection.connection._get_columns(table_name)
            
            columns = []
            for col in raw_columns:
                col_type = self._map_column_type(col.get("type", "string"))
                columns.append({
                    "name": col["name"],
                    "type": col_type,
                    "nullable": col.get("nullable", True),
                    "default": None,
                    "autoincrement": False,
                    "comment": col.get("description"),
                })
            
            return columns
        except Exception as e:
            logger.warning(f"Failed to get columns for {table_name}: {e}")
            return []
    
    def get_pk_constraint(self, connection, table_name, schema=None, **kw) -> Dict:
        """Get primary key constraint (none for SetuPranali)."""
        return {"constrained_columns": [], "name": None}
    
    def get_foreign_keys(self, connection, table_name, schema=None, **kw) -> List:
        """Get foreign keys (none for SetuPranali)."""
        return []
    
    def get_indexes(self, connection, table_name, schema=None, **kw) -> List:
        """Get indexes (none for SetuPranali)."""
        return []
    
    def get_unique_constraints(self, connection, table_name, schema=None, **kw) -> List:
        """Get unique constraints (none for SetuPranali)."""
        return []
    
    def get_check_constraints(self, connection, table_name, schema=None, **kw) -> List:
        """Get check constraints (none for SetuPranali)."""
        return []
    
    def _map_column_type(self, type_name: str) -> types.TypeEngine:
        """Map SetuPranali type to SQLAlchemy type."""
        type_map = {
            "string": types.String(),
            "varchar": types.String(),
            "text": types.Text(),
            "number": types.Numeric(),
            "integer": types.Integer(),
            "int": types.Integer(),
            "bigint": types.BigInteger(),
            "float": types.Float(),
            "double": types.Float(),
            "decimal": types.Numeric(),
            "boolean": types.Boolean(),
            "date": types.Date(),
            "timestamp": types.DateTime(),
            "datetime": types.DateTime(),
            "time": types.Time(),
        }
        return type_map.get(type_name.lower(), types.String())


# Register dialect
from sqlalchemy.dialects import registry
registry.register("setupranali", "sqlalchemy_setupranali.dialect", "SetuPranaliDialect")
registry.register("setupranali.http", "sqlalchemy_setupranali.dialect", "SetuPranaliDialect")
registry.register("setupranali.https", "sqlalchemy_setupranali.dialect", "SetuPranaliDialect")

