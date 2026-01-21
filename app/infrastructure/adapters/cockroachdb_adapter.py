"""
CockroachDB Adapter for SetuPranali

CockroachDB is ideal for:
- Globally distributed databases
- Multi-region deployments
- High availability requirements
- Cloud-native applications
- Horizontal scaling

Features:
- PostgreSQL wire protocol compatibility
- Distributed SQL across regions
- Serializable isolation
- Automatic sharding
- Geo-partitioning

Requirements:
    pip install psycopg2-binary
    # or for async:
    pip install asyncpg
"""

import logging
from typing import Any, Dict, List, Optional

from app.adapters.postgres_adapter import PostgresAdapter
from app.infrastructure.adapters.base import AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class CockroachDBAdapter(PostgresAdapter):
    """
    Adapter for CockroachDB (distributed SQL database).
    
    Inherits PostgreSQL functionality with CockroachDB-specific features.
    
    Config options (inherited from PostgreSQL):
        host: Server hostname or IP (required)
        port: Server port (default: 26257 for CockroachDB)
        database: Database name (required)
        user: Username (required)
        password: Password (required)
        sslmode: SSL mode (default: verify-full for cloud)
        sslrootcert: Path to CA certificate
        cluster: CockroachDB Cloud cluster name
        options: Additional connection options
        
    CockroachDB-specific options:
        cluster: Cluster identifier (for CockroachDB Cloud)
        
    Example (Self-hosted):
        adapter = CockroachDBAdapter({
            "host": "cockroach.company.com",
            "port": 26257,
            "database": "defaultdb",
            "user": "root",
            "password": "secret",
            "sslmode": "verify-full",
            "sslrootcert": "/path/to/ca.crt"
        })
        
    Example (CockroachDB Cloud):
        adapter = CockroachDBAdapter({
            "host": "free-tier.gcp-us-central1.cockroachlabs.cloud",
            "port": 26257,
            "database": "defaultdb",
            "user": "username",
            "password": "password",
            "cluster": "cluster-name-123",
            "sslmode": "verify-full"
        })
    """
    
    ENGINE = "cockroachdb"
    DEFAULT_PORT = 26257  # CockroachDB default port
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize CockroachDB adapter."""
        # Set CockroachDB-specific defaults
        if "port" not in config:
            config["port"] = self.DEFAULT_PORT
        
        # CockroachDB Cloud requires SSL
        if "sslmode" not in config:
            host = config.get("host", "")
            if "cockroachlabs.cloud" in host:
                config["sslmode"] = "verify-full"
        
        # Handle cluster option for CockroachDB Cloud
        self.cluster = config.pop("cluster", None)
        if self.cluster:
            # Add cluster to connection options
            options = config.get("options", "")
            cluster_option = f"--cluster={self.cluster}"
            if options:
                config["options"] = f"{options} {cluster_option}"
            else:
                config["options"] = cluster_option
        
        super().__init__(config)
    
    def connect(self) -> None:
        """Connect to CockroachDB."""
        # Use parent PostgreSQL connection
        super().connect()
        
        # Verify CockroachDB and get version
        try:
            result = self.execute("SELECT version()")
            if result.rows:
                version = result.rows[0].get("version", "")
                if "CockroachDB" in version:
                    logger.info(f"CockroachDB connected: {version.split()[2] if len(version.split()) > 2 else version}")
                else:
                    logger.warning("Connected but CockroachDB not detected in version string")
        except Exception as e:
            logger.warning(f"Could not verify CockroachDB version: {e}")
    
    def get_crdb_version(self) -> str:
        """Get CockroachDB version."""
        if not self._connected:
            return ""
        
        result = self.execute("SELECT version()")
        if result.rows:
            version = result.rows[0].get("version", "")
            # Parse "CockroachDB CCL v23.1.0 ..."
            parts = version.split()
            for i, part in enumerate(parts):
                if part.startswith("v"):
                    return part
        return ""
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get CockroachDB cluster information."""
        if not self._connected:
            return {}
        
        result = self.execute("""
            SELECT 
                node_id,
                address,
                locality,
                is_live,
                ranges,
                range_leaders
            FROM crdb_internal.gossip_nodes
        """)
        
        return {
            "nodes": result.rows,
            "node_count": len(result.rows)
        }
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of nodes in the cluster."""
        if not self._connected:
            return []
        
        result = self.execute("""
            SELECT 
                node_id,
                address,
                locality,
                is_live,
                ranges,
                replicas_leaders
            FROM crdb_internal.kv_node_status
        """)
        
        return result.rows
    
    def get_ranges(self, table: str = None) -> List[Dict[str, Any]]:
        """Get range distribution information."""
        if not self._connected:
            return []
        
        if table:
            result = self.execute("""
                SELECT 
                    range_id,
                    start_key,
                    end_key,
                    lease_holder,
                    replicas
                FROM crdb_internal.ranges
                WHERE table_name = %s
                ORDER BY start_key
            """, [table])
        else:
            result = self.execute("""
                SELECT 
                    range_id,
                    database_name,
                    table_name,
                    start_key,
                    end_key,
                    lease_holder,
                    replicas
                FROM crdb_internal.ranges
                LIMIT 100
            """)
        
        return result.rows
    
    def get_regions(self) -> List[str]:
        """Get configured regions."""
        if not self._connected:
            return []
        
        result = self.execute("SHOW REGIONS")
        return [row.get("region", "") for row in result.rows]
    
    def get_zone_configs(self) -> List[Dict[str, Any]]:
        """Get zone configuration for data placement."""
        if not self._connected:
            return []
        
        result = self.execute("SHOW ZONE CONFIGURATIONS")
        return result.rows
    
    def get_running_queries(self) -> List[Dict[str, Any]]:
        """Get currently running queries."""
        if not self._connected:
            return []
        
        result = self.execute("""
            SELECT 
                query_id,
                node_id,
                user_name,
                start,
                query,
                phase
            FROM crdb_internal.cluster_queries
            ORDER BY start DESC
            LIMIT 50
        """)
        
        return result.rows
    
    def get_table_statistics(self, table: str, schema: str = "public") -> Dict[str, Any]:
        """Get table statistics."""
        if not self._connected:
            return {}
        
        result = self.execute("""
            SELECT 
                table_name,
                approximate_row_count,
                range_count,
                live_bytes,
                total_bytes
            FROM crdb_internal.table_row_statistics
            WHERE table_name = %s
        """, [table])
        
        return result.rows[0] if result.rows else {}
    
    def get_jobs(self, status: str = None) -> List[Dict[str, Any]]:
        """Get CockroachDB jobs (backups, imports, etc.)."""
        if not self._connected:
            return []
        
        sql = """
            SELECT 
                job_id,
                job_type,
                status,
                created,
                started,
                finished,
                description
            FROM crdb_internal.jobs
        """
        
        if status:
            sql += " WHERE status = %s"
            result = self.execute(sql + " ORDER BY created DESC LIMIT 50", [status])
        else:
            result = self.execute(sql + " ORDER BY created DESC LIMIT 50")
        
        return result.rows
    
    def explain_analyze(self, sql: str) -> Dict[str, Any]:
        """Run EXPLAIN ANALYZE on a query."""
        if not self._connected:
            return {}
        
        result = self.execute(f"EXPLAIN ANALYZE {sql}")
        return {
            "plan": [row for row in result.rows]
        }
    
    def health_check(self) -> bool:
        """Check CockroachDB connection health."""
        if not super().health_check():
            return False
        
        # Verify cluster is healthy
        try:
            result = self.execute("SELECT 1")
            return bool(result.rows)
        except Exception:
            return False


# Aliases
CRDBAdapter = CockroachDBAdapter
RoachAdapter = CockroachDBAdapter

