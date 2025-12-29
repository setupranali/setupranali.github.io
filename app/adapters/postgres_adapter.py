"""
PostgreSQL Adapter for SetuPranali

PostgreSQL is ideal for:
- Small to medium datasets (up to ~100GB efficiently)
- Transactional workloads with analytics
- Existing Postgres data warehouses

Features:
- Connection pooling (optional, via config)
- SSL support
- Read replica support
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import psycopg2
    import psycopg2.pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class PostgresAdapter(BaseAdapter):
    """
    Adapter for PostgreSQL database.
    
    Config options:
        host: Database host (required)
        port: Database port (default: 5432)
        database: Database name (required)
        user: Username (required)
        password: Password (required)
        sslmode: SSL mode (default: prefer)
        connect_timeout: Connection timeout in seconds (default: 10)
        pool_size: Connection pool size (default: 5, 0 = no pooling)
    
    Example:
        adapter = PostgresAdapter({
            "host": "localhost",
            "database": "analytics",
            "user": "readonly",
            "password": "secret"
        })
        adapter.connect()
        result = adapter.execute("SELECT * FROM orders WHERE tenant_id = ?", ["tenant_a"])
    """
    
    ENGINE = "postgres"
    PLACEHOLDER = "%s"  # PostgreSQL uses %s for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize PostgreSQL adapter."""
        super().__init__(config)
        
        if not PSYCOPG2_AVAILABLE:
            raise ConnectionError(
                "psycopg2 not installed. Run: pip install psycopg2-binary",
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
        
        self.host = config["host"]
        self.port = config.get("port", 5432)
        self.database = config["database"]
        self.user = config["user"]
        self.password = config["password"]
        self.sslmode = config.get("sslmode", "prefer")
        self.connect_timeout = config.get("connect_timeout", 10)
        self.pool_size = config.get("pool_size", 5)
        
        self._pool = None
    
    def connect(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            if self.pool_size > 0:
                # Use connection pooling
                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=self.pool_size,
                    host=self.host,
                    port=self.port,
                    dbname=self.database,
                    user=self.user,
                    password=self.password,
                    sslmode=self.sslmode,
                    connect_timeout=self.connect_timeout
                )
                # Test connection
                conn = self._pool.getconn()
                self._pool.putconn(conn)
            else:
                # Single connection (no pooling)
                self._connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=self.database,
                    user=self.user,
                    password=self.password,
                    sslmode=self.sslmode,
                    connect_timeout=self.connect_timeout
                )
            
            self._connected = True
            logger.info(f"PostgreSQL connected: {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to PostgreSQL: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection(s)."""
        try:
            if self._pool:
                self._pool.closeall()
                self._pool = None
            elif self._connection:
                self._connection.close()
                self._connection = None
        except Exception as e:
            logger.warning(f"Error closing PostgreSQL connection: {e}")
        finally:
            self._connected = False
    
    def _get_connection(self):
        """Get a connection from pool or return single connection."""
        if self._pool:
            return self._pool.getconn()
        return self._connection
    
    def _release_connection(self, conn):
        """Return connection to pool if using pooling."""
        if self._pool:
            self._pool.putconn(conn)
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """Convert ? placeholders to PostgreSQL %s format."""
        # Replace ? with %s
        converted_sql = sql.replace("?", "%s")
        return converted_sql, params or []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on PostgreSQL.
        
        Automatically converts ? placeholders to %s format.
        """
        if not self._connected:
            raise QueryError(
                "Not connected to PostgreSQL",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        pg_sql, pg_params = self.convert_placeholders(sql, params)
        
        conn = None
        cursor = None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Execute query
            cursor.execute(pg_sql, pg_params)
            
            # Fetch results
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = cursor.fetchall() if cursor.description else []
            
            # Convert to list of dicts
            rows = [dict(zip(columns, row)) for row in data]
            
            # Get column types from cursor description
            column_types = {}
            if cursor.description:
                for desc in cursor.description:
                    # desc[1] is the type OID, we'll just use the name
                    column_types[desc[0]] = str(desc[1])
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=pg_sql,
                metadata={
                    "host": self.host,
                    "database": self.database
                }
            )
            
        except Exception as e:
            # Rollback on error
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise QueryError(
                f"PostgreSQL query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                self._release_connection(conn)
    
    def health_check(self) -> bool:
        """Check PostgreSQL connection health."""
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

