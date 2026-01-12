"""
Schema Introspection Module

Discovers database metadata:
- Schemas/Databases
- Tables and Views
- Columns with types, nullability, keys
- Primary keys, foreign keys
- Indexes (where available)

Supports lazy loading for large databases.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from app.adapters import get_adapter
from app.adapters.base import BaseAdapter, AdapterError

logger = logging.getLogger(__name__)


class ColumnType(str, Enum):
    """Normalized column types across databases."""
    STRING = "string"
    INTEGER = "integer"
    BIGINT = "bigint"
    FLOAT = "float"
    DOUBLE = "double"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    TIME = "time"
    BINARY = "binary"
    JSON = "json"
    ARRAY = "array"
    UNKNOWN = "unknown"


@dataclass
class ColumnInfo:
    """Column metadata."""
    name: str
    data_type: str
    normalized_type: ColumnType
    nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_ref: Optional[str] = None  # "schema.table.column"
    default_value: Optional[str] = None
    comment: Optional[str] = None
    ordinal_position: int = 0
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dataType": self.data_type,
            "normalizedType": self.normalized_type.value,
            "nullable": self.nullable,
            "isPrimaryKey": self.is_primary_key,
            "isForeignKey": self.is_foreign_key,
            "foreignKeyRef": self.foreign_key_ref,
            "defaultValue": self.default_value,
            "comment": self.comment,
            "ordinalPosition": self.ordinal_position,
            "maxLength": self.max_length,
            "precision": self.precision,
            "scale": self.scale,
        }


@dataclass
class TableInfo:
    """Table/View metadata."""
    schema_name: str
    table_name: str
    table_type: str  # "TABLE" | "VIEW" | "MATERIALIZED VIEW"
    columns: List[ColumnInfo] = field(default_factory=list)
    row_count: Optional[int] = None
    comment: Optional[str] = None
    primary_key: List[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"
    
    def to_dict(self, include_columns: bool = True) -> dict:
        result = {
            "schemaName": self.schema_name,
            "tableName": self.table_name,
            "fullName": self.full_name,
            "tableType": self.table_type,
            "rowCount": self.row_count,
            "comment": self.comment,
            "primaryKey": self.primary_key,
        }
        if include_columns:
            result["columns"] = [c.to_dict() for c in self.columns]
        return result


@dataclass
class SchemaInfo:
    """Schema/Database metadata."""
    name: str
    tables: List[TableInfo] = field(default_factory=list)
    
    def to_dict(self, include_tables: bool = True) -> dict:
        result = {"name": self.name}
        if include_tables:
            result["tables"] = [t.to_dict(include_columns=False) for t in self.tables]
        return result


class SchemaIntrospector:
    """
    Database schema introspection engine.
    
    Usage:
        introspector = SchemaIntrospector(adapter)
        schemas = introspector.get_schemas()
        tables = introspector.get_tables("public")
        columns = introspector.get_columns("public", "orders")
    """
    
    # SQL templates per database engine
    SCHEMA_QUERIES = {
        "postgres": "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')",
        "mysql": "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')",
        "snowflake": "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('INFORMATION_SCHEMA')",
        "bigquery": "SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA",
        "redshift": "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema')",
        "duckdb": "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema')",
        "clickhouse": "SELECT name FROM system.databases WHERE name NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')",
        "databricks": "SHOW SCHEMAS",
        "sqlserver": "SELECT name FROM sys.schemas WHERE name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')",
        "oracle": "SELECT username AS schema_name FROM all_users WHERE oracle_maintained = 'N'",
        "sqlite": "SELECT 'main' AS schema_name",
    }
    
    TABLE_QUERIES = {
        "postgres": """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """,
        "mysql": """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """,
        "snowflake": """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """,
        "bigquery": """
            SELECT table_name, table_type 
            FROM `{project}.{dataset}.INFORMATION_SCHEMA.TABLES`
        """,
        "duckdb": """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = ?
            ORDER BY table_name
        """,
        "clickhouse": """
            SELECT name AS table_name, engine AS table_type 
            FROM system.tables 
            WHERE database = {schema:String}
            ORDER BY name
        """,
        "sqlserver": """
            SELECT t.name AS table_name, 
                   CASE WHEN t.type = 'U' THEN 'BASE TABLE' ELSE 'VIEW' END AS table_type
            FROM sys.tables t
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = @schema
            ORDER BY t.name
        """,
        "sqlite": """
            SELECT name AS table_name, type AS table_type 
            FROM sqlite_master 
            WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """,
    }
    
    COLUMN_QUERIES = {
        "postgres": """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.ordinal_position,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_primary_key,
                fk.foreign_table_schema || '.' || fk.foreign_table_name || '.' || fk.foreign_column_name AS fk_ref
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY' 
                    AND tc.table_schema = %s AND tc.table_name = %s
            ) pk ON c.column_name = pk.column_name
            LEFT JOIN (
                SELECT 
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s AND tc.table_name = %s
            ) fk ON c.column_name = fk.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """,
        "mysql": """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.ordinal_position,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                CASE WHEN c.column_key = 'PRI' THEN 1 ELSE 0 END AS is_primary_key,
                CONCAT(kcu.referenced_table_schema, '.', kcu.referenced_table_name, '.', kcu.referenced_column_name) AS fk_ref
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu 
                ON c.table_schema = kcu.table_schema 
                AND c.table_name = kcu.table_name 
                AND c.column_name = kcu.column_name
                AND kcu.referenced_table_name IS NOT NULL
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """,
        "duckdb": """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                ordinal_position,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = ? AND table_name = ?
            ORDER BY ordinal_position
        """,
        "sqlite": """
            SELECT 
                name AS column_name,
                type AS data_type,
                CASE WHEN "notnull" = 0 THEN 'YES' ELSE 'NO' END AS is_nullable,
                dflt_value AS column_default,
                cid + 1 AS ordinal_position,
                pk AS is_primary_key
            FROM pragma_table_info(?)
            ORDER BY cid
        """,
    }
    
    # Type mapping to normalized types
    TYPE_MAPPING = {
        # String types
        "varchar": ColumnType.STRING,
        "character varying": ColumnType.STRING,
        "char": ColumnType.STRING,
        "text": ColumnType.STRING,
        "string": ColumnType.STRING,
        "nvarchar": ColumnType.STRING,
        "nchar": ColumnType.STRING,
        "ntext": ColumnType.STRING,
        "longtext": ColumnType.STRING,
        "mediumtext": ColumnType.STRING,
        "tinytext": ColumnType.STRING,
        
        # Integer types
        "int": ColumnType.INTEGER,
        "integer": ColumnType.INTEGER,
        "smallint": ColumnType.INTEGER,
        "tinyint": ColumnType.INTEGER,
        "mediumint": ColumnType.INTEGER,
        "int2": ColumnType.INTEGER,
        "int4": ColumnType.INTEGER,
        
        # Big integer
        "bigint": ColumnType.BIGINT,
        "int8": ColumnType.BIGINT,
        
        # Float types
        "float": ColumnType.FLOAT,
        "real": ColumnType.FLOAT,
        "float4": ColumnType.FLOAT,
        
        # Double types
        "double": ColumnType.DOUBLE,
        "double precision": ColumnType.DOUBLE,
        "float8": ColumnType.DOUBLE,
        
        # Decimal types
        "decimal": ColumnType.DECIMAL,
        "numeric": ColumnType.DECIMAL,
        "number": ColumnType.DECIMAL,
        "money": ColumnType.DECIMAL,
        
        # Boolean
        "boolean": ColumnType.BOOLEAN,
        "bool": ColumnType.BOOLEAN,
        "bit": ColumnType.BOOLEAN,
        
        # Date/Time types
        "date": ColumnType.DATE,
        "datetime": ColumnType.DATETIME,
        "datetime2": ColumnType.DATETIME,
        "smalldatetime": ColumnType.DATETIME,
        "timestamp": ColumnType.TIMESTAMP,
        "timestamp without time zone": ColumnType.TIMESTAMP,
        "timestamp with time zone": ColumnType.TIMESTAMP,
        "timestamptz": ColumnType.TIMESTAMP,
        "time": ColumnType.TIME,
        "time without time zone": ColumnType.TIME,
        "time with time zone": ColumnType.TIME,
        
        # Binary types
        "binary": ColumnType.BINARY,
        "varbinary": ColumnType.BINARY,
        "bytea": ColumnType.BINARY,
        "blob": ColumnType.BINARY,
        "longblob": ColumnType.BINARY,
        "mediumblob": ColumnType.BINARY,
        "tinyblob": ColumnType.BINARY,
        
        # JSON types
        "json": ColumnType.JSON,
        "jsonb": ColumnType.JSON,
        
        # Array types
        "array": ColumnType.ARRAY,
    }
    
    def __init__(self, adapter: BaseAdapter):
        """
        Initialize introspector with a database adapter.
        
        Args:
            adapter: Connected database adapter
        """
        self.adapter = adapter
        self.engine = adapter.ENGINE.lower()
        self._schema_cache: Dict[str, SchemaInfo] = {}
        self._table_cache: Dict[str, TableInfo] = {}
    
    def get_schemas(self) -> List[SchemaInfo]:
        """
        Get list of schemas/databases.
        
        Returns:
            List of SchemaInfo objects
        """
        query = self.SCHEMA_QUERIES.get(self.engine)
        if not query:
            # Fallback for unsupported engines
            query = "SELECT schema_name FROM information_schema.schemata"
        
        try:
            result = self.adapter.execute(query)
            schemas = []
            for row in result.rows:
                # Handle different column names
                name = row.get("schema_name") or row.get("name") or row.get("databaseName") or list(row.values())[0]
                schemas.append(SchemaInfo(name=name))
            return schemas
        except Exception as e:
            logger.error(f"Failed to get schemas: {e}")
            # Return default schema
            return [SchemaInfo(name="public")]
    
    def get_tables(self, schema_name: str) -> List[TableInfo]:
        """
        Get list of tables in a schema.
        
        Args:
            schema_name: Schema/database name
        
        Returns:
            List of TableInfo objects (without columns)
        """
        query_template = self.TABLE_QUERIES.get(self.engine)
        
        if self.engine == "sqlite":
            # SQLite doesn't use schema parameter
            query = self.TABLE_QUERIES.get("sqlite", "")
            params = []
        elif self.engine == "duckdb":
            query = query_template
            params = [schema_name]
        elif query_template:
            query = query_template
            params = [schema_name]
        else:
            # Fallback
            query = """
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = ?
            """
            params = [schema_name]
        
        try:
            result = self.adapter.execute(query, params if params else None)
            tables = []
            for row in result.rows:
                table_name = row.get("table_name") or row.get("name") or list(row.values())[0]
                table_type = row.get("table_type") or row.get("type") or "TABLE"
                if isinstance(table_type, str):
                    table_type = table_type.upper()
                    if table_type in ("U", "BASE TABLE"):
                        table_type = "TABLE"
                    elif table_type in ("V",):
                        table_type = "VIEW"
                
                tables.append(TableInfo(
                    schema_name=schema_name,
                    table_name=table_name,
                    table_type=table_type
                ))
            return tables
        except Exception as e:
            logger.error(f"Failed to get tables for schema {schema_name}: {e}")
            return []
    
    def get_columns(self, schema_name: str, table_name: str) -> List[ColumnInfo]:
        """
        Get columns for a specific table.
        
        Args:
            schema_name: Schema name
            table_name: Table name
        
        Returns:
            List of ColumnInfo objects
        """
        query_template = self.COLUMN_QUERIES.get(self.engine)
        
        if self.engine == "postgres":
            params = [schema_name, table_name, schema_name, table_name, schema_name, table_name]
            query = query_template
        elif self.engine == "mysql":
            params = [schema_name, table_name]
            query = query_template
        elif self.engine == "duckdb":
            params = [schema_name, table_name]
            query = query_template
        elif self.engine == "sqlite":
            params = [table_name]
            query = query_template
        else:
            # Generic fallback
            query = """
                SELECT column_name, data_type, is_nullable, ordinal_position
                FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ?
                ORDER BY ordinal_position
            """
            params = [schema_name, table_name]
        
        try:
            result = self.adapter.execute(query, params)
            columns = []
            for row in result.rows:
                col_name = row.get("column_name") or row.get("name")
                data_type = (row.get("data_type") or row.get("type") or "unknown").lower()
                is_nullable = row.get("is_nullable", "YES")
                if isinstance(is_nullable, str):
                    is_nullable = is_nullable.upper() == "YES"
                elif isinstance(is_nullable, int):
                    is_nullable = is_nullable == 0  # SQLite: 0 means nullable
                
                is_pk = row.get("is_primary_key", False)
                if isinstance(is_pk, int):
                    is_pk = is_pk > 0
                
                fk_ref = row.get("fk_ref")
                if fk_ref and fk_ref.startswith("None"):
                    fk_ref = None
                
                columns.append(ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    normalized_type=self._normalize_type(data_type),
                    nullable=is_nullable,
                    is_primary_key=bool(is_pk),
                    is_foreign_key=fk_ref is not None,
                    foreign_key_ref=fk_ref,
                    default_value=row.get("column_default"),
                    ordinal_position=row.get("ordinal_position", 0),
                    max_length=row.get("character_maximum_length"),
                    precision=row.get("numeric_precision"),
                    scale=row.get("numeric_scale"),
                ))
            return columns
        except Exception as e:
            logger.error(f"Failed to get columns for {schema_name}.{table_name}: {e}")
            return []
    
    def get_table_info(self, schema_name: str, table_name: str) -> TableInfo:
        """
        Get complete table info including columns.
        
        Args:
            schema_name: Schema name
            table_name: Table name
        
        Returns:
            TableInfo with columns populated
        """
        cache_key = f"{schema_name}.{table_name}"
        if cache_key in self._table_cache:
            return self._table_cache[cache_key]
        
        columns = self.get_columns(schema_name, table_name)
        primary_keys = [c.name for c in columns if c.is_primary_key]
        
        table_info = TableInfo(
            schema_name=schema_name,
            table_name=table_name,
            table_type="TABLE",
            columns=columns,
            primary_key=primary_keys,
        )
        
        self._table_cache[cache_key] = table_info
        return table_info
    
    def get_foreign_keys(self, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
        """
        Get foreign key relationships for a table.
        
        Returns:
            List of FK info dicts with source and target columns
        """
        columns = self.get_columns(schema_name, table_name)
        fks = []
        for col in columns:
            if col.is_foreign_key and col.foreign_key_ref:
                parts = col.foreign_key_ref.split(".")
                if len(parts) >= 3:
                    fks.append({
                        "sourceColumn": col.name,
                        "targetSchema": parts[0],
                        "targetTable": parts[1],
                        "targetColumn": parts[2],
                    })
        return fks
    
    def search_tables(self, pattern: str, schema_name: Optional[str] = None) -> List[TableInfo]:
        """
        Search for tables by name pattern.
        
        Args:
            pattern: Search pattern (case-insensitive)
            schema_name: Optional schema to filter
        
        Returns:
            List of matching TableInfo objects
        """
        pattern_lower = pattern.lower()
        results = []
        
        schemas = [SchemaInfo(name=schema_name)] if schema_name else self.get_schemas()
        
        for schema in schemas:
            tables = self.get_tables(schema.name)
            for table in tables:
                if pattern_lower in table.table_name.lower():
                    results.append(table)
        
        return results
    
    def _normalize_type(self, data_type: str) -> ColumnType:
        """Normalize database type to standard type."""
        dt = data_type.lower().split("(")[0].strip()  # Remove size info
        return self.TYPE_MAPPING.get(dt, ColumnType.UNKNOWN)
    
    def get_sample_data(
        self, 
        schema_name: str, 
        table_name: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get sample data from a table.
        
        Args:
            schema_name: Schema name
            table_name: Table name
            limit: Max rows to return
        
        Returns:
            List of row dicts
        """
        # Quote identifiers properly
        full_name = f'"{schema_name}"."{table_name}"'
        if self.engine in ("mysql", "clickhouse"):
            full_name = f"`{schema_name}`.`{table_name}`"
        elif self.engine == "sqlite":
            full_name = f'"{table_name}"'
        
        query = f"SELECT * FROM {full_name} LIMIT {limit}"
        
        try:
            result = self.adapter.execute(query)
            return result.rows
        except Exception as e:
            logger.error(f"Failed to get sample data: {e}")
            return []
    
    def get_table_stats(self, schema_name: str, table_name: str) -> Dict[str, Any]:
        """
        Get table statistics (row count, size estimate).
        """
        stats = {"rowCount": None, "sizeBytes": None}
        
        try:
            if self.engine == "postgres":
                result = self.adapter.execute(f"""
                    SELECT reltuples::bigint AS row_count,
                           pg_total_relation_size('{schema_name}.{table_name}') AS size_bytes
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = '{schema_name}' AND c.relname = '{table_name}'
                """)
                if result.rows:
                    stats["rowCount"] = result.rows[0].get("row_count")
                    stats["sizeBytes"] = result.rows[0].get("size_bytes")
            elif self.engine == "mysql":
                result = self.adapter.execute(f"""
                    SELECT table_rows AS row_count, data_length + index_length AS size_bytes
                    FROM information_schema.tables
                    WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
                """)
                if result.rows:
                    stats["rowCount"] = result.rows[0].get("row_count")
                    stats["sizeBytes"] = result.rows[0].get("size_bytes")
            else:
                # Generic count
                result = self.adapter.execute(f"SELECT COUNT(*) as cnt FROM \"{schema_name}\".\"{table_name}\"")
                if result.rows:
                    stats["rowCount"] = result.rows[0].get("cnt")
        except Exception as e:
            logger.warning(f"Could not get stats for {schema_name}.{table_name}: {e}")
        
        return stats

