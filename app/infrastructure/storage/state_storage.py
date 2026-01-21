"""
DuckDB State Storage Module for SetuPranali

Centralized state storage using DuckDB for all application state:
- Query analytics and observability data
- API keys and authentication state
- System metrics and statistics
- Cache metadata

Benefits of DuckDB for state storage:
- Fast analytical queries on time-series data
- Efficient columnar storage for analytics
- SQL interface for complex queries
- File-based persistence
- No external dependencies (embedded)
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None

logger = logging.getLogger(__name__)


# =============================================================================
# STATE STORAGE MANAGER
# =============================================================================

class StateStorage:
    """
    Centralized state storage using DuckDB.
    
    All application state is stored in a single DuckDB database file.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize state storage.
        
        Args:
            db_path: Path to DuckDB database file. Defaults to app/db/state.db
        """
        if not DUCKDB_AVAILABLE:
            raise RuntimeError("DuckDB not available. Install with: pip install duckdb")
        
        if db_path is None:
            # Database files are now in data/db/ (outside app/)
            db_dir = Path(__file__).parent.parent.parent.parent / "data" / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "state.db")
        
        self.db_path = db_path
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._init_database()
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection."""
        if self._connection is None:
            self._connection = duckdb.connect(self.db_path)
        return self._connection
    
    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        
        # Query Analytics Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_records (
                query_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                dataset TEXT NOT NULL,
                tenant_id TEXT,
                dimensions TEXT,  -- JSON array
                metrics TEXT,    -- JSON array
                filters TEXT,    -- JSON object
                duration_ms DOUBLE NOT NULL,
                rows_returned INTEGER NOT NULL,
                bytes_scanned INTEGER DEFAULT 0,
                cache_hit BOOLEAN DEFAULT FALSE,
                success BOOLEAN DEFAULT TRUE,
                error_code TEXT,
                error_message TEXT,
                api_key_hash TEXT,
                user_id TEXT,
                source_ip TEXT,
                user_agent TEXT
            )
        """)
        
        # Create indexes for common queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_records_timestamp 
            ON query_records(timestamp)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_records_dataset 
            ON query_records(dataset)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_records_tenant 
            ON query_records(tenant_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_records_success 
            ON query_records(success)
        """)
        
        # API Keys Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL UNIQUE,
                tenant TEXT NOT NULL,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL,
                last_used_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_status 
            ON api_keys(status)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_tenant 
            ON api_keys(tenant)
        """)
        
        # Aggregated Stats Table (for fast lookups)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS aggregated_stats (
                stat_key TEXT PRIMARY KEY,
                stat_type TEXT NOT NULL,  -- 'total', 'by_dataset', 'by_hour', 'by_tenant'
                stat_data TEXT NOT NULL,  -- JSON object
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # System Metrics Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                metric_id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                metric_value DOUBLE NOT NULL,
                metric_labels TEXT,  -- JSON object
                timestamp TIMESTAMP NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_metrics_name 
            ON system_metrics(metric_name, timestamp)
        """)
        
        logger.info(f"State storage initialized: {self.db_path}")
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    # =========================================================================
    # QUERY ANALYTICS
    # =========================================================================
    
    def record_query(self, record: Dict[str, Any]) -> None:
        """
        Record a query execution.
        
        Args:
            record: QueryRecord as dictionary
        """
        conn = self._get_connection()
        
        # Convert lists/dicts to JSON strings
        dimensions_json = json.dumps(record.get("dimensions", []))
        metrics_json = json.dumps(record.get("metrics", []))
        filters_json = json.dumps(record.get("filters", {}) or {})
        
        conn.execute("""
            INSERT OR REPLACE INTO query_records (
                query_id, timestamp, dataset, tenant_id,
                dimensions, metrics, filters,
                duration_ms, rows_returned, bytes_scanned,
                cache_hit, success, error_code, error_message,
                api_key_hash, user_id, source_ip, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record.get("query_id"),
            record.get("timestamp"),
            record.get("dataset"),
            record.get("tenant_id"),
            dimensions_json,
            metrics_json,
            filters_json,
            record.get("duration_ms"),
            record.get("rows_returned"),
            record.get("bytes_scanned", 0),
            record.get("cache_hit", False),
            record.get("success", True),
            record.get("error_code"),
            record.get("error_message"),
            record.get("api_key_hash"),
            record.get("user_id"),
            record.get("source_ip"),
            record.get("user_agent"),
        ])
    
    def get_query_records(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        dataset: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get query records with filters."""
        conn = self._get_connection()
        
        conditions = []
        params = []
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
        if dataset:
            conditions.append("dataset = ?")
            params.append(dataset)
        
        if tenant_id:
            conditions.append("tenant_id = ?")
            params.append(tenant_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT * FROM query_records
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)
        
        result = conn.execute(query, params).fetchdf()
        
        # Convert to list of dicts and parse JSON fields
        records = []
        for _, row in result.iterrows():
            record = row.to_dict()
            # Parse JSON fields
            if record.get("dimensions"):
                record["dimensions"] = json.loads(record["dimensions"])
            if record.get("metrics"):
                record["metrics"] = json.loads(record["metrics"])
            if record.get("filters"):
                record["filters"] = json.loads(record["filters"])
            records.append(record)
        
        return records
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly statistics for the last N hours."""
        conn = self._get_connection()
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        result = conn.execute("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as count,
                SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as errors,
                AVG(duration_ms) as avg_duration_ms,
                SUM(duration_ms) as total_duration_ms
            FROM query_records
            WHERE timestamp >= ?
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour ASC
        """, [cutoff]).fetchdf()
        
        # Create a dict of hour -> stats for quick lookup
        hour_stats_map = {}
        for _, row in result.iterrows():
            hour_key = row["hour"].strftime("%Y-%m-%d-%H")
            hour_stats_map[hour_key] = {
                "hour": hour_key,
                "count": int(row["count"]),
                "errors": int(row["errors"]),
                "avg_duration_ms": float(row["avg_duration_ms"]) if row["avg_duration_ms"] else 0.0,
            }
        
        # Fill in missing hours with zeros
        stats = []
        now = datetime.now(timezone.utc)
        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            if hour_key in hour_stats_map:
                stats.append(hour_stats_map[hour_key])
            else:
                stats.append({
                    "hour": hour_key,
                    "count": 0,
                    "errors": 0,
                    "avg_duration_ms": 0.0,
                })
        
        # Return in chronological order (oldest first)
        return list(reversed(stats))
    
    def get_dataset_stats(self) -> List[Dict[str, Any]]:
        """Get per-dataset statistics."""
        conn = self._get_connection()
        
        result = conn.execute("""
            SELECT 
                dataset,
                COUNT(*) as count,
                SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as errors,
                AVG(duration_ms) as avg_duration_ms,
                SUM(duration_ms) as total_duration_ms
            FROM query_records
            GROUP BY dataset
            ORDER BY count DESC
        """).fetchdf()
        
        stats = []
        for _, row in result.iterrows():
            stats.append({
                "dataset": row["dataset"],
                "count": int(row["count"]),
                "errors": int(row["errors"]),
                "avg_duration_ms": float(row["avg_duration_ms"]) if row["avg_duration_ms"] else 0.0,
                "error_rate": float(row["errors"]) / int(row["count"]) if row["count"] > 0 else 0.0,
            })
        
        return stats
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall aggregated statistics."""
        conn = self._get_connection()
        
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_queries,
                SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as total_errors,
                AVG(duration_ms) as avg_duration_ms,
                SUM(duration_ms) as total_duration_ms,
                SUM(rows_returned) as total_rows,
                SUM(CASE WHEN cache_hit = TRUE THEN 1 ELSE 0 END) as cache_hits
            FROM query_records
        """).fetchone()
        
        total_queries = result[0] or 0
        total_errors = result[1] or 0
        
        return {
            "total_queries": total_queries,
            "total_errors": total_errors,
            "error_rate": total_errors / total_queries if total_queries > 0 else 0.0,
            "avg_duration_ms": float(result[2]) if result[2] else 0.0,
            "avg_rows": float(result[4]) / total_queries if total_queries > 0 else 0.0,
            "cache_hit_rate": float(result[5]) / total_queries if total_queries > 0 else 0.0,
        }
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries."""
        conn = self._get_connection()
        
        result = conn.execute("""
            SELECT 
                query_id,
                dataset,
                duration_ms,
                timestamp,
                success
            FROM query_records
            WHERE duration_ms > 1000
            ORDER BY duration_ms DESC
            LIMIT ?
        """, [limit]).fetchdf()
        
        queries = []
        for _, row in result.iterrows():
            queries.append({
                "query_id": row["query_id"],
                "dataset": row["dataset"],
                "duration_ms": float(row["duration_ms"]),
                "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
            })
        
        return queries
    
    def cleanup_old_records(self, retention_hours: int = 168):
        """Remove query records older than retention period."""
        conn = self._get_connection()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        
        result = conn.execute("""
            DELETE FROM query_records
            WHERE timestamp < ?
        """, [cutoff])
        
        deleted = result.rowcount if hasattr(result, 'rowcount') else 0
        logger.info(f"Cleaned up {deleted} old query records")
        return deleted
    
    # =========================================================================
    # API KEYS
    # =========================================================================
    
    def save_api_key(self, key_record: Dict[str, Any]) -> None:
        """Save or update an API key."""
        conn = self._get_connection()
        
        conn.execute("""
            INSERT OR REPLACE INTO api_keys (
                key_id, api_key, tenant, role, name,
                status, created_at, last_used_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            key_record.get("key_id"),
            key_record.get("api_key"),
            key_record.get("tenant"),
            key_record.get("role"),
            key_record.get("name"),
            key_record.get("status", "active"),
            key_record.get("created_at"),
            key_record.get("last_used_at"),
            key_record.get("expires_at"),
        ])
    
    def get_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get API key record by key."""
        conn = self._get_connection()
        
        result = conn.execute("""
            SELECT * FROM api_keys
            WHERE api_key = ? AND status = 'active'
        """, [api_key]).fetchdf()
        
        if result.empty:
            return None
        
        row = result.iloc[0]
        return row.to_dict()
    
    def get_api_key_by_id(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key record by key_id."""
        conn = self._get_connection()
        
        result = conn.execute("""
            SELECT * FROM api_keys
            WHERE key_id = ?
        """, [key_id]).fetchdf()
        
        if result.empty:
            return None
        
        row = result.iloc[0]
        return row.to_dict()
    
    def get_api_key_for_revocation(self, key_id: str) -> Optional[str]:
        """Get API key string by key_id (for revocation)."""
        record = self.get_api_key_by_id(key_id)
        if record:
            return record.get("api_key")
        return None
    
    def list_api_keys(self, tenant: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all API keys, optionally filtered by tenant."""
        conn = self._get_connection()
        
        if tenant:
            result = conn.execute("""
                SELECT key_id, tenant, role, name, status, created_at, last_used_at
                FROM api_keys
                WHERE tenant = ?
                ORDER BY created_at DESC
            """, [tenant]).fetchdf()
        else:
            result = conn.execute("""
                SELECT key_id, tenant, role, name, status, created_at, last_used_at
                FROM api_keys
                ORDER BY created_at DESC
            """).fetchdf()
        
        keys = []
        for _, row in result.iterrows():
            keys.append(row.to_dict())
        
        return keys
    
    def update_api_key_last_used(self, api_key: str) -> None:
        """Update last_used_at timestamp for an API key."""
        conn = self._get_connection()
        
        conn.execute("""
            UPDATE api_keys
            SET last_used_at = ?
            WHERE api_key = ?
        """, [datetime.now(timezone.utc), api_key])
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        conn = self._get_connection()
        
        result = conn.execute("""
            UPDATE api_keys
            SET status = 'revoked'
            WHERE api_key = ? AND status = 'active'
        """, [api_key])
        
        return result.rowcount > 0 if hasattr(result, 'rowcount') else False
    
    # =========================================================================
    # SYSTEM METRICS
    # =========================================================================
    
    def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a system metric."""
        conn = self._get_connection()
        
        metric_id = f"{metric_name}_{datetime.now(timezone.utc).isoformat()}"
        labels_json = json.dumps(labels or {})
        
        conn.execute("""
            INSERT INTO system_metrics (
                metric_id, metric_name, metric_value, metric_labels, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        """, [
            metric_id,
            metric_name,
            metric_value,
            labels_json,
            datetime.now(timezone.utc)
        ])
    
    def get_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get system metrics with optional filters."""
        conn = self._get_connection()
        
        conditions = []
        params = []
        
        if metric_name:
            conditions.append("metric_name = ?")
            params.append(metric_name)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT * FROM system_metrics
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)
        
        result = conn.execute(query, params).fetchdf()
        
        metrics = []
        for _, row in result.iterrows():
            metric = row.to_dict()
            if metric.get("metric_labels"):
                metric["metric_labels"] = json.loads(metric["metric_labels"])
            metrics.append(metric)
        
        return metrics


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_state_storage: Optional[StateStorage] = None


def get_state_storage() -> StateStorage:
    """Get global state storage instance."""
    global _state_storage
    
    if _state_storage is None:
        _state_storage = StateStorage()
    
    return _state_storage


def init_state_storage(db_path: Optional[str] = None) -> StateStorage:
    """Initialize state storage (called on startup)."""
    global _state_storage
    
    _state_storage = StateStorage(db_path)
    logger.info("State storage initialized with DuckDB")
    
    return _state_storage
