"""
Oracle Database Adapter for SetuPranali

Oracle Database is ideal for:
- Enterprise mission-critical applications
- Oracle Cloud Infrastructure (OCI)
- Existing Oracle data warehouses
- Oracle Autonomous Database

Features:
- Connection pooling
- Oracle Wallet authentication
- SSL/TLS encryption
- Thick and Thin client modes
- Oracle Cloud (ATP/ADW) support

Requirements:
    pip install oracledb
    # or legacy driver:
    pip install cx_Oracle
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

# Try python-oracledb first (newer, recommended)
try:
    import oracledb
    ORACLEDB_AVAILABLE = True
except ImportError:
    ORACLEDB_AVAILABLE = False
    oracledb = None

# Fall back to cx_Oracle (legacy)
try:
    import cx_Oracle
    CX_ORACLE_AVAILABLE = True
except ImportError:
    CX_ORACLE_AVAILABLE = False
    cx_Oracle = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class OracleAdapter(BaseAdapter):
    """
    Adapter for Oracle Database.
    
    Supports Oracle 12c+ and Oracle Cloud (ATP/ADW).
    
    Config options:
        host: Server hostname or IP (required for basic connection)
        port: Server port (default: 1521)
        service_name: Oracle service name (required)
        sid: Oracle SID (alternative to service_name)
        user: Username (required)
        password: Password (required)
        dsn: Full DSN string (alternative to host/port/service)
        wallet_location: Path to Oracle Wallet (for cloud)
        wallet_password: Wallet password
        thick_mode: Use thick client mode (default: False)
        lib_dir: Oracle Client library directory (for thick mode)
        encoding: Character encoding (default: UTF-8)
        connection_timeout: Connection timeout in seconds (default: 30)
        query_timeout: Query timeout in seconds (default: 0 = no timeout)
        pool_min: Minimum pool size (default: 1)
        pool_max: Maximum pool size (default: 5)
        prefetch_rows: Rows to prefetch (default: 1000)
        arraysize: Fetch array size (default: 1000)
        
    Example (Basic):
        adapter = OracleAdapter({
            "host": "oracle.company.com",
            "service_name": "ORCL",
            "user": "bi_user",
            "password": "secret"
        })
        
    Example (Oracle Cloud ATP):
        adapter = OracleAdapter({
            "dsn": "myatp_high",
            "user": "ADMIN",
            "password": "secret",
            "wallet_location": "/path/to/wallet"
        })
        
    Example (Easy Connect):
        adapter = OracleAdapter({
            "dsn": "oracle.company.com:1521/ORCL",
            "user": "bi_user",
            "password": "secret"
        })
    """
    
    ENGINE = "oracle"
    PLACEHOLDER = ":"  # Oracle uses :1, :2 or :name for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Oracle adapter."""
        super().__init__(config)
        
        # Determine driver
        self.use_oracledb = True
        
        if not ORACLEDB_AVAILABLE:
            if CX_ORACLE_AVAILABLE:
                self.use_oracledb = False
                logger.info("oracledb not available, using cx_Oracle")
            else:
                raise ConnectionError(
                    "Neither oracledb nor cx_Oracle installed. Run: pip install oracledb",
                    engine=self.ENGINE
                )
        
        # Get the driver module
        self.driver = oracledb if self.use_oracledb else cx_Oracle
        
        # Validate required config
        required = ["user", "password"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConnectionError(
                f"Missing required config: {', '.join(missing)}",
                engine=self.ENGINE
            )
        
        # Connection settings
        self.user = config["user"]
        self.password = config["password"]
        self.host = config.get("host", "")
        self.port = config.get("port", 1521)
        self.service_name = config.get("service_name", "")
        self.sid = config.get("sid", "")
        self.dsn = config.get("dsn", "")
        
        # Oracle Cloud / Wallet
        self.wallet_location = config.get("wallet_location", "")
        self.wallet_password = config.get("wallet_password", "")
        
        # Client mode (thin vs thick)
        self.thick_mode = config.get("thick_mode", False)
        self.lib_dir = config.get("lib_dir", "")
        
        # Encoding
        self.encoding = config.get("encoding", "UTF-8")
        
        # Timeouts and performance
        self.connection_timeout = config.get("connection_timeout", 30)
        self.query_timeout = config.get("query_timeout", 0)
        self.prefetch_rows = config.get("prefetch_rows", 1000)
        self.arraysize = config.get("arraysize", 1000)
        
        # Connection pool settings
        self.pool_min = config.get("pool_min", 1)
        self.pool_max = config.get("pool_max", 5)
        
        # Pool reference
        self._pool = None
        
        # Initialize thick mode if needed
        if self.thick_mode and self.use_oracledb:
            try:
                if self.lib_dir:
                    oracledb.init_oracle_client(lib_dir=self.lib_dir)
                else:
                    oracledb.init_oracle_client()
            except Exception as e:
                logger.warning(f"Failed to initialize thick mode: {e}")
    
    def _build_dsn(self) -> str:
        """Build DSN from config options."""
        # If DSN is provided, use it directly
        if self.dsn:
            return self.dsn
        
        # Build Easy Connect string
        if self.service_name:
            # Easy Connect format: host:port/service_name
            return f"{self.host}:{self.port}/{self.service_name}"
        elif self.sid:
            # SID format requires makedsn
            return self.driver.makedsn(self.host, self.port, sid=self.sid)
        else:
            raise ConnectionError(
                "Either dsn, service_name, or sid must be provided",
                engine=self.ENGINE
            )
    
    def _get_connect_params(self) -> Dict[str, Any]:
        """Get connection parameters."""
        params = {
            "user": self.user,
            "password": self.password,
            "dsn": self._build_dsn(),
        }
        
        # Add wallet config for Oracle Cloud
        if self.wallet_location and self.use_oracledb:
            params["config_dir"] = self.wallet_location
            params["wallet_location"] = self.wallet_location
            if self.wallet_password:
                params["wallet_password"] = self.wallet_password
        
        return params
    
    def connect(self) -> None:
        """Connect to Oracle Database."""
        try:
            connect_params = self._get_connect_params()
            
            # Create connection (or pool)
            if self.pool_max > 1:
                # Use connection pool
                self._pool = self.driver.SessionPool(
                    user=connect_params["user"],
                    password=connect_params["password"],
                    dsn=connect_params["dsn"],
                    min=self.pool_min,
                    max=self.pool_max,
                    increment=1,
                    encoding=self.encoding if not self.use_oracledb else None,
                )
                self._connection = self._pool.acquire()
            else:
                # Single connection
                if self.use_oracledb:
                    self._connection = self.driver.connect(**connect_params)
                else:
                    self._connection = self.driver.connect(
                        user=connect_params["user"],
                        password=connect_params["password"],
                        dsn=connect_params["dsn"],
                        encoding=self.encoding,
                    )
            
            # Test connection
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.fetchone()
            cursor.close()
            
            self._connected = True
            dsn_display = self._build_dsn()
            logger.info(f"Oracle connected: {self.user}@{dsn_display}")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Oracle: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close Oracle connection."""
        try:
            if self._connection:
                if self._pool:
                    self._pool.release(self._connection)
                else:
                    self._connection.close()
                self._connection = None
            
            if self._pool:
                self._pool.close()
                self._pool = None
                
        except Exception as e:
            logger.warning(f"Error closing Oracle connection: {e}")
        finally:
            self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Convert placeholders for Oracle.
        
        Oracle uses :1, :2, etc. or :name for named parameters.
        We convert ? to :1, :2, etc.
        """
        if not params:
            return sql, {}
        
        # Replace ? with :1, :2, etc.
        result = []
        param_count = 0
        i = 0
        while i < len(sql):
            if sql[i] == '?':
                param_count += 1
                result.append(f":{param_count}")
            else:
                result.append(sql[i])
            i += 1
        
        # Convert list to dict for Oracle
        param_dict = {str(i + 1): v for i, v in enumerate(params)}
        
        return ''.join(result), param_dict
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on Oracle.
        """
        if not self._connected:
            raise QueryError(
                "Not connected to Oracle",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        final_sql, final_params = self.convert_placeholders(sql, params)
        
        cursor = None
        
        try:
            cursor = self._connection.cursor()
            
            # Set fetch performance options
            cursor.prefetchrows = self.prefetch_rows
            cursor.arraysize = self.arraysize
            
            # Execute query
            if final_params:
                cursor.execute(final_sql, final_params)
            else:
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
                    # desc[1] is the type object
                    type_obj = desc[1]
                    type_name = self._map_oracle_type(type_obj)
                    column_types[desc[0]] = type_name
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=final_sql,
                metadata={
                    "dsn": self._build_dsn(),
                    "user": self.user,
                    "driver": "oracledb" if self.use_oracledb else "cx_Oracle"
                }
            )
            
        except Exception as e:
            raise QueryError(
                f"Oracle query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _map_oracle_type(self, type_obj) -> str:
        """Map Oracle type object to type name."""
        if type_obj is None:
            return "unknown"
        
        type_name = str(type_obj).lower()
        
        # Common Oracle type mappings
        if "number" in type_name:
            return "number"
        elif "varchar" in type_name or "char" in type_name:
            return "varchar"
        elif "clob" in type_name:
            return "clob"
        elif "blob" in type_name:
            return "blob"
        elif "date" in type_name:
            return "date"
        elif "timestamp" in type_name:
            return "timestamp"
        elif "interval" in type_name:
            return "interval"
        elif "raw" in type_name:
            return "raw"
        elif "rowid" in type_name:
            return "rowid"
        elif "cursor" in type_name:
            return "cursor"
        else:
            return type_name
    
    def health_check(self) -> bool:
        """Check Oracle connection health."""
        if not self._connected:
            return False
        
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
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
    
    def get_schemas(self) -> List[str]:
        """Get list of schemas (users) in the database."""
        if not self._connected:
            return []
        
        result = self.execute(
            "SELECT username FROM all_users ORDER BY username"
        )
        return [row.get("USERNAME", "") for row in result.rows]
    
    def get_tables(self, schema: str = None) -> List[str]:
        """Get list of tables in a schema."""
        if not self._connected:
            return []
        
        if schema:
            result = self.execute(
                "SELECT table_name FROM all_tables WHERE owner = ? ORDER BY table_name",
                [schema.upper()]
            )
        else:
            result = self.execute(
                "SELECT table_name FROM user_tables ORDER BY table_name"
            )
        
        return [row.get("TABLE_NAME", "") for row in result.rows]
    
    def get_views(self, schema: str = None) -> List[str]:
        """Get list of views in a schema."""
        if not self._connected:
            return []
        
        if schema:
            result = self.execute(
                "SELECT view_name FROM all_views WHERE owner = ? ORDER BY view_name",
                [schema.upper()]
            )
        else:
            result = self.execute(
                "SELECT view_name FROM user_views ORDER BY view_name"
            )
        
        return [row.get("VIEW_NAME", "") for row in result.rows]
    
    def get_columns(self, table: str, schema: str = None) -> List[Dict[str, Any]]:
        """Get columns for a table."""
        if not self._connected:
            return []
        
        if schema:
            result = self.execute(
                """SELECT column_name, data_type, nullable, data_length, data_precision, data_scale
                   FROM all_tab_columns 
                   WHERE owner = ? AND table_name = ?
                   ORDER BY column_id""",
                [schema.upper(), table.upper()]
            )
        else:
            result = self.execute(
                """SELECT column_name, data_type, nullable, data_length, data_precision, data_scale
                   FROM user_tab_columns 
                   WHERE table_name = ?
                   ORDER BY column_id""",
                [table.upper()]
            )
        
        return result.rows
    
    def get_version(self) -> str:
        """Get Oracle version."""
        if not self._connected:
            return ""
        
        result = self.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
        if result.rows:
            return result.rows[0].get("BANNER", "")
        return ""


# Aliases
OracleDBAdapter = OracleAdapter
OCIAdapter = OracleAdapter  # Oracle Cloud Infrastructure
ATPAdapter = OracleAdapter  # Autonomous Transaction Processing
ADWAdapter = OracleAdapter  # Autonomous Data Warehouse

