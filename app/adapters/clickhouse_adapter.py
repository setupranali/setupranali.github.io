"""
ClickHouse Adapter for SetuPranali

ClickHouse is ideal for:
- Real-time analytics and OLAP
- High-speed data ingestion
- Time-series and event data
- Sub-second query performance on billions of rows

Features:
- Native protocol support (faster than HTTP)
- HTTP interface support
- Compression options
- Secure connections (TLS)
- Query settings customization
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import clickhouse_connect
    from clickhouse_connect.driver import Client as ClickHouseClient
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    clickhouse_connect = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class ClickHouseAdapter(BaseAdapter):
    """
    Adapter for ClickHouse database.
    
    Config options:
        host: ClickHouse server host (required)
        port: ClickHouse port (default: 8123 for HTTP, 9000 for native)
        
        # Authentication
        username: Username (default: "default")
        password: Password (default: "")
        
        # Database
        database: Default database (default: "default")
        
        # Connection settings
        interface: "http" or "native" (default: "http")
        secure: Use HTTPS/TLS (default: False)
        verify: Verify TLS certificates (default: True)
        
        # Query settings
        connect_timeout: Connection timeout in seconds (default: 10)
        send_receive_timeout: Query timeout in seconds (default: 300)
        compress: Enable compression (default: True)
        
        # ClickHouse-specific settings
        settings: Dict of ClickHouse query settings
            Example: {"max_execution_time": 60, "max_memory_usage": 10000000000}
    
    Example:
        # Basic connection
        adapter = ClickHouseAdapter({
            "host": "clickhouse.example.com",
            "username": "readonly",
            "password": "secret",
            "database": "analytics"
        })
        
        # Secure connection with custom settings
        adapter = ClickHouseAdapter({
            "host": "clickhouse.example.com",
            "port": 8443,
            "secure": True,
            "username": "bi_service",
            "password": "secret",
            "database": "events",
            "settings": {
                "max_execution_time": 120,
                "max_rows_to_read": 1000000000
            }
        })
        
        adapter.connect()
        result = adapter.execute(
            "SELECT * FROM events WHERE tenant_id = {tenant:String}",
            ["tenant_a"]
        )
    """
    
    ENGINE = "clickhouse"
    PLACEHOLDER = "{}"  # ClickHouse uses {param:Type} format
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ClickHouse adapter."""
        super().__init__(config)
        
        if not CLICKHOUSE_AVAILABLE:
            raise ConnectionError(
                "clickhouse-connect not installed. "
                "Run: pip install clickhouse-connect",
                engine=self.ENGINE
            )
        
        # Validate required config
        if "host" not in config:
            raise ConnectionError(
                "Missing required config: host",
                engine=self.ENGINE
            )
        
        # Store config
        self.host = config["host"]
        self.port = config.get("port")  # Let library pick default based on interface
        self.username = config.get("username", "default")
        self.password = config.get("password", "")
        self.database = config.get("database", "default")
        
        # Connection settings
        self.interface = config.get("interface", "http")
        self.secure = config.get("secure", False)
        self.verify = config.get("verify", True)
        
        # Query settings
        self.connect_timeout = config.get("connect_timeout", 10)
        self.send_receive_timeout = config.get("send_receive_timeout", 300)
        self.compress = config.get("compress", True)
        
        # ClickHouse query settings
        self.settings = config.get("settings", {})
        
        self._client = None
    
    def connect(self) -> None:
        """Connect to ClickHouse."""
        try:
            logger.info(f"Connecting to ClickHouse: {self.host}")
            
            # Build connection parameters
            connect_params = {
                "host": self.host,
                "username": self.username,
                "password": self.password,
                "database": self.database,
                "secure": self.secure,
                "verify": self.verify,
                "compress": self.compress,
                "connect_timeout": self.connect_timeout,
                "send_receive_timeout": self.send_receive_timeout,
            }
            
            # Add port if specified
            if self.port:
                connect_params["port"] = self.port
            
            # Add interface setting
            if self.interface == "native":
                connect_params["interface"] = "native"
            
            # Add custom settings
            if self.settings:
                connect_params["settings"] = self.settings
            
            self._client = clickhouse_connect.get_client(**connect_params)
            
            # Test connection
            self._client.ping()
            
            self._connected = True
            
            # Get server version
            version = self._client.server_version
            logger.info(
                f"ClickHouse connected: {self.host}/{self.database} "
                f"(version: {version})"
            )
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to ClickHouse: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close ClickHouse connection."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing ClickHouse connection: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Convert ? placeholders to ClickHouse named parameters.
        
        ClickHouse uses {param_name:Type} format for parameters.
        We convert positional ? to {p0}, {p1}, etc.
        
        The clickhouse-connect library handles type inference.
        
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
                # Use simple format - clickhouse-connect handles types
                converted_sql += f"{{{param_name}}}"
                param_dict[param_name] = params[param_index]
                param_index += 1
            else:
                converted_sql += sql[i]
            i += 1
        
        return converted_sql, param_dict
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on ClickHouse.
        
        ClickHouse supports:
        - Standard SQL with extensions
        - Parameterized queries
        - Massive parallelism for fast queries
        """
        if not self._connected or not self._client:
            raise QueryError(
                "Not connected to ClickHouse",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        ch_sql, param_dict = self.convert_placeholders(sql, params)
        
        try:
            # Execute query with parameters
            if param_dict:
                result = self._client.query(ch_sql, parameters=param_dict)
            else:
                result = self._client.query(ch_sql)
            
            # Get column info
            columns = result.column_names
            column_types = {}
            if result.column_types:
                for i, col in enumerate(columns):
                    column_types[col] = str(result.column_types[i])
            
            # Convert to list of dicts
            rows = []
            for row in result.result_rows:
                rows.append(dict(zip(columns, row)))
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Build metadata
            metadata = {
                "host": self.host,
                "database": self.database,
                "rows_read": result.summary.get("read_rows", 0) if result.summary else 0,
                "bytes_read": result.summary.get("read_bytes", 0) if result.summary else 0,
                "elapsed": result.summary.get("elapsed", 0) if result.summary else 0,
            }
            
            return AdapterResult(
                rows=rows,
                columns=list(columns),
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=ch_sql,
                metadata=metadata
            )
            
        except Exception as e:
            raise QueryError(
                f"ClickHouse query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def health_check(self) -> bool:
        """Check ClickHouse connection health."""
        if not self._connected or not self._client:
            return False
        
        try:
            return self._client.ping()
        except Exception:
            return False
    
    def get_databases(self) -> List[str]:
        """List available databases."""
        result = self.execute("SHOW DATABASES")
        return [row.get("name", row.get("NAME", "")) for row in result.rows]
    
    def get_tables(self, database: Optional[str] = None) -> List[str]:
        """List tables in a database."""
        db = database or self.database
        result = self.execute(f"SHOW TABLES FROM {db}")
        return [row.get("name", row.get("NAME", "")) for row in result.rows]
    
    def get_table_schema(self, table: str, database: Optional[str] = None) -> List[Dict]:
        """Get schema for a table."""
        db = database or self.database
        result = self.execute(f"DESCRIBE TABLE {db}.{table}")
        
        return [
            {
                "name": row.get("name", ""),
                "type": row.get("type", ""),
                "default_type": row.get("default_type", ""),
                "default_expression": row.get("default_expression", ""),
                "comment": row.get("comment", "")
            }
            for row in result.rows
        ]
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get ClickHouse server information."""
        if not self._client:
            raise QueryError("Not connected", engine=self.ENGINE)
        
        return {
            "version": self._client.server_version,
            "timezone": self._client.server_tz,
            "host": self.host,
            "database": self.database
        }
    
    def execute_command(self, command: str) -> None:
        """
        Execute a command (no result expected).
        
        Useful for DDL operations like CREATE TABLE, ALTER, etc.
        """
        if not self._connected or not self._client:
            raise QueryError("Not connected", engine=self.ENGINE)
        
        try:
            self._client.command(command)
        except Exception as e:
            raise QueryError(
                f"ClickHouse command failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def insert_data(
        self,
        table: str,
        data: List[Dict],
        database: Optional[str] = None
    ) -> int:
        """
        Insert data into a table.
        
        ClickHouse is optimized for batch inserts.
        
        Args:
            table: Table name
            data: List of row dicts
            database: Database name (uses default if not specified)
        
        Returns:
            Number of rows inserted
        """
        if not self._connected or not self._client:
            raise QueryError("Not connected", engine=self.ENGINE)
        
        if not data:
            return 0
        
        db = database or self.database
        full_table = f"{db}.{table}"
        
        # Get column names from first row
        columns = list(data[0].keys())
        
        # Convert to list of lists
        rows = [[row.get(col) for col in columns] for row in data]
        
        try:
            self._client.insert(full_table, rows, column_names=columns)
            return len(rows)
        except Exception as e:
            raise QueryError(
                f"ClickHouse insert failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )

