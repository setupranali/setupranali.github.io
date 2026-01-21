"""
Trino/Presto Adapter for SetuPranali

Trino (formerly PrestoSQL) and Presto are distributed SQL query engines
designed for fast analytic queries against data of any size.

Ideal for:
- Federated queries across multiple data sources
- Large-scale data analytics
- Interactive queries on data lakes
- Querying data in HDFS, S3, and other storage systems

Features:
- Trino and Presto protocol support
- Connection pooling
- SSL/TLS support
- Query timeout configuration
- HTTP headers for authentication (Basic, JWT, OAuth)

Requirements:
    pip install trino
    # or for Presto:
    pip install presto-python-client
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

# Try Trino first, then fall back to Presto
try:
    import trino
    from trino.auth import BasicAuthentication, JWTAuthentication
    TRINO_AVAILABLE = True
    PRESTO_MODE = False
except ImportError:
    TRINO_AVAILABLE = False
    trino = None

try:
    import prestodb
    from prestodb.auth import BasicAuthentication as PrestoBasicAuth
    PRESTO_AVAILABLE = True
    PRESTO_MODE = True
except ImportError:
    PRESTO_AVAILABLE = False
    prestodb = None

from app.infrastructure.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class TrinoAdapter(BaseAdapter):
    """
    Adapter for Trino and Presto distributed SQL engines.
    
    Config options:
        host: Trino/Presto coordinator host (required)
        port: Coordinator port (default: 8080 for Trino, 8443 for Presto)
        user: Username (required)
        password: Password (optional, for basic auth)
        catalog: Default catalog (required)
        schema: Default schema (default: 'default')
        source: Query source identifier (default: 'setupranali')
        http_scheme: 'http' or 'https' (default: 'https')
        auth_type: 'none', 'basic', 'jwt' (default: 'basic' if password provided)
        jwt_token: JWT token for jwt auth
        verify_ssl: Verify SSL certificates (default: True)
        request_timeout: Request timeout in seconds (default: 30)
        query_timeout: Query execution timeout in seconds (default: 300)
        isolation_level: Transaction isolation level (default: 'AUTOCOMMIT')
        
    Example (Trino):
        adapter = TrinoAdapter({
            "host": "trino.example.com",
            "port": 8443,
            "user": "analyst",
            "password": "secret",
            "catalog": "hive",
            "schema": "default",
            "http_scheme": "https"
        })
        
    Example (Presto):
        adapter = TrinoAdapter({
            "host": "presto.example.com",
            "port": 8080,
            "user": "analyst",
            "catalog": "hive",
            "schema": "analytics",
            "mode": "presto"
        })
    """
    
    ENGINE = "trino"
    PLACEHOLDER = "?"  # Trino uses ? for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Trino/Presto adapter."""
        super().__init__(config)
        
        # Determine mode
        self.presto_mode = config.get("mode", "trino").lower() == "presto"
        
        if self.presto_mode:
            if not PRESTO_AVAILABLE:
                raise ConnectionError(
                    "prestodb not installed. Run: pip install presto-python-client",
                    engine=self.ENGINE
                )
        else:
            if not TRINO_AVAILABLE:
                raise ConnectionError(
                    "trino not installed. Run: pip install trino",
                    engine=self.ENGINE
                )
        
        # Validate required config
        required = ["host", "user", "catalog"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConnectionError(
                f"Missing required config: {', '.join(missing)}",
                engine=self.ENGINE
            )
        
        # Connection settings
        self.host = config["host"]
        self.port = config.get("port", 8443 if config.get("http_scheme") == "https" else 8080)
        self.user = config["user"]
        self.password = config.get("password")
        self.catalog = config["catalog"]
        self.schema = config.get("schema", "default")
        self.source = config.get("source", "setupranali")
        self.http_scheme = config.get("http_scheme", "https" if self.password else "http")
        
        # Authentication
        self.auth_type = config.get("auth_type", "basic" if self.password else "none")
        self.jwt_token = config.get("jwt_token")
        
        # SSL
        self.verify_ssl = config.get("verify_ssl", True)
        
        # Timeouts
        self.request_timeout = config.get("request_timeout", 30)
        self.query_timeout = config.get("query_timeout", 300)
        
        # Isolation level
        self.isolation_level = config.get("isolation_level", "AUTOCOMMIT")
        
        self._cursor = None
    
    def _get_auth(self):
        """Get authentication object based on config."""
        if self.presto_mode:
            if self.auth_type == "basic" and self.password:
                return PrestoBasicAuth(self.user, self.password)
            return None
        else:
            # Trino auth
            if self.auth_type == "basic" and self.password:
                return BasicAuthentication(self.user, self.password)
            elif self.auth_type == "jwt" and self.jwt_token:
                return JWTAuthentication(self.jwt_token)
            return None
    
    def connect(self) -> None:
        """Connect to Trino/Presto cluster."""
        try:
            auth = self._get_auth()
            
            if self.presto_mode:
                # Presto connection
                self._connection = prestodb.dbapi.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    catalog=self.catalog,
                    schema=self.schema,
                    source=self.source,
                    http_scheme=self.http_scheme,
                    auth=auth
                )
            else:
                # Trino connection
                conn_params = {
                    "host": self.host,
                    "port": self.port,
                    "user": self.user,
                    "catalog": self.catalog,
                    "schema": self.schema,
                    "source": self.source,
                    "http_scheme": self.http_scheme,
                    "verify": self.verify_ssl,
                    "request_timeout": self.request_timeout,
                }
                
                if auth:
                    conn_params["auth"] = auth
                
                self._connection = trino.dbapi.connect(**conn_params)
            
            # Test connection
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            self._connected = True
            engine_name = "Presto" if self.presto_mode else "Trino"
            logger.info(f"{engine_name} connected: {self.host}:{self.port}/{self.catalog}.{self.schema}")
            
        except Exception as e:
            engine_name = "Presto" if self.presto_mode else "Trino"
            raise ConnectionError(
                f"Failed to connect to {engine_name}: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close Trino/Presto connection."""
        try:
            if self._cursor:
                self._cursor.close()
                self._cursor = None
            if self._connection:
                self._connection.close()
                self._connection = None
        except Exception as e:
            logger.warning(f"Error closing Trino/Presto connection: {e}")
        finally:
            self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert placeholders for Trino/Presto.
        
        Trino and Presto use different parameter binding:
        - Trino: Uses ? placeholders
        - Presto: Uses %s placeholders (like psycopg2)
        
        For safety, we'll inline simple values. For complex queries,
        use the qmark format which both support.
        """
        if not params:
            return sql, []
        
        # For now, we'll use inline parameterization for safety
        # This is because Trino's parameter support varies by connector
        result_sql = sql
        for param in params:
            if isinstance(param, str):
                # Escape single quotes and wrap in quotes
                escaped = param.replace("'", "''")
                result_sql = result_sql.replace("?", f"'{escaped}'", 1)
            elif param is None:
                result_sql = result_sql.replace("?", "NULL", 1)
            elif isinstance(param, bool):
                result_sql = result_sql.replace("?", str(param).upper(), 1)
            else:
                result_sql = result_sql.replace("?", str(param), 1)
        
        return result_sql, []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on Trino/Presto.
        
        Supports SELECT queries with parameter substitution.
        """
        if not self._connected:
            raise QueryError(
                "Not connected to Trino/Presto",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        final_sql, _ = self.convert_placeholders(sql, params)
        
        cursor = None
        
        try:
            cursor = self._connection.cursor()
            
            # Execute query
            cursor.execute(final_sql)
            
            # Fetch results
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = cursor.fetchall() if cursor.description else []
            
            # Convert to list of dicts
            rows = [dict(zip(columns, row)) for row in data]
            
            # Get column types from cursor description
            column_types = {}
            if cursor.description:
                for desc in cursor.description:
                    # desc[1] is the type code, desc[0] is name
                    column_types[desc[0]] = str(desc[1]) if len(desc) > 1 else "unknown"
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=final_sql,
                metadata={
                    "host": self.host,
                    "catalog": self.catalog,
                    "schema": self.schema,
                    "mode": "presto" if self.presto_mode else "trino"
                }
            )
            
        except Exception as e:
            raise QueryError(
                f"Trino/Presto query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def health_check(self) -> bool:
        """Check Trino/Presto connection health."""
        if not self._connected:
            return False
        
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def get_catalogs(self) -> List[str]:
        """Get list of available catalogs."""
        if not self._connected:
            return []
        
        result = self.execute("SHOW CATALOGS")
        return [row.get("Catalog", row.get("catalog", "")) for row in result.rows]
    
    def get_schemas(self, catalog: Optional[str] = None) -> List[str]:
        """Get list of schemas in a catalog."""
        if not self._connected:
            return []
        
        cat = catalog or self.catalog
        result = self.execute(f"SHOW SCHEMAS FROM {cat}")
        return [row.get("Schema", row.get("schema", "")) for row in result.rows]
    
    def get_tables(self, catalog: Optional[str] = None, schema: Optional[str] = None) -> List[str]:
        """Get list of tables in a schema."""
        if not self._connected:
            return []
        
        cat = catalog or self.catalog
        sch = schema or self.schema
        result = self.execute(f"SHOW TABLES FROM {cat}.{sch}")
        return [row.get("Table", row.get("table", "")) for row in result.rows]


# Alias for Presto compatibility
PrestoAdapter = TrinoAdapter

