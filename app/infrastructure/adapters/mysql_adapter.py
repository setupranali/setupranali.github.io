"""
MySQL Adapter for SetuPranali

MySQL is ideal for:
- Traditional relational workloads
- Web application backends
- Read replicas for analytics
- Aurora MySQL (AWS managed)

Features:
- Connection pooling
- SSL/TLS encryption
- Read replica support
- Multiple authentication methods
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import mysql.connector
    from mysql.connector import pooling
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    mysql = None

from app.infrastructure.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class MySQLAdapter(BaseAdapter):
    """
    Adapter for MySQL database.
    
    Config options:
        host: MySQL server host (required)
        port: MySQL port (default: 3306)
        database: Database name (required)
        user: Username (required)
        password: Password (required)
        
        # Connection settings
        charset: Character set (default: utf8mb4)
        collation: Collation (default: utf8mb4_unicode_ci)
        use_pure: Use pure Python implementation (default: False)
        
        # SSL settings
        ssl_disabled: Disable SSL (default: False)
        ssl_ca: Path to CA certificate
        ssl_cert: Path to client certificate
        ssl_key: Path to client key
        ssl_verify_cert: Verify server certificate (default: True)
        ssl_verify_identity: Verify server identity (default: False)
        
        # Pool settings
        pool_size: Connection pool size (default: 5, 0 = no pooling)
        pool_name: Pool name (default: "ubi_pool")
        
        # Query settings
        connect_timeout: Connection timeout in seconds (default: 10)
        read_timeout: Read timeout in seconds (default: 30)
        write_timeout: Write timeout in seconds (default: 30)
        autocommit: Enable autocommit (default: True)
        
    Example:
        adapter = MySQLAdapter({
            "host": "mysql.example.com",
            "database": "analytics",
            "user": "bi_readonly",
            "password": "secret"
        })
        
        # With SSL
        adapter = MySQLAdapter({
            "host": "mysql.example.com",
            "database": "analytics",
            "user": "bi_readonly",
            "password": "secret",
            "ssl_ca": "/path/to/ca.pem",
            "ssl_verify_cert": True
        })
        
        adapter.connect()
        result = adapter.execute(
            "SELECT * FROM orders WHERE tenant_id = %s",
            ["tenant_a"]
        )
    """
    
    ENGINE = "mysql"
    PLACEHOLDER = "%s"  # MySQL uses %s for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize MySQL adapter."""
        super().__init__(config)
        
        if not MYSQL_AVAILABLE:
            raise ConnectionError(
                "mysql-connector-python not installed. "
                "Run: pip install mysql-connector-python",
                engine=self.ENGINE
            )
        
        # Validate required config
        required = ["host", "database", "user", "password"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConnectionError(
                f"Missing required config: {', '.join(missing)}",
                engine=self.ENGINE
            )
        
        # Store config
        self.host = config["host"]
        self.port = config.get("port", 3306)
        self.database = config["database"]
        self.user = config["user"]
        self.password = config["password"]
        
        # Catalog for StarRocks/Doris/Trino
        self.catalog = config.get("catalog", "")
        
        # Connection settings
        self.charset = config.get("charset", "utf8mb4")
        self.collation = config.get("collation", "utf8mb4_unicode_ci")
        self.use_pure = config.get("use_pure", False)
        
        # SSL settings
        self.ssl_disabled = config.get("ssl_disabled", False)
        self.ssl_ca = config.get("ssl_ca")
        self.ssl_cert = config.get("ssl_cert")
        self.ssl_key = config.get("ssl_key")
        self.ssl_verify_cert = config.get("ssl_verify_cert", True)
        self.ssl_verify_identity = config.get("ssl_verify_identity", False)
        
        # Pool settings
        self.pool_size = config.get("pool_size", 5)
        self.pool_name = config.get("pool_name", "ubi_pool")
        
        # Query settings
        self.connect_timeout = config.get("connect_timeout", 10)
        self.read_timeout = config.get("read_timeout", 30)
        self.write_timeout = config.get("write_timeout", 30)
        self.autocommit = config.get("autocommit", True)
        
        self._pool = None
    
    def _build_connection_params(self, include_database: bool = True) -> Dict[str, Any]:
        """Build connection parameters dict.
        
        Args:
            include_database: If False, don't include database in params (for catalog-first connections)
        """
        params = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "charset": self.charset,
            "collation": self.collation,
            "use_pure": self.use_pure,
            "connect_timeout": self.connect_timeout,
            "autocommit": self.autocommit,
        }
        
        # Only include database if requested and no catalog is specified
        # When catalog is specified, we connect first, set catalog, then USE database
        if include_database and not self.catalog:
            params["database"] = self.database
        
        # SSL configuration
        if not self.ssl_disabled:
            ssl_config = {}
            if self.ssl_ca:
                ssl_config["ca"] = self.ssl_ca
            if self.ssl_cert:
                ssl_config["cert"] = self.ssl_cert
            if self.ssl_key:
                ssl_config["key"] = self.ssl_key
            if ssl_config:
                ssl_config["verify_cert"] = self.ssl_verify_cert
                ssl_config["verify_identity"] = self.ssl_verify_identity
                params["ssl_ca"] = self.ssl_ca
                params["ssl_verify_cert"] = self.ssl_verify_cert
        else:
            params["ssl_disabled"] = True
        
        return params
    
    def connect(self) -> None:
        """Connect to MySQL."""
        try:
            connection_params = self._build_connection_params()
            
            catalog_info = f" (catalog: {self.catalog})" if self.catalog else ""
            logger.info(f"Connecting to MySQL: {self.host}:{self.port}/{self.database}{catalog_info}")
            
            if self.pool_size > 0:
                # Use connection pooling
                self._pool = pooling.MySQLConnectionPool(
                    pool_name=self.pool_name,
                    pool_size=self.pool_size,
                    **connection_params
                )
                # Test connection and initialize catalog/database
                conn = self._pool.get_connection()
                self._initialize_connection(conn)
                conn.close()
            else:
                # Single connection (no pooling)
                self._connection = mysql.connector.connect(**connection_params)
                # Initialize catalog and database
                self._initialize_connection(self._connection)
            
            self._connected = True
            logger.info(f"MySQL connected: {self.host}:{self.port}/{self.database}{catalog_info}")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to MySQL: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def _initialize_connection(self, conn) -> None:
        """Initialize connection with catalog and database settings."""
        cursor = conn.cursor()
        try:
            # If catalog is specified, set it first (for StarRocks/Doris)
            if self.catalog:
                logger.info(f"Setting catalog to: {self.catalog}")
                cursor.execute(f"SET CATALOG {self.catalog}")
                
                # Now switch to the database within the catalog context
                if self.database:
                    logger.info(f"Switching to database: {self.database}")
                    cursor.execute(f"USE {self.database}")
        except Exception as e:
            raise ConnectionError(
                f"Failed to initialize connection (catalog={self.catalog}, database={self.database}): {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            cursor.close()
    
    def _set_catalog(self, conn) -> None:
        """Set catalog for StarRocks/Doris connections (legacy method)."""
        if not self.catalog:
            return
        try:
            cursor = conn.cursor()
            # StarRocks/Doris use SET CATALOG
            cursor.execute(f"SET CATALOG {self.catalog}")
            if self.database:
                cursor.execute(f"USE {self.database}")
            cursor.close()
            logger.info(f"Catalog set to: {self.catalog}")
        except Exception as e:
            logger.warning(f"Failed to set catalog '{self.catalog}': {e}")
    
    def disconnect(self) -> None:
        """Close MySQL connection(s)."""
        try:
            if self._pool:
                # Pool doesn't have a close method, connections are returned
                self._pool = None
            elif self._connection:
                self._connection.close()
                self._connection = None
        except Exception as e:
            logger.warning(f"Error closing MySQL connection: {e}")
        finally:
            self._connected = False
    
    def _get_connection(self):
        """Get a connection from pool or return single connection."""
        if self._pool:
            conn = self._pool.get_connection()
            # Initialize catalog and database for each connection from pool
            if self.catalog:
                self._initialize_connection(conn)
            return conn
        return self._connection
    
    def _release_connection(self, conn):
        """Return connection to pool if using pooling."""
        if self._pool and conn:
            try:
                conn.close()  # Returns to pool
            except Exception:
                pass
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert ? placeholders to MySQL %s format.
        """
        converted_sql = sql.replace("?", "%s")
        return converted_sql, params or []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on MySQL.
        
        Supports:
        - Parameterized queries with ? or %s placeholders
        - Connection pooling
        - Result set streaming for large queries
        """
        if not self._connected:
            raise QueryError(
                "Not connected to MySQL",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        my_sql, my_params = self.convert_placeholders(sql, params)
        
        conn = None
        cursor = None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)  # Return rows as dicts
            
            # Execute query
            if my_params:
                cursor.execute(my_sql, my_params)
            else:
                cursor.execute(my_sql)
            
            # Fetch results
            columns = []
            column_types = {}
            
            if cursor.description:
                for desc in cursor.description:
                    col_name = desc[0]
                    col_type = desc[1] if len(desc) > 1 else None
                    columns.append(col_name)
                    # Map MySQL type codes to names
                    column_types[col_name] = self._type_code_to_name(col_type)
            
            # Fetch all rows (already as dicts from dictionary cursor)
            rows = cursor.fetchall() if cursor.description else []
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Build metadata
            metadata = {
                "host": self.host,
                "database": self.database,
                "row_count": cursor.rowcount if cursor.rowcount >= 0 else len(rows)
            }
            
            return AdapterResult(
                rows=list(rows),
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=my_sql,
                metadata=metadata
            )
            
        except Exception as e:
            raise QueryError(
                f"MySQL query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                self._release_connection(conn)
    
    def _type_code_to_name(self, type_code: int) -> str:
        """Convert MySQL type code to readable name."""
        if type_code is None:
            return "unknown"
        
        # MySQL field type constants
        type_map = {
            0: "DECIMAL",
            1: "TINY",
            2: "SHORT",
            3: "LONG",
            4: "FLOAT",
            5: "DOUBLE",
            6: "NULL",
            7: "TIMESTAMP",
            8: "LONGLONG",
            9: "INT24",
            10: "DATE",
            11: "TIME",
            12: "DATETIME",
            13: "YEAR",
            14: "NEWDATE",
            15: "VARCHAR",
            16: "BIT",
            245: "JSON",
            246: "NEWDECIMAL",
            247: "ENUM",
            248: "SET",
            249: "TINY_BLOB",
            250: "MEDIUM_BLOB",
            251: "LONG_BLOB",
            252: "BLOB",
            253: "VAR_STRING",
            254: "STRING",
            255: "GEOMETRY",
        }
        return type_map.get(type_code, f"TYPE_{type_code}")
    
    def health_check(self) -> bool:
        """Check MySQL connection health."""
        if not self._connected:
            return False
        
        conn = None
        cursor = None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                self._release_connection(conn)
    
    def get_databases(self) -> List[str]:
        """List available databases."""
        result = self.execute("SHOW DATABASES")
        return [row.get("Database", "") for row in result.rows]
    
    def get_tables(self, database: Optional[str] = None) -> List[str]:
        """List tables in a database."""
        db = database or self.database
        result = self.execute(f"SHOW TABLES FROM `{db}`")
        # Column name varies based on database name
        key = f"Tables_in_{db}"
        return [row.get(key, list(row.values())[0] if row else "") for row in result.rows]
    
    def get_table_schema(self, table: str, database: Optional[str] = None) -> List[Dict]:
        """Get schema for a table."""
        db = database or self.database
        result = self.execute(f"DESCRIBE `{db}`.`{table}`")
        
        return [
            {
                "name": row.get("Field", ""),
                "type": row.get("Type", ""),
                "nullable": row.get("Null", "") == "YES",
                "key": row.get("Key", ""),
                "default": row.get("Default", ""),
                "extra": row.get("Extra", "")
            }
            for row in result.rows
        ]
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get MySQL server information."""
        result = self.execute("""
            SELECT 
                VERSION() as version,
                DATABASE() as current_database,
                USER() as current_user,
                @@hostname as hostname
        """)
        
        if result.rows:
            return result.rows[0]
        return {}
    
    def get_processlist(self) -> List[Dict]:
        """Get current processes (requires PROCESS privilege)."""
        result = self.execute("SHOW PROCESSLIST")
        return result.rows
    
    def kill_query(self, process_id: int) -> bool:
        """
        Kill a running query.
        
        Requires SUPER or CONNECTION_ADMIN privilege.
        """
        try:
            self.execute(f"KILL QUERY {process_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not kill query {process_id}: {e}")
            return False

