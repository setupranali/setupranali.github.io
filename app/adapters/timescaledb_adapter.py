"""
TimescaleDB Adapter for SetuPranali

TimescaleDB is ideal for:
- Time-series data and IoT analytics
- Real-time monitoring and observability
- Financial tick data and metrics
- Sensor data and telemetry
- Log analytics and events

Features:
- Full PostgreSQL compatibility
- Hypertables for automatic partitioning
- Continuous aggregates for fast queries
- Compression for storage efficiency
- Time-based functions and analytics

Requirements:
    pip install psycopg2-binary
    # or for async:
    pip install asyncpg
"""

import logging
from typing import Any, Dict, List, Optional

from app.adapters.postgres_adapter import PostgresAdapter
from app.adapters.base import AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class TimescaleDBAdapter(PostgresAdapter):
    """
    Adapter for TimescaleDB (PostgreSQL extension for time-series).
    
    Inherits all PostgreSQL functionality and adds TimescaleDB-specific features.
    
    Config options (inherited from PostgreSQL):
        host: Server hostname or IP (required)
        port: Server port (default: 5432)
        database: Database name (required)
        user: Username (required)
        password: Password (required)
        schema: Default schema (default: public)
        sslmode: SSL mode (default: prefer)
        connect_timeout: Connection timeout (default: 30)
        application_name: Application identifier
        options: Additional connection options
        
    TimescaleDB-specific options:
        chunk_time_interval: Default chunk interval for new hypertables
        compression_enabled: Enable query on compressed chunks (default: True)
        
    Example (Basic):
        adapter = TimescaleDBAdapter({
            "host": "timescale.company.com",
            "database": "metrics",
            "user": "analytics",
            "password": "secret"
        })
        
    Example (Cloud):
        adapter = TimescaleDBAdapter({
            "host": "xxx.tsdb.cloud.timescale.com",
            "port": 5432,
            "database": "tsdb",
            "user": "tsdbadmin",
            "password": "secret",
            "sslmode": "require"
        })
    """
    
    ENGINE = "timescaledb"
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize TimescaleDB adapter."""
        super().__init__(config)
        
        # TimescaleDB-specific settings
        self.chunk_time_interval = config.get("chunk_time_interval", "7 days")
        self.compression_enabled = config.get("compression_enabled", True)
    
    def connect(self) -> None:
        """Connect to TimescaleDB."""
        # Use parent PostgreSQL connection
        super().connect()
        
        # Verify TimescaleDB extension is installed
        try:
            result = self.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
            )
            if not result.rows:
                logger.warning("TimescaleDB extension not found - using as regular PostgreSQL")
            else:
                version = result.rows[0].get("extversion", "unknown")
                logger.info(f"TimescaleDB version: {version}")
        except Exception as e:
            logger.warning(f"Could not verify TimescaleDB extension: {e}")
    
    def get_timescaledb_version(self) -> str:
        """Get TimescaleDB extension version."""
        if not self._connected:
            return ""
        
        result = self.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
        )
        if result.rows:
            return result.rows[0].get("extversion", "")
        return ""
    
    def get_hypertables(self, schema: str = None) -> List[Dict[str, Any]]:
        """Get list of hypertables."""
        if not self._connected:
            return []
        
        sql = """
            SELECT 
                hypertable_schema,
                hypertable_name,
                num_dimensions,
                num_chunks,
                compression_enabled,
                tablespaces
            FROM timescaledb_information.hypertables
        """
        
        if schema:
            sql += " WHERE hypertable_schema = %s"
            result = self.execute(sql, [schema])
        else:
            result = self.execute(sql)
        
        return result.rows
    
    def get_chunks(self, hypertable: str, schema: str = "public") -> List[Dict[str, Any]]:
        """Get chunks for a hypertable."""
        if not self._connected:
            return []
        
        result = self.execute("""
            SELECT 
                chunk_schema,
                chunk_name,
                range_start,
                range_end,
                is_compressed
            FROM timescaledb_information.chunks
            WHERE hypertable_schema = %s AND hypertable_name = %s
            ORDER BY range_start DESC
        """, [schema, hypertable])
        
        return result.rows
    
    def get_continuous_aggregates(self, schema: str = None) -> List[Dict[str, Any]]:
        """Get list of continuous aggregates."""
        if not self._connected:
            return []
        
        sql = """
            SELECT 
                view_schema,
                view_name,
                view_owner,
                materialization_hypertable_schema,
                materialization_hypertable_name,
                view_definition
            FROM timescaledb_information.continuous_aggregates
        """
        
        if schema:
            sql += " WHERE view_schema = %s"
            result = self.execute(sql, [schema])
        else:
            result = self.execute(sql)
        
        return result.rows
    
    def get_compression_stats(self, hypertable: str, schema: str = "public") -> Dict[str, Any]:
        """Get compression statistics for a hypertable."""
        if not self._connected:
            return {}
        
        result = self.execute("""
            SELECT 
                total_chunks,
                number_compressed_chunks,
                before_compression_total_bytes,
                after_compression_total_bytes,
                CASE 
                    WHEN before_compression_total_bytes > 0 
                    THEN ROUND((1 - after_compression_total_bytes::numeric / before_compression_total_bytes) * 100, 2)
                    ELSE 0 
                END as compression_ratio_pct
            FROM hypertable_compression_stats(%s)
        """, [f"{schema}.{hypertable}"])
        
        return result.rows[0] if result.rows else {}
    
    def get_data_retention_policies(self) -> List[Dict[str, Any]]:
        """Get data retention policies."""
        if not self._connected:
            return []
        
        result = self.execute("""
            SELECT 
                hypertable_schema,
                hypertable_name,
                schedule_interval,
                config
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_retention'
        """)
        
        return result.rows
    
    def get_time_bucket_gapfill_example(self) -> str:
        """Return example query using time_bucket_gapfill."""
        return """
        -- Example: Fill gaps in time-series data
        SELECT 
            time_bucket_gapfill('1 hour', time) AS bucket,
            locf(avg(value)) AS value  -- Last observation carried forward
        FROM metrics
        WHERE time > NOW() - INTERVAL '1 day'
        GROUP BY bucket
        ORDER BY bucket;
        """
    
    def health_check(self) -> bool:
        """Check TimescaleDB connection health."""
        if not super().health_check():
            return False
        
        # Also verify TimescaleDB is working
        try:
            result = self.execute("SELECT timescaledb_pre_restore()")
            self.execute("SELECT timescaledb_post_restore()")
            return True
        except Exception:
            # TimescaleDB functions not available, but PostgreSQL works
            return True


# Aliases
TSDBAdapter = TimescaleDBAdapter
TimeScaleAdapter = TimescaleDBAdapter

