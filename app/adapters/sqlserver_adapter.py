"""
Microsoft SQL Server Adapter for SetuPranali

SQL Server is ideal for:
- Enterprise Windows-based environments
- Azure SQL Database and Azure Synapse
- Existing Microsoft data warehouses
- Integration with Power BI (native)

Features:
- Connection pooling
- Windows Authentication (NTLM) and SQL Authentication
- SSL/TLS encryption
- Azure Active Directory authentication
- Read-only intent for replicas

Requirements:
    pip install pymssql
    # or for full ODBC support:
    pip install pyodbc
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

# Try pymssql first (simpler, no ODBC config needed)
try:
    import pymssql
    PYMSSQL_AVAILABLE = True
except ImportError:
    PYMSSQL_AVAILABLE = False
    pymssql = None

# Fall back to pyodbc
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class SQLServerAdapter(BaseAdapter):
    """
    Adapter for Microsoft SQL Server.
    
    Supports SQL Server 2012+ and Azure SQL Database.
    
    Config options:
        host: Server hostname or IP (required)
        port: Server port (default: 1433)
        database: Database name (required)
        user: Username (required for SQL auth)
        password: Password (required for SQL auth)
        driver: ODBC driver name (for pyodbc, default: auto-detect)
        trusted_connection: Use Windows auth (default: False)
        encrypt: Encrypt connection (default: True for Azure)
        trust_server_certificate: Trust self-signed certs (default: False)
        connection_timeout: Connection timeout in seconds (default: 30)
        query_timeout: Query timeout in seconds (default: 0 = no timeout)
        application_name: Application identifier (default: 'SetuPranali')
        read_only: Connect with read-only intent (default: True)
        azure: Connect to Azure SQL (default: auto-detect)
        
    Example (On-premises):
        adapter = SQLServerAdapter({
            "host": "sqlserver.company.com",
            "database": "analytics",
            "user": "bi_user",
            "password": "secret"
        })
        
    Example (Azure SQL):
        adapter = SQLServerAdapter({
            "host": "myserver.database.windows.net",
            "database": "analytics",
            "user": "bi_user@myserver",
            "password": "secret",
            "azure": True
        })
        
    Example (Windows Auth):
        adapter = SQLServerAdapter({
            "host": "sqlserver.company.com",
            "database": "analytics",
            "trusted_connection": True
        })
    """
    
    ENGINE = "sqlserver"
    PLACEHOLDER = "?"  # SQL Server uses ? for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SQL Server adapter."""
        super().__init__(config)
        
        # Determine driver
        self.use_pyodbc = config.get("use_pyodbc", False)
        
        if self.use_pyodbc:
            if not PYODBC_AVAILABLE:
                raise ConnectionError(
                    "pyodbc not installed. Run: pip install pyodbc",
                    engine=self.ENGINE
                )
        else:
            if not PYMSSQL_AVAILABLE:
                if PYODBC_AVAILABLE:
                    self.use_pyodbc = True
                    logger.info("pymssql not available, using pyodbc")
                else:
                    raise ConnectionError(
                        "Neither pymssql nor pyodbc installed. Run: pip install pymssql",
                        engine=self.ENGINE
                    )
        
        # Validate required config
        trusted_connection = config.get("trusted_connection", False)
        if not trusted_connection:
            required = ["host", "database", "user", "password"]
            missing = [k for k in required if k not in config]
            if missing:
                raise ConnectionError(
                    f"Missing required config: {', '.join(missing)}",
                    engine=self.ENGINE
                )
        else:
            required = ["host", "database"]
            missing = [k for k in required if k not in config]
            if missing:
                raise ConnectionError(
                    f"Missing required config: {', '.join(missing)}",
                    engine=self.ENGINE
                )
        
        # Connection settings
        self.host = config["host"]
        self.port = config.get("port", 1433)
        self.database = config["database"]
        self.user = config.get("user", "")
        self.password = config.get("password", "")
        
        # Authentication
        self.trusted_connection = config.get("trusted_connection", False)
        
        # SSL/Encryption
        self.encrypt = config.get("encrypt", "database.windows.net" in self.host.lower())
        self.trust_server_certificate = config.get("trust_server_certificate", False)
        
        # Timeouts
        self.connection_timeout = config.get("connection_timeout", 30)
        self.query_timeout = config.get("query_timeout", 0)
        
        # Application
        self.application_name = config.get("application_name", "SetuPranali")
        self.read_only = config.get("read_only", True)
        
        # Azure-specific
        self.azure = config.get("azure", "database.windows.net" in self.host.lower())
        
        # ODBC driver (for pyodbc)
        self.driver = config.get("driver", self._detect_driver() if self.use_pyodbc else None)
    
    def _detect_driver(self) -> str:
        """Auto-detect available ODBC driver."""
        if not PYODBC_AVAILABLE:
            return ""
        
        # Preferred drivers in order
        preferred_drivers = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 13.1 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "SQL Server Native Client 11.0",
            "SQL Server"
        ]
        
        available = pyodbc.drivers()
        for driver in preferred_drivers:
            if driver in available:
                return driver
        
        # Return first available SQL Server driver
        for driver in available:
            if "sql" in driver.lower():
                return driver
        
        return "ODBC Driver 17 for SQL Server"  # Default assumption
    
    def _get_pyodbc_connection_string(self) -> str:
        """Build ODBC connection string."""
        parts = [
            f"DRIVER={{{self.driver}}}",
            f"SERVER={self.host},{self.port}",
            f"DATABASE={self.database}",
            f"APP={self.application_name}",
        ]
        
        if self.trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.user}")
            parts.append(f"PWD={self.password}")
        
        if self.encrypt:
            parts.append("Encrypt=yes")
        
        if self.trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        
        if self.read_only:
            parts.append("ApplicationIntent=ReadOnly")
        
        return ";".join(parts)
    
    def connect(self) -> None:
        """Connect to SQL Server."""
        try:
            if self.use_pyodbc:
                conn_string = self._get_pyodbc_connection_string()
                self._connection = pyodbc.connect(
                    conn_string,
                    timeout=self.connection_timeout
                )
                if self.query_timeout:
                    self._connection.timeout = self.query_timeout
            else:
                # pymssql connection
                conn_params = {
                    "server": self.host,
                    "port": str(self.port),
                    "database": self.database,
                    "user": self.user,
                    "password": self.password,
                    "login_timeout": self.connection_timeout,
                    "appname": self.application_name,
                    "as_dict": False,  # We'll convert ourselves
                }
                
                # Azure requires encryption
                if self.azure or self.encrypt:
                    conn_params["tds_version"] = "7.3"
                
                self._connection = pymssql.connect(**conn_params)
            
            # Test connection
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            self._connected = True
            logger.info(f"SQL Server connected: {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to SQL Server: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close SQL Server connection."""
        try:
            if self._connection:
                self._connection.close()
                self._connection = None
        except Exception as e:
            logger.warning(f"Error closing SQL Server connection: {e}")
        finally:
            self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert placeholders for SQL Server.
        
        SQL Server uses ? for positional parameters (same as our format).
        For pyodbc, we can use ? directly.
        For pymssql, we need to use %s.
        """
        if not self.use_pyodbc and PYMSSQL_AVAILABLE:
            # pymssql uses %s like PostgreSQL
            converted_sql = sql.replace("?", "%s")
            return converted_sql, params or []
        
        # pyodbc uses ? directly
        return sql, params or []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on SQL Server.
        """
        if not self._connected:
            raise QueryError(
                "Not connected to SQL Server",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        final_sql, final_params = self.convert_placeholders(sql, params)
        
        cursor = None
        
        try:
            cursor = self._connection.cursor()
            
            # Set query timeout if specified
            if self.query_timeout and self.use_pyodbc:
                cursor.timeout = self.query_timeout
            
            # Execute query
            if final_params:
                cursor.execute(final_sql, tuple(final_params))
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
                    # Map SQL Server type codes to names
                    type_code = desc[1] if len(desc) > 1 else None
                    column_types[desc[0]] = self._map_type_code(type_code)
            
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
                    "database": self.database,
                    "driver": "pyodbc" if self.use_pyodbc else "pymssql"
                }
            )
            
        except Exception as e:
            raise QueryError(
                f"SQL Server query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _map_type_code(self, type_code) -> str:
        """Map SQL Server type code to type name."""
        if type_code is None:
            return "unknown"
        
        # Common SQL Server type mappings
        type_map = {
            1: "char",
            2: "numeric",
            3: "decimal",
            4: "int",
            5: "smallint",
            6: "float",
            7: "real",
            8: "double",
            9: "datetime",
            10: "date",
            11: "time",
            12: "varchar",
            -1: "text",
            -2: "binary",
            -3: "varbinary",
            -4: "image",
            -5: "bigint",
            -6: "tinyint",
            -7: "bit",
            -8: "nchar",
            -9: "nvarchar",
            -10: "ntext",
            -11: "uniqueidentifier",
        }
        
        return type_map.get(type_code, f"type_{type_code}")
    
    def health_check(self) -> bool:
        """Check SQL Server connection health."""
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
    
    def get_databases(self) -> List[str]:
        """Get list of databases."""
        if not self._connected:
            return []
        
        result = self.execute("SELECT name FROM sys.databases WHERE state = 0 ORDER BY name")
        return [row.get("name", "") for row in result.rows]
    
    def get_schemas(self) -> List[str]:
        """Get list of schemas in current database."""
        if not self._connected:
            return []
        
        result = self.execute("SELECT name FROM sys.schemas ORDER BY name")
        return [row.get("name", "") for row in result.rows]
    
    def get_tables(self, schema: str = "dbo") -> List[str]:
        """Get list of tables in a schema."""
        if not self._connected:
            return []
        
        result = self.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = ? AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME",
            [schema]
        )
        return [row.get("TABLE_NAME", "") for row in result.rows]
    
    def get_version(self) -> str:
        """Get SQL Server version."""
        if not self._connected:
            return ""
        
        result = self.execute("SELECT @@VERSION as version")
        if result.rows:
            return result.rows[0].get("version", "")
        return ""


# Aliases
MSSQLAdapter = SQLServerAdapter
AzureSQLAdapter = SQLServerAdapter

