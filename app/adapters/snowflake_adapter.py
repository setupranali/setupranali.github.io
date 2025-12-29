"""
Snowflake Adapter for SetuPranali

Snowflake is ideal for:
- TB to PB scale analytics
- Multi-cloud deployments (AWS, Azure, GCP)
- Separation of storage and compute
- Concurrent workloads with auto-scaling

Features:
- Connection pooling
- Warehouse auto-suspend/resume
- Query result caching (Snowflake-side)
- Session parameter configuration
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import snowflake.connector
    from snowflake.connector import DictCursor
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    snowflake = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class SnowflakeAdapter(BaseAdapter):
    """
    Adapter for Snowflake Data Cloud.
    
    Config options:
        account: Snowflake account identifier (required)
                 Format: <orgname>-<account_name> or <account_locator>.<region>.<cloud>
                 Example: "xy12345.us-east-1" or "myorg-myaccount"
        
        user: Username (required)
        password: Password (required for password auth)
        
        warehouse: Compute warehouse name (required)
        database: Default database (required)
        schema: Default schema (default: PUBLIC)
        role: Role to use (optional, uses default if not set)
        
        # Alternative auth methods
        private_key_path: Path to private key file (for key pair auth)
        private_key_passphrase: Passphrase for encrypted key
        authenticator: Auth method (default: snowflake, options: externalbrowser, oauth)
        token: OAuth token (for OAuth auth)
        
        # Connection settings
        login_timeout: Login timeout in seconds (default: 60)
        network_timeout: Network timeout in seconds (default: None)
        query_timeout: Query timeout in seconds (default: None, uses warehouse default)
        
        # Session parameters
        session_parameters: Dict of session parameters to set
            Example: {"QUERY_TAG": "ubi_connector", "STATEMENT_TIMEOUT_IN_SECONDS": 300}
    
    Example:
        adapter = SnowflakeAdapter({
            "account": "xy12345.us-east-1",
            "user": "bi_service",
            "password": "***",
            "warehouse": "BI_WH",
            "database": "ANALYTICS",
            "schema": "MARTS",
            "role": "BI_READONLY"
        })
        adapter.connect()
        result = adapter.execute(
            "SELECT * FROM ORDERS WHERE TENANT_ID = ?",
            ["tenant_a"]
        )
    """
    
    ENGINE = "snowflake"
    PLACEHOLDER = "%s"  # Snowflake connector uses %s with format
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Snowflake adapter."""
        super().__init__(config)
        
        if not SNOWFLAKE_AVAILABLE:
            raise ConnectionError(
                "snowflake-connector-python not installed. "
                "Run: pip install snowflake-connector-python",
                engine=self.ENGINE
            )
        
        # Validate required config
        required = ["account", "user", "warehouse", "database"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConnectionError(
                f"Missing required config: {', '.join(missing)}",
                engine=self.ENGINE
            )
        
        # Must have either password or private key
        has_auth = (
            config.get("password") or 
            config.get("private_key_path") or 
            config.get("authenticator") in ("externalbrowser", "oauth")
        )
        if not has_auth:
            raise ConnectionError(
                "Authentication required: provide password, private_key_path, or authenticator",
                engine=self.ENGINE
            )
        
        # Store config
        self.account = config["account"]
        self.user = config["user"]
        self.password = config.get("password")
        self.warehouse = config["warehouse"]
        self.database = config["database"]
        self.schema = config.get("schema", "PUBLIC")
        self.role = config.get("role")
        
        # Auth options
        self.private_key_path = config.get("private_key_path")
        self.private_key_passphrase = config.get("private_key_passphrase")
        self.authenticator = config.get("authenticator", "snowflake")
        self.token = config.get("token")
        
        # Connection settings
        self.login_timeout = config.get("login_timeout", 60)
        self.network_timeout = config.get("network_timeout")
        self.query_timeout = config.get("query_timeout")
        
        # Session parameters
        self.session_parameters = config.get("session_parameters", {})
        
        # Add default session parameters for BI connector
        default_params = {
            "QUERY_TAG": "universal_bi_connector",
            "CLIENT_SESSION_KEEP_ALIVE": True,
        }
        for k, v in default_params.items():
            if k not in self.session_parameters:
                self.session_parameters[k] = v
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build connection parameters dict."""
        params = {
            "account": self.account,
            "user": self.user,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
            "login_timeout": self.login_timeout,
            "session_parameters": self.session_parameters,
        }
        
        # Add optional params
        if self.password:
            params["password"] = self.password
        
        if self.role:
            params["role"] = self.role
        
        if self.network_timeout:
            params["network_timeout"] = self.network_timeout
        
        if self.authenticator and self.authenticator != "snowflake":
            params["authenticator"] = self.authenticator
        
        if self.token:
            params["token"] = self.token
        
        # Handle key pair authentication
        if self.private_key_path:
            params["private_key_path"] = self.private_key_path
            if self.private_key_passphrase:
                params["private_key_passphrase"] = self.private_key_passphrase
        
        return params
    
    def connect(self) -> None:
        """Connect to Snowflake."""
        try:
            connection_params = self._build_connection_params()
            
            logger.info(f"Connecting to Snowflake: {self.account} / {self.database}")
            
            self._connection = snowflake.connector.connect(**connection_params)
            self._connected = True
            
            logger.info(
                f"Snowflake connected: {self.account} / {self.database}.{self.schema} "
                f"(warehouse: {self.warehouse})"
            )
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Snowflake: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")
            finally:
                self._connection = None
                self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert ? placeholders to Snowflake format.
        
        Snowflake connector supports:
        - %s with pyformat (default)
        - :1, :2 with numeric
        - %(name)s with named
        
        We use %s for consistency with psycopg2.
        """
        converted_sql = sql.replace("?", "%s")
        return converted_sql, params or []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on Snowflake.
        
        Uses DictCursor for automatic dict conversion of results.
        """
        if not self._connected or not self._connection:
            raise QueryError(
                "Not connected to Snowflake",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        sf_sql, sf_params = self.convert_placeholders(sql, params)
        
        cursor = None
        
        try:
            # Use DictCursor for automatic conversion to dicts
            cursor = self._connection.cursor(DictCursor)
            
            # Set query timeout if specified
            if self.query_timeout:
                cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {self.query_timeout}")
            
            # Execute query
            cursor.execute(sf_sql, sf_params)
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Get column info from description
            columns = []
            column_types = {}
            if cursor.description:
                for desc in cursor.description:
                    col_name = desc[0]
                    col_type = desc[1]  # Type code
                    columns.append(col_name)
                    column_types[col_name] = self._type_code_to_name(col_type)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Get query metadata
            metadata = {
                "account": self.account,
                "database": self.database,
                "schema": self.schema,
                "warehouse": self.warehouse,
                "query_id": cursor.sfqid if hasattr(cursor, 'sfqid') else None,
            }
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=sf_sql,
                metadata=metadata
            )
            
        except Exception as e:
            raise QueryError(
                f"Snowflake query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                cursor.close()
    
    def _type_code_to_name(self, type_code: int) -> str:
        """Convert Snowflake type code to readable name."""
        # Snowflake type codes
        type_map = {
            0: "NUMBER",
            1: "REAL",
            2: "TEXT",
            3: "DATE",
            4: "TIMESTAMP",
            5: "VARIANT",
            6: "TIMESTAMP_LTZ",
            7: "TIMESTAMP_TZ",
            8: "TIMESTAMP_NTZ",
            9: "OBJECT",
            10: "ARRAY",
            11: "BINARY",
            12: "TIME",
            13: "BOOLEAN",
        }
        return type_map.get(type_code, f"TYPE_{type_code}")
    
    def health_check(self) -> bool:
        """Check Snowflake connection health."""
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
    
    def get_warehouses(self) -> List[str]:
        """List available warehouses."""
        result = self.execute("SHOW WAREHOUSES")
        return [row.get("name", row.get("NAME", "")) for row in result.rows]
    
    def get_databases(self) -> List[str]:
        """List available databases."""
        result = self.execute("SHOW DATABASES")
        return [row.get("name", row.get("NAME", "")) for row in result.rows]
    
    def get_schemas(self, database: Optional[str] = None) -> List[str]:
        """List schemas in database."""
        db = database or self.database
        result = self.execute(f"SHOW SCHEMAS IN DATABASE {db}")
        return [row.get("name", row.get("NAME", "")) for row in result.rows]
    
    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> List[str]:
        """List tables in schema."""
        db = database or self.database
        sch = schema or self.schema
        result = self.execute(f"SHOW TABLES IN {db}.{sch}")
        return [row.get("name", row.get("NAME", "")) for row in result.rows]
    
    def suspend_warehouse(self) -> None:
        """Suspend the warehouse to save credits."""
        try:
            self.execute(f"ALTER WAREHOUSE {self.warehouse} SUSPEND")
            logger.info(f"Warehouse {self.warehouse} suspended")
        except Exception as e:
            logger.warning(f"Could not suspend warehouse: {e}")
    
    def resume_warehouse(self) -> None:
        """Resume the warehouse."""
        try:
            self.execute(f"ALTER WAREHOUSE {self.warehouse} RESUME")
            logger.info(f"Warehouse {self.warehouse} resumed")
        except Exception as e:
            logger.warning(f"Could not resume warehouse: {e}")

