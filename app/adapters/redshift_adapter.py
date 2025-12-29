"""
Amazon Redshift Adapter for SetuPranali

Amazon Redshift is ideal for:
- AWS-native data warehousing
- Petabyte-scale analytics
- Tight integration with S3 and AWS ecosystem
- Columnar storage with MPP architecture

Features:
- IAM authentication support
- Serverless and provisioned clusters
- Connection pooling
- SSL/TLS encryption
- Workload Management (WLM) queue support
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import redshift_connector
    REDSHIFT_AVAILABLE = True
except ImportError:
    REDSHIFT_AVAILABLE = False
    redshift_connector = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class RedshiftAdapter(BaseAdapter):
    """
    Adapter for Amazon Redshift.
    
    Config options:
        host: Redshift cluster endpoint (required)
              Example: "my-cluster.abc123.us-east-1.redshift.amazonaws.com"
        
        port: Redshift port (default: 5439)
        database: Database name (required)
        
        # Authentication (choose one method)
        # Method 1: Username/Password
        user: Username
        password: Password
        
        # Method 2: IAM Authentication
        iam: True to enable IAM auth
        cluster_identifier: Cluster ID (required for IAM)
        region: AWS region (required for IAM)
        profile: AWS profile name (optional)
        access_key_id: AWS access key (optional, uses default chain if not set)
        secret_access_key: AWS secret key (optional)
        session_token: AWS session token (optional, for temporary credentials)
        
        # Connection settings
        ssl: Enable SSL (default: True)
        sslmode: SSL mode - verify-ca, verify-full, require, prefer (default: verify-full)
        timeout: Connection timeout in seconds (default: 30)
        
        # Query settings
        application_name: Application name for tracking (default: "universal_bi_connector")
        
    Example:
        # Username/Password authentication
        adapter = RedshiftAdapter({
            "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
            "database": "analytics",
            "user": "bi_readonly",
            "password": "secret"
        })
        
        # IAM authentication
        adapter = RedshiftAdapter({
            "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
            "database": "analytics",
            "iam": True,
            "cluster_identifier": "my-cluster",
            "region": "us-east-1",
            "user": "iam_user"
        })
        
        adapter.connect()
        result = adapter.execute(
            "SELECT * FROM orders WHERE tenant_id = %s",
            ["tenant_a"]
        )
    """
    
    ENGINE = "redshift"
    PLACEHOLDER = "%s"  # Redshift uses PostgreSQL-style %s
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Redshift adapter."""
        super().__init__(config)
        
        if not REDSHIFT_AVAILABLE:
            raise ConnectionError(
                "redshift-connector not installed. "
                "Run: pip install redshift-connector",
                engine=self.ENGINE
            )
        
        # Validate required config
        required = ["host", "database"]
        missing = [k for k in required if k not in config]
        if missing:
            raise ConnectionError(
                f"Missing required config: {', '.join(missing)}",
                engine=self.ENGINE
            )
        
        # Store config
        self.host = config["host"]
        self.port = config.get("port", 5439)
        self.database = config["database"]
        
        # Authentication
        self.user = config.get("user")
        self.password = config.get("password")
        self.iam = config.get("iam", False)
        self.cluster_identifier = config.get("cluster_identifier")
        self.region = config.get("region")
        self.profile = config.get("profile")
        self.access_key_id = config.get("access_key_id")
        self.secret_access_key = config.get("secret_access_key")
        self.session_token = config.get("session_token")
        
        # Validate auth
        if not self.iam and not (self.user and self.password):
            raise ConnectionError(
                "Authentication required: provide user/password or enable IAM auth",
                engine=self.ENGINE
            )
        
        if self.iam and not self.cluster_identifier:
            raise ConnectionError(
                "cluster_identifier required for IAM authentication",
                engine=self.ENGINE
            )
        
        # Connection settings
        self.ssl = config.get("ssl", True)
        self.sslmode = config.get("sslmode", "verify-full")
        self.timeout = config.get("timeout", 30)
        self.application_name = config.get("application_name", "universal_bi_connector")
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build connection parameters dict."""
        params = {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "ssl": self.ssl,
            "sslmode": self.sslmode,
            "timeout": self.timeout,
            "application_name": self.application_name,
        }
        
        if self.iam:
            # IAM authentication
            params["iam"] = True
            params["cluster_identifier"] = self.cluster_identifier
            params["db_user"] = self.user
            
            if self.region:
                params["region"] = self.region
            if self.profile:
                params["profile"] = self.profile
            if self.access_key_id:
                params["access_key_id"] = self.access_key_id
            if self.secret_access_key:
                params["secret_access_key"] = self.secret_access_key
            if self.session_token:
                params["session_token"] = self.session_token
        else:
            # Username/password authentication
            params["user"] = self.user
            params["password"] = self.password
        
        return params
    
    def connect(self) -> None:
        """Connect to Redshift."""
        try:
            connection_params = self._build_connection_params()
            
            auth_type = "IAM" if self.iam else "password"
            logger.info(f"Connecting to Redshift: {self.host} ({auth_type} auth)")
            
            self._connection = redshift_connector.connect(**connection_params)
            self._connected = True
            
            logger.info(f"Redshift connected: {self.host}/{self.database}")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Redshift: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close Redshift connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing Redshift connection: {e}")
            finally:
                self._connection = None
                self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert ? placeholders to Redshift %s format.
        
        Redshift uses PostgreSQL-style %s placeholders.
        """
        converted_sql = sql.replace("?", "%s")
        return converted_sql, params or []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on Redshift.
        
        Supports:
        - Parameterized queries with ? or %s placeholders
        - Large result sets
        - Columnar query optimization
        """
        if not self._connected or not self._connection:
            raise QueryError(
                "Not connected to Redshift",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        rs_sql, rs_params = self.convert_placeholders(sql, params)
        
        cursor = None
        
        try:
            cursor = self._connection.cursor()
            
            # Execute query
            if rs_params:
                cursor.execute(rs_sql, rs_params)
            else:
                cursor.execute(rs_sql)
            
            # Fetch results
            columns = []
            column_types = {}
            if cursor.description:
                for desc in cursor.description:
                    col_name = desc[0]
                    col_type = desc[1] if len(desc) > 1 else None
                    columns.append(col_name)
                    column_types[col_name] = str(col_type) if col_type else "unknown"
            
            # Fetch all rows
            rows_raw = cursor.fetchall() if cursor.description else []
            
            # Convert to list of dicts
            rows = [dict(zip(columns, row)) for row in rows_raw]
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Build metadata
            metadata = {
                "host": self.host,
                "database": self.database,
                "row_count": len(rows)
            }
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=rs_sql,
                metadata=metadata
            )
            
        except Exception as e:
            # Rollback on error
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
            raise QueryError(
                f"Redshift query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                cursor.close()
    
    def health_check(self) -> bool:
        """Check Redshift connection health."""
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
    
    def get_schemas(self) -> List[str]:
        """List schemas in the database."""
        result = self.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_internal')
            ORDER BY schema_name
        """)
        return [row.get("schema_name", "") for row in result.rows]
    
    def get_tables(self, schema: str = "public") -> List[str]:
        """List tables in a schema."""
        result = self.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """, [schema])
        return [row.get("table_name", "") for row in result.rows]
    
    def get_table_schema(self, table: str, schema: str = "public") -> List[Dict]:
        """Get schema for a table."""
        result = self.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, [schema, table])
        
        return [
            {
                "name": row.get("column_name", ""),
                "type": row.get("data_type", ""),
                "nullable": row.get("is_nullable", "") == "YES",
                "default": row.get("column_default", "")
            }
            for row in result.rows
        ]
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get Redshift cluster information."""
        result = self.execute("""
            SELECT 
                current_database() as database,
                current_user as user,
                version() as version
        """)
        
        if result.rows:
            return result.rows[0]
        return {}
    
    def get_running_queries(self) -> List[Dict]:
        """Get currently running queries (requires appropriate permissions)."""
        result = self.execute("""
            SELECT 
                pid,
                user_name,
                query,
                starttime,
                DATEDIFF(second, starttime, GETDATE()) as elapsed_seconds
            FROM stv_recents
            WHERE status = 'Running'
            ORDER BY starttime
        """)
        return result.rows
    
    def cancel_query(self, pid: int) -> bool:
        """
        Cancel a running query.
        
        Requires superuser or query owner permissions.
        """
        try:
            self.execute(f"CANCEL {pid}")
            return True
        except Exception as e:
            logger.warning(f"Could not cancel query {pid}: {e}")
            return False

