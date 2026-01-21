"""
Databricks Adapter for SetuPranali

Databricks is ideal for:
- Unified analytics on data lakes (Delta Lake)
- TB to PB scale with Spark/Photon
- ML and AI workloads alongside BI
- Multi-cloud (AWS, Azure, GCP)

Features:
- SQL Warehouse (serverless) support
- Classic cluster support
- Unity Catalog integration
- OAuth and PAT authentication
- Query result caching
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from databricks import sql as databricks_sql
    from databricks.sql.client import Connection as DatabricksConnection
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    databricks_sql = None

from app.infrastructure.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class DatabricksAdapter(BaseAdapter):
    """
    Adapter for Databricks SQL.
    
    Config options:
        server_hostname: Databricks workspace hostname (required)
                        Example: "dbc-abc12345-1234.cloud.databricks.com"
        
        http_path: SQL Warehouse or cluster HTTP path (required)
                   Example: "/sql/1.0/warehouses/abc123" (SQL Warehouse)
                   Example: "/sql/protocolv1/o/0/1234-567890-abcd12" (Cluster)
        
        # Authentication (one required)
        access_token: Personal Access Token (PAT)
        # OR OAuth (for service principals)
        client_id: OAuth client ID
        client_secret: OAuth client secret
        
        # Optional settings
        catalog: Unity Catalog name (default: uses workspace default)
        schema: Default schema (default: "default")
        timeout: Query timeout in seconds (default: 300)
        
        # Connection settings
        retry_count: Number of retries on transient errors (default: 3)
        retry_delay: Delay between retries in seconds (default: 1)
    
    Example:
        # Using Personal Access Token
        adapter = DatabricksAdapter({
            "server_hostname": "dbc-abc12345-1234.cloud.databricks.com",
            "http_path": "/sql/1.0/warehouses/abc123def456",
            "access_token": "dapi1234567890abcdef",
            "catalog": "main",
            "schema": "analytics"
        })
        
        # Using OAuth (Service Principal)
        adapter = DatabricksAdapter({
            "server_hostname": "dbc-abc12345-1234.cloud.databricks.com",
            "http_path": "/sql/1.0/warehouses/abc123def456",
            "client_id": "your-client-id",
            "client_secret": "your-client-secret",
            "catalog": "main"
        })
        
        adapter.connect()
        result = adapter.execute(
            "SELECT * FROM orders WHERE tenant_id = ?",
            ["tenant_a"]
        )
    """
    
    ENGINE = "databricks"
    PLACEHOLDER = "?"  # Databricks SQL uses ? for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Databricks adapter."""
        super().__init__(config)
        
        if not DATABRICKS_AVAILABLE:
            raise ConnectionError(
                "databricks-sql-connector not installed. "
                "Run: pip install databricks-sql-connector",
                engine=self.ENGINE
            )
        
        # Validate required config
        required = ["server_hostname", "http_path"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConnectionError(
                f"Missing required config: {', '.join(missing)}",
                engine=self.ENGINE
            )
        
        # Must have either access_token or OAuth credentials
        has_auth = (
            config.get("access_token") or 
            (config.get("client_id") and config.get("client_secret"))
        )
        if not has_auth:
            raise ConnectionError(
                "Authentication required: provide access_token or (client_id + client_secret)",
                engine=self.ENGINE
            )
        
        # Store config
        self.server_hostname = config["server_hostname"]
        self.http_path = config["http_path"]
        self.access_token = config.get("access_token")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.catalog = config.get("catalog")
        self.schema = config.get("schema", "default")
        self.timeout = config.get("timeout", 300)
        self.retry_count = config.get("retry_count", 3)
        self.retry_delay = config.get("retry_delay", 1)
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build connection parameters dict."""
        params = {
            "server_hostname": self.server_hostname,
            "http_path": self.http_path,
        }
        
        # Authentication
        if self.access_token:
            params["access_token"] = self.access_token
        else:
            # OAuth authentication
            params["credentials_provider"] = self._get_oauth_provider()
        
        # Optional: catalog and schema
        if self.catalog:
            params["catalog"] = self.catalog
        if self.schema:
            params["schema"] = self.schema
        
        return params
    
    def _get_oauth_provider(self):
        """Get OAuth credentials provider for service principal auth."""
        try:
            from databricks.sdk.core import oauth_service_principal
            return oauth_service_principal(
                self.client_id,
                self.client_secret
            )
        except ImportError:
            # Fallback for older SDK versions
            raise ConnectionError(
                "OAuth authentication requires databricks-sdk. "
                "Install with: pip install databricks-sdk",
                engine=self.ENGINE
            )
    
    def connect(self) -> None:
        """Connect to Databricks SQL."""
        try:
            connection_params = self._build_connection_params()
            
            logger.info(f"Connecting to Databricks: {self.server_hostname}")
            
            self._connection = databricks_sql.connect(**connection_params)
            self._connected = True
            
            catalog_info = f" (catalog: {self.catalog})" if self.catalog else ""
            logger.info(
                f"Databricks connected: {self.server_hostname}{catalog_info}"
            )
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Databricks: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close Databricks connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing Databricks connection: {e}")
            finally:
                self._connection = None
                self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Convert ? placeholders to Databricks named parameters.
        
        Databricks SQL connector uses %(name)s or named parameter style.
        We convert positional ? to :p0, :p1, :p2, etc. with a dict.
        
        Returns:
            (converted_sql, parameter_dict)
        """
        if not params:
            return sql, {}
        
        param_dict = {}
        param_index = 0
        converted_sql = ""
        i = 0
        
        while i < len(sql):
            if sql[i] == '?':
                param_name = f"p{param_index}"
                converted_sql += f":{param_name}"
                param_dict[param_name] = params[param_index]
                param_index += 1
            else:
                converted_sql += sql[i]
            i += 1
        
        return converted_sql, param_dict
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on Databricks.
        
        Supports:
        - Parameterized queries with ? placeholders
        - Unity Catalog fully qualified names
        - Delta Lake tables
        """
        if not self._connected or not self._connection:
            raise QueryError(
                "Not connected to Databricks",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders to named parameters
        db_sql, param_dict = self.convert_placeholders(sql, params)
        
        cursor = None
        
        try:
            cursor = self._connection.cursor()
            
            # Execute with parameters
            if param_dict:
                cursor.execute(db_sql, param_dict)
            else:
                cursor.execute(db_sql)
            
            # Fetch results
            rows_raw = cursor.fetchall()
            
            # Get column info
            columns = []
            column_types = {}
            if cursor.description:
                for desc in cursor.description:
                    col_name = desc[0]
                    col_type = desc[1] if len(desc) > 1 else "STRING"
                    columns.append(col_name)
                    column_types[col_name] = str(col_type) if col_type else "STRING"
            
            # Convert to list of dicts
            rows = [dict(zip(columns, row)) for row in rows_raw]
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Build metadata
            metadata = {
                "server_hostname": self.server_hostname,
                "catalog": self.catalog,
                "schema": self.schema,
            }
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=db_sql,
                metadata=metadata
            )
            
        except Exception as e:
            raise QueryError(
                f"Databricks query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                cursor.close()
    
    def health_check(self) -> bool:
        """Check Databricks connection health."""
        if not self._connected or not self._connection:
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
                cursor.close()
    
    def get_catalogs(self) -> List[str]:
        """List available Unity Catalogs."""
        result = self.execute("SHOW CATALOGS")
        return [row.get("catalog", row.get("CATALOG", "")) for row in result.rows]
    
    def get_schemas(self, catalog: Optional[str] = None) -> List[str]:
        """List schemas in a catalog."""
        cat = catalog or self.catalog or "main"
        result = self.execute(f"SHOW SCHEMAS IN {cat}")
        return [
            row.get("databaseName", row.get("namespace", row.get("SCHEMA_NAME", ""))) 
            for row in result.rows
        ]
    
    def get_tables(self, catalog: Optional[str] = None, schema: Optional[str] = None) -> List[str]:
        """List tables in a schema."""
        cat = catalog or self.catalog or "main"
        sch = schema or self.schema or "default"
        result = self.execute(f"SHOW TABLES IN {cat}.{sch}")
        return [
            row.get("tableName", row.get("TABLE_NAME", "")) 
            for row in result.rows
        ]
    
    def get_table_schema(
        self, 
        table: str, 
        catalog: Optional[str] = None, 
        schema: Optional[str] = None
    ) -> List[Dict]:
        """Get schema for a table."""
        cat = catalog or self.catalog or "main"
        sch = schema or self.schema or "default"
        full_name = f"{cat}.{sch}.{table}"
        
        result = self.execute(f"DESCRIBE TABLE {full_name}")
        
        return [
            {
                "name": row.get("col_name", row.get("COLUMN_NAME", "")),
                "type": row.get("data_type", row.get("DATA_TYPE", "")),
                "comment": row.get("comment", "")
            }
            for row in result.rows
            if row.get("col_name", row.get("COLUMN_NAME", ""))  # Filter empty rows
        ]
    
    def get_warehouse_info(self) -> Dict[str, Any]:
        """Get information about the connected SQL Warehouse."""
        # Extract warehouse ID from http_path if it's a SQL Warehouse
        if "/sql/1.0/warehouses/" in self.http_path:
            warehouse_id = self.http_path.split("/sql/1.0/warehouses/")[1].split("/")[0]
            return {
                "type": "sql_warehouse",
                "warehouse_id": warehouse_id,
                "http_path": self.http_path
            }
        else:
            return {
                "type": "cluster",
                "http_path": self.http_path
            }

