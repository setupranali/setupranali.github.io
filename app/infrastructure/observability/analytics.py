"""
Observability Module for SetuPranali

Provides comprehensive monitoring and observability:
- Query Analytics: Track query patterns and performance
- Prometheus Metrics: Export metrics for monitoring
- OpenTelemetry: Distributed tracing support
- Audit Logs: Full audit trail of all queries

Features:
- Real-time metrics collection
- Query performance tracking
- Error rate monitoring
- Request tracing
- Structured audit logging
- Dashboard-ready analytics
"""

import os
import time
import json
import logging
import hashlib
import threading
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from functools import wraps
from contextlib import contextmanager

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class ObservabilityConfig(BaseModel):
    """Observability configuration."""
    
    # Query Analytics
    analytics_enabled: bool = Field(default=True)
    analytics_retention_hours: int = Field(default=168)  # 7 days
    analytics_sample_rate: float = Field(default=1.0)  # 100%
    
    # Prometheus Metrics
    metrics_enabled: bool = Field(default=True)
    metrics_prefix: str = Field(default="setupranali")
    metrics_default_labels: Dict[str, str] = Field(default={})
    
    # OpenTelemetry
    tracing_enabled: bool = Field(default=True)
    tracing_sample_rate: float = Field(default=1.0)
    tracing_exporter: str = Field(default="otlp")  # otlp, jaeger, zipkin
    tracing_endpoint: Optional[str] = Field(default=None)
    tracing_service_name: str = Field(default="setupranali")
    
    # Audit Logs
    audit_enabled: bool = Field(default=True)
    audit_log_file: Optional[str] = Field(default=None)
    audit_include_query_text: bool = Field(default=True)
    audit_include_results: bool = Field(default=False)
    audit_sensitive_fields: List[str] = Field(default=["password", "secret", "token", "key"])


# =============================================================================
# Query Analytics
# =============================================================================

@dataclass
class QueryRecord:
    """Record of a query execution."""
    
    query_id: str
    timestamp: datetime
    dataset: str
    dimensions: List[str]
    metrics: List[str]
    filters: Optional[Dict[str, Any]]
    
    # Performance
    duration_ms: float
    rows_returned: int
    bytes_scanned: int = 0
    cache_hit: bool = False
    
    # Context
    api_key_hash: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Status
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class QueryAnalytics:
    """Query analytics collector and analyzer."""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self._lock = threading.Lock()
        
        # Use DuckDB state storage instead of in-memory
        try:
            from app.infrastructure.storage.state_storage import get_state_storage
            self._storage = get_state_storage()
            self._use_storage = True
        except Exception as e:
            logger.warning(f"Failed to initialize state storage, falling back to in-memory: {e}")
            self._storage = None
            self._use_storage = False
            # Fallback to in-memory for backward compatibility
            self._records: List[QueryRecord] = []
            self._stats = {
                "total_queries": 0,
                "total_errors": 0,
                "total_duration_ms": 0,
                "total_rows": 0,
                "cache_hits": 0,
                "by_dataset": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                "by_hour": defaultdict(lambda: {"count": 0, "duration_ms": 0}),
                "by_tenant": defaultdict(lambda: {"count": 0, "duration_ms": 0}),
                "slow_queries": [],
                "popular_dimensions": defaultdict(int),
                "popular_metrics": defaultdict(int),
            }
    
    def record_query(self, record: QueryRecord) -> None:
        """Record a query execution."""
        if not self.config.analytics_enabled:
            logger.debug("Analytics disabled, skipping query record")
            return
        
        # Apply sampling
        if self.config.analytics_sample_rate < 1.0:
            import random
            if random.random() > self.config.analytics_sample_rate:
                logger.debug(f"Query skipped due to sampling (rate={self.config.analytics_sample_rate})")
                return
        
        if self._use_storage and self._storage:
            # Store in DuckDB
            try:
                record_dict = {
                    "query_id": record.query_id,
                    "timestamp": record.timestamp,
                    "dataset": record.dataset,
                    "tenant_id": record.tenant_id,
                    "dimensions": record.dimensions,
                    "metrics": record.metrics,
                    "filters": record.filters,
                    "duration_ms": record.duration_ms,
                    "rows_returned": record.rows_returned,
                    "bytes_scanned": record.bytes_scanned,
                    "cache_hit": record.cache_hit,
                    "success": record.success,
                    "error_code": record.error_code,
                    "error_message": record.error_message,
                    "api_key_hash": record.api_key_hash,
                    "user_id": record.user_id,
                    "source_ip": record.source_ip,
                    "user_agent": record.user_agent,
                }
                self._storage.record_query(record_dict)
                logger.debug(f"Query recorded in DuckDB: {record.query_id}, dataset={record.dataset}")
                
                # Also update in-memory stats as backup (for get_hourly_stats fallback)
                with self._lock:
                    if not hasattr(self, '_stats'):
                        from collections import defaultdict
                        self._stats = {
                            "total_queries": 0,
                            "total_errors": 0,
                            "total_duration_ms": 0,
                            "total_rows": 0,
                            "cache_hits": 0,
                            "by_dataset": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                            "by_hour": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                            "by_tenant": defaultdict(lambda: {"count": 0, "duration_ms": 0}),
                            "slow_queries": [],
                            "popular_dimensions": defaultdict(int),
                            "popular_metrics": defaultdict(int),
                        }
                    if not hasattr(self, '_records'):
                        self._records = []
                    self._records.append(record)
                    self._update_stats(record)
                
                # Periodic cleanup
                if hasattr(self, '_last_cleanup'):
                    if (datetime.now() - self._last_cleanup).total_seconds() > 3600:  # Every hour
                        self._storage.cleanup_old_records(self.config.analytics_retention_hours)
                        self._last_cleanup = datetime.now()
                else:
                    self._last_cleanup = datetime.now()
            except Exception as e:
                logger.error(f"Failed to store query in DuckDB, using fallback: {e}", exc_info=True)
                # Fallback to in-memory
                with self._lock:
                    if not hasattr(self, '_records'):
                        self._records = []
                    if not hasattr(self, '_stats'):
                        from collections import defaultdict
                        self._stats = {
                            "total_queries": 0,
                            "total_errors": 0,
                            "total_duration_ms": 0,
                            "total_rows": 0,
                            "cache_hits": 0,
                            "by_dataset": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                            "by_hour": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                            "by_tenant": defaultdict(lambda: {"count": 0, "duration_ms": 0}),
                            "slow_queries": [],
                            "popular_dimensions": defaultdict(int),
                            "popular_metrics": defaultdict(int),
                        }
                    self._records.append(record)
                    self._update_stats(record)
        else:
            # Fallback to in-memory
            logger.debug(f"Using in-memory storage (use_storage={self._use_storage}, storage={self._storage})")
            with self._lock:
                if not hasattr(self, '_records'):
                    self._records = []
                if not hasattr(self, '_stats'):
                    from collections import defaultdict
                    self._stats = {
                        "total_queries": 0,
                        "total_errors": 0,
                        "total_duration_ms": 0,
                        "total_rows": 0,
                        "cache_hits": 0,
                        "by_dataset": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                        "by_hour": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                        "by_tenant": defaultdict(lambda: {"count": 0, "duration_ms": 0}),
                        "slow_queries": [],
                        "popular_dimensions": defaultdict(int),
                        "popular_metrics": defaultdict(int),
                    }
                self._records.append(record)
                self._update_stats(record)
                self._cleanup_old_records()
    
    def _update_stats(self, record: QueryRecord) -> None:
        """Update aggregated statistics."""
        # Ensure _stats is initialized
        if not hasattr(self, '_stats') or not self._stats:
            self._stats = {
                "total_queries": 0,
                "total_duration_ms": 0,
                "total_rows": 0,
                "total_errors": 0,
                "cache_hits": 0,
                "by_dataset": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                "by_hour": defaultdict(lambda: {"count": 0, "duration_ms": 0, "errors": 0}),
                "by_tenant": defaultdict(lambda: {"count": 0, "duration_ms": 0}),
                "slow_queries": [],
                "popular_dimensions": defaultdict(int),
                "popular_metrics": defaultdict(int),
            }
        self._stats["total_queries"] += 1
        self._stats["total_duration_ms"] += record.duration_ms
        self._stats["total_rows"] += record.rows_returned
        
        if not record.success:
            self._stats["total_errors"] += 1
        
        if record.cache_hit:
            self._stats["cache_hits"] += 1
        
        # By dataset
        ds_stats = self._stats["by_dataset"][record.dataset]
        ds_stats["count"] += 1
        ds_stats["duration_ms"] += record.duration_ms
        if not record.success:
            ds_stats["errors"] += 1
        
        # By hour - ensure timestamp is timezone-aware
        ts = record.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        hour_key = ts.strftime("%Y-%m-%d-%H")
        hour_stats = self._stats["by_hour"][hour_key]
        hour_stats["count"] += 1
        hour_stats["duration_ms"] += record.duration_ms
        if not record.success:
            hour_stats["errors"] = hour_stats.get("errors", 0) + 1
        
        # By tenant
        if record.tenant_id:
            tenant_stats = self._stats["by_tenant"][record.tenant_id]
            tenant_stats["count"] += 1
            tenant_stats["duration_ms"] += record.duration_ms
        
        # Popular dimensions/metrics
        for dim in record.dimensions:
            self._stats["popular_dimensions"][dim] += 1
        for met in record.metrics:
            self._stats["popular_metrics"][met] += 1
        
        # Slow queries (keep top 10)
        if record.duration_ms > 1000:  # > 1 second
            self._stats["slow_queries"].append({
                "query_id": record.query_id,
                "dataset": record.dataset,
                "duration_ms": record.duration_ms,
                "timestamp": record.timestamp.isoformat(),
            })
            self._stats["slow_queries"] = sorted(
                self._stats["slow_queries"],
                key=lambda x: x["duration_ms"],
                reverse=True
            )[:10]
    
    def _cleanup_old_records(self) -> None:
        """Remove records older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.config.analytics_retention_hours)
        # Ensure both timestamps are timezone-aware for comparison
        filtered = []
        for r in self._records:
            # Make timestamp timezone-aware if it's not
            ts = r.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts > cutoff:
                filtered.append(r)
        self._records = filtered
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        if self._use_storage and self._storage:
            # Get from DuckDB
            try:
                overall_stats = self._storage.get_overall_stats()
                dataset_stats = self._storage.get_dataset_stats()
                slow_queries = self._storage.get_slow_queries(limit=10)
                
                # Get popular dimensions/metrics from recent queries
                recent_records = self._storage.get_query_records(limit=1000)
                popular_dimensions = defaultdict(int)
                popular_metrics = defaultdict(int)
                
                for record in recent_records:
                    for dim in record.get("dimensions", []):
                        popular_dimensions[dim] += 1
                    for met in record.get("metrics", []):
                        popular_metrics[met] += 1
                
                return {
                    **overall_stats,
                    "by_dataset": {ds["dataset"]: {
                        "count": ds["count"],
                        "duration_ms": ds["avg_duration_ms"] * ds["count"],
                        "errors": ds["errors"]
                    } for ds in dataset_stats},
                    "slow_queries": slow_queries,
                    "popular_dimensions": dict(sorted(
                        popular_dimensions.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:20]),
                    "popular_metrics": dict(sorted(
                        popular_metrics.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:20]),
                }
            except Exception as e:
                logger.warning(f"Failed to get stats from DuckDB: {e}")
                # Fallback to in-memory
                pass
        
        # Fallback to in-memory stats
        with self._lock:
            if not hasattr(self, '_stats'):
                return {
                    "total_queries": 0,
                    "total_errors": 0,
                    "error_rate": 0,
                    "avg_duration_ms": 0,
                    "avg_rows": 0,
                    "cache_hit_rate": 0,
                    "by_dataset": {},
                    "slow_queries": [],
                    "popular_dimensions": {},
                    "popular_metrics": {},
                }
            
            total = self._stats["total_queries"]
            return {
                "total_queries": total,
                "total_errors": self._stats["total_errors"],
                "error_rate": self._stats["total_errors"] / total if total > 0 else 0,
                "avg_duration_ms": self._stats["total_duration_ms"] / total if total > 0 else 0,
                "avg_rows": self._stats["total_rows"] / total if total > 0 else 0,
                "cache_hit_rate": self._stats["cache_hits"] / total if total > 0 else 0,
                "by_dataset": dict(self._stats["by_dataset"]),
                "slow_queries": self._stats["slow_queries"],
                "popular_dimensions": dict(sorted(
                    self._stats["popular_dimensions"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]),
                "popular_metrics": dict(sorted(
                    self._stats["popular_metrics"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]),
            }
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly statistics for the last N hours."""
        if self._use_storage and self._storage:
            # Get from DuckDB
            try:
                duckdb_stats = self._storage.get_hourly_stats(hours=hours)
                # Merge with in-memory stats to ensure we have the latest data
                # (DuckDB might not have committed recent queries yet)
                with self._lock:
                    # Build DuckDB map
                    duckdb_map = {}
                    for stat in duckdb_stats:
                        hour_key = stat["hour"]
                        duckdb_map[hour_key] = stat
                    
                    # Get in-memory stats (always check, even if empty)
                    in_memory_map = {}
                    if hasattr(self, '_stats') and self._stats:
                        now = datetime.now(timezone.utc)
                        for i in range(hours):
                            hour = now - timedelta(hours=i)
                            hour_key = hour.strftime("%Y-%m-%d-%H")
                            stats = self._stats["by_hour"].get(hour_key, {"count": 0, "duration_ms": 0, "errors": 0})
                            if stats["count"] > 0:
                                in_memory_map[hour_key] = {
                                    "hour": hour_key,
                                    "count": stats["count"],
                                    "errors": stats.get("errors", 0),
                                    "avg_duration_ms": stats["duration_ms"] / stats["count"] if stats["count"] > 0 else 0,
                                }
                    
                    # Merge: always prefer in-memory data (it's more recent)
                    merged_map = {}
                    # Start with DuckDB data
                    for hour_key, stat in duckdb_map.items():
                        merged_map[hour_key] = stat
                    
                    # Override with in-memory data (always more recent)
                    for hour_key, stat in in_memory_map.items():
                        merged_map[hour_key] = stat
                    
                    # Build result for ALL hours, ensuring chronological order
                    result = []
                    now = datetime.now(timezone.utc)
                    for i in range(hours):
                        hour = now - timedelta(hours=i)
                        hour_key = hour.strftime("%Y-%m-%d-%H")
                        if hour_key in merged_map:
                            result.append(merged_map[hour_key])
                        else:
                            result.append({
                                "hour": hour_key,
                                "count": 0,
                                "errors": 0,
                                "avg_duration_ms": 0,
                            })
                    # Return in chronological order (oldest first)
                    return list(reversed(result))
                
            except Exception as e:
                logger.warning(f"Failed to get hourly stats from DuckDB: {e}")
                # Fallback to in-memory
                pass
            except Exception as e:
                logger.warning(f"Failed to get hourly stats from DuckDB: {e}")
                # Fallback to in-memory
                pass
        
        # Fallback to in-memory stats
        with self._lock:
            if not hasattr(self, '_stats'):
                # Return empty stats for all hours
                result = []
                now = datetime.now(timezone.utc)
                for i in range(hours):
                    hour = now - timedelta(hours=i)
                    hour_key = hour.strftime("%Y-%m-%d-%H")
                    result.append({
                        "hour": hour_key,
                        "count": 0,
                        "errors": 0,
                        "avg_duration_ms": 0,
                    })
                return list(reversed(result))
            
            result = []
            # Use UTC timezone for consistency with recording
            now = datetime.now(timezone.utc)
            for i in range(hours):
                hour = now - timedelta(hours=i)
                hour_key = hour.strftime("%Y-%m-%d-%H")
                stats = self._stats["by_hour"].get(hour_key, {"count": 0, "duration_ms": 0, "errors": 0})
                result.append({
                    "hour": hour_key,
                    "count": stats["count"],
                    "errors": stats.get("errors", 0),
                    "avg_duration_ms": stats["duration_ms"] / stats["count"] if stats["count"] > 0 else 0,
                })
            return list(reversed(result))
    
    def get_dataset_stats(self) -> List[Dict[str, Any]]:
        """Get per-dataset statistics."""
        if self._use_storage and self._storage:
            # Get from DuckDB
            try:
                return self._storage.get_dataset_stats()
            except Exception as e:
                logger.warning(f"Failed to get dataset stats from DuckDB: {e}")
                # Fallback to in-memory
                pass
        
        # Fallback to in-memory stats
        with self._lock:
            if not hasattr(self, '_stats'):
                return []
            
            result = []
            for dataset, stats in self._stats["by_dataset"].items():
                result.append({
                    "dataset": dataset,
                    "count": stats["count"],
                    "avg_duration_ms": stats["duration_ms"] / stats["count"] if stats["count"] > 0 else 0,
                    "error_rate": stats["errors"] / stats["count"] if stats["count"] > 0 else 0,
                })
            return sorted(result, key=lambda x: x["count"], reverse=True)
    
    def get_recent_queries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent query records formatted for dashboard."""
        if self._use_storage and self._storage:
            # Get from DuckDB
            try:
                records = self._storage.get_query_records(limit=limit)
                formatted = []
                for record in records:
                    # Parse JSON fields
                    dimensions = record.get("dimensions", [])
                    metrics = record.get("metrics", [])
                    if isinstance(dimensions, str):
                        import json
                        dimensions = json.loads(dimensions)
                    if isinstance(metrics, str):
                        import json
                        metrics = json.loads(metrics)
                    
                    formatted.append({
                        "dataset": record.get("dataset", "unknown"),
                        "metrics": metrics if isinstance(metrics, list) else [],
                        "dimensions": dimensions if isinstance(dimensions, list) else [],
                        "duration": f"{int(record.get('duration_ms', 0))}ms",
                        "status": "error" if not record.get("success", True) else ("warning" if record.get("duration_ms", 0) > 1000 else "success"),
                        "timestamp": record.get("timestamp"),
                    })
                return formatted
            except Exception as e:
                logger.warning(f"Failed to get recent queries from DuckDB: {e}")
                # Fallback to in-memory
                pass
        
        # Fallback to in-memory - get from all recent records, not just slow queries
        with self._lock:
            if not hasattr(self, '_records') or not self._records:
                logger.debug("No in-memory records found in get_recent_queries()")
                return []
            
            logger.debug(f"Found {len(self._records)} in-memory records, returning {limit} most recent")
            # Get the most recent records (sorted by timestamp, newest first)
            sorted_records = sorted(self._records, key=lambda r: r.timestamp, reverse=True)
            recent = []
            for record in sorted_records[:limit]:
                recent.append({
                    "dataset": record.dataset,
                    "metrics": record.metrics if isinstance(record.metrics, list) else [],
                    "dimensions": record.dimensions if isinstance(record.dimensions, list) else [],
                    "duration": f"{int(record.duration_ms)}ms",
                    "status": "error" if not record.success else ("warning" if record.duration_ms > 1000 else "success"),
                    "timestamp": record.timestamp.isoformat() if hasattr(record.timestamp, 'isoformat') else str(record.timestamp),
                })
            logger.debug(f"Returning {len(recent)} recent queries from in-memory storage")
            return recent


# =============================================================================
# Prometheus Metrics
# =============================================================================

class PrometheusMetrics:
    """Prometheus metrics exporter."""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.prefix = config.metrics_prefix
        self.default_labels = config.metrics_default_labels
        
        # Metrics storage
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        
        # Histogram buckets for latency
        self._latency_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    
    def _label_str(self, labels: Dict[str, str]) -> str:
        """Convert labels to string key."""
        all_labels = {**self.default_labels, **labels}
        if not all_labels:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in sorted(all_labels.items())) + "}"
    
    def inc_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter."""
        if not self.config.metrics_enabled:
            return
        labels = labels or {}
        key = f"{self.prefix}_{name}{self._label_str(labels)}"
        with self._lock:
            self._counters[key] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge value."""
        if not self.config.metrics_enabled:
            return
        labels = labels or {}
        key = f"{self.prefix}_{name}{self._label_str(labels)}"
        with self._lock:
            self._gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Observe a histogram value."""
        if not self.config.metrics_enabled:
            return
        labels = labels or {}
        key = f"{self.prefix}_{name}{self._label_str(labels)}"
        with self._lock:
            self._histograms[key].append(value)
            # Keep only last 10000 observations
            if len(self._histograms[key]) > 10000:
                self._histograms[key] = self._histograms[key][-10000:]
    
    def _histogram_buckets(self, values: List[float]) -> Dict[str, int]:
        """Calculate histogram bucket counts."""
        result = {}
        for bucket in self._latency_buckets:
            result[str(bucket)] = sum(1 for v in values if v <= bucket)
        result["+Inf"] = len(values)
        return result
    
    def export(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            # Counters
            for key, value in self._counters.items():
                lines.append(f"{key} {value}")
            
            # Gauges
            for key, value in self._gauges.items():
                lines.append(f"{key} {value}")
            
            # Histograms
            for key, values in self._histograms.items():
                if not values:
                    continue
                
                buckets = self._histogram_buckets(values)
                for bucket, count in buckets.items():
                    bucket_label = f'le="{bucket}"'
                    if "{" in key:
                        bucket_key = key.replace("}", f",{bucket_label}}}")
                    else:
                        bucket_key = f"{key}{{{bucket_label}}}"
                    lines.append(f"{bucket_key}_bucket {count}")
                
                lines.append(f"{key}_sum {sum(values)}")
                lines.append(f"{key}_count {len(values)}")
        
        return "\n".join(lines)
    
    # Convenience methods for common metrics
    def record_query(
        self,
        dataset: str,
        duration_seconds: float,
        success: bool,
        cache_hit: bool = False,
        rows: int = 0
    ) -> None:
        """Record query metrics."""
        labels = {"dataset": dataset}
        
        self.inc_counter("queries_total", labels=labels)
        
        if success:
            self.inc_counter("queries_success_total", labels=labels)
        else:
            self.inc_counter("queries_error_total", labels=labels)
        
        if cache_hit:
            self.inc_counter("queries_cache_hits_total", labels=labels)
        
        self.observe_histogram("query_duration_seconds", duration_seconds, labels=labels)
        self.inc_counter("query_rows_total", value=rows, labels=labels)
    
    def record_request(self, method: str, path: str, status: int, duration_seconds: float) -> None:
        """Record HTTP request metrics."""
        labels = {"method": method, "path": path, "status": str(status)}
        
        self.inc_counter("http_requests_total", labels=labels)
        self.observe_histogram("http_request_duration_seconds", duration_seconds, labels={"method": method, "path": path})
    
    def set_active_connections(self, count: int) -> None:
        """Set active connections gauge."""
        self.set_gauge("active_connections", count)
    
    def set_cache_size(self, size: int) -> None:
        """Set cache size gauge."""
        self.set_gauge("cache_size_bytes", size)


# =============================================================================
# OpenTelemetry Tracing
# =============================================================================

class Span:
    """Represents a trace span."""
    
    def __init__(
        self,
        tracer: "OpenTelemetryTracer",
        name: str,
        parent_id: Optional[str] = None
    ):
        self.tracer = tracer
        self.name = name
        self.trace_id = tracer._current_trace_id or self._generate_id(32)
        self.span_id = self._generate_id(16)
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.status = "OK"
        self.status_message: Optional[str] = None
    
    def _generate_id(self, length: int) -> str:
        """Generate a random ID."""
        import random
        return "".join(random.choices("0123456789abcdef", k=length))
    
    def set_attribute(self, key: str, value: Any) -> "Span":
        """Set a span attribute."""
        self.attributes[key] = value
        return self
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> "Span":
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
        return self
    
    def set_status(self, status: str, message: Optional[str] = None) -> "Span":
        """Set span status (OK, ERROR)."""
        self.status = status
        self.status_message = message
        return self
    
    def end(self) -> None:
        """End the span."""
        self.end_time = time.time()
        self.tracer._record_span(self)
    
    def __enter__(self) -> "Span":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.set_status("ERROR", str(exc_val))
            self.add_event("exception", {
                "exception.type": exc_type.__name__,
                "exception.message": str(exc_val),
            })
        self.end()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_id,
            "name": self.name,
            "startTimeUnixNano": int(self.start_time * 1e9),
            "endTimeUnixNano": int((self.end_time or time.time()) * 1e9),
            "attributes": self.attributes,
            "events": self.events,
            "status": {"code": self.status, "message": self.status_message},
        }


class OpenTelemetryTracer:
    """OpenTelemetry-compatible tracer."""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.service_name = config.tracing_service_name
        self._spans: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._current_trace_id: Optional[str] = None
        self._span_stack: List[Span] = []
    
    @contextmanager
    def start_trace(self, name: str):
        """Start a new trace."""
        if not self.config.tracing_enabled:
            yield None
            return
        
        # Apply sampling
        if self.config.tracing_sample_rate < 1.0:
            import random
            if random.random() > self.config.tracing_sample_rate:
                yield None
                return
        
        self._current_trace_id = None  # New trace
        span = Span(self, name)
        self._current_trace_id = span.trace_id
        self._span_stack.append(span)
        
        try:
            yield span
        finally:
            span.end()
            self._span_stack.pop()
            if not self._span_stack:
                self._current_trace_id = None
    
    @contextmanager
    def start_span(self, name: str):
        """Start a new span within current trace."""
        if not self.config.tracing_enabled or not self._current_trace_id:
            yield None
            return
        
        parent_id = self._span_stack[-1].span_id if self._span_stack else None
        span = Span(self, name, parent_id)
        self._span_stack.append(span)
        
        try:
            yield span
        finally:
            span.end()
            self._span_stack.pop()
    
    def _record_span(self, span: Span) -> None:
        """Record a completed span."""
        with self._lock:
            self._spans.append(span.to_dict())
            # Keep only last 1000 spans
            if len(self._spans) > 1000:
                self._spans = self._spans[-1000:]
    
    def get_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent spans."""
        with self._lock:
            return self._spans[-limit:]
    
    def export(self) -> Dict[str, Any]:
        """Export spans in OTLP format."""
        with self._lock:
            spans = self._spans.copy()
            self._spans = []
        
        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.service_name}},
                    ]
                },
                "scopeSpans": [{
                    "scope": {"name": "setupranali"},
                    "spans": spans,
                }]
            }]
        }


def trace(name: str):
    """Decorator to trace a function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer:
                with tracer.start_span(name) as span:
                    if span:
                        span.set_attribute("function", func.__name__)
                    return func(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Audit Logs
# =============================================================================

class AuditEventType(str, Enum):
    """Audit event types."""
    QUERY = "query"
    LOGIN = "login"
    LOGOUT = "logout"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    SOURCE_CREATED = "source_created"
    SOURCE_UPDATED = "source_updated"
    SOURCE_DELETED = "source_deleted"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_GRANTED = "permission_granted"
    CONFIG_CHANGED = "config_changed"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Audit log event."""
    
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    
    # Actor
    api_key_hash: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Resource
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    
    # Action details
    action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Result
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Metadata
    duration_ms: Optional[float] = None
    request_id: Optional[str] = None


class AuditLogger:
    """Audit log collector and exporter."""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self._events: List[AuditEvent] = []
        self._lock = threading.Lock()
        self._file_handler = None
        
        if config.audit_log_file:
            self._file_handler = open(config.audit_log_file, "a")
    
    def _hash_api_key(self, api_key: Optional[str]) -> Optional[str]:
        """Hash API key for logging."""
        if not api_key:
            return None
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive fields from details."""
        sanitized = {}
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in self.config.audit_sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def log(self, event: AuditEvent) -> None:
        """Log an audit event."""
        if not self.config.audit_enabled:
            return
        
        # Sanitize
        event.details = self._sanitize_details(event.details)
        
        with self._lock:
            self._events.append(event)
            
            # Write to file if configured
            if self._file_handler:
                self._file_handler.write(json.dumps(asdict(event), default=str) + "\n")
                self._file_handler.flush()
            
            # Keep only last 10000 events in memory
            if len(self._events) > 10000:
                self._events = self._events[-10000:]
    
    def log_query(
        self,
        dataset: str,
        dimensions: List[str],
        metrics: List[str],
        filters: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        rows_returned: int = 0,
        request_id: Optional[str] = None,
    ) -> None:
        """Log a query event."""
        details = {
            "dataset": dataset,
            "dimensions": dimensions,
            "metrics": metrics,
            "rows_returned": rows_returned,
        }
        
        if self.config.audit_include_query_text and filters:
            details["filters"] = filters
        
        event = AuditEvent(
            event_id=request_id or hashlib.sha256(str(time.time()).encode()).hexdigest()[:16],
            timestamp=datetime.now(),
            event_type=AuditEventType.QUERY,
            api_key_hash=self._hash_api_key(api_key),
            user_id=user_id,
            tenant_id=tenant_id,
            source_ip=source_ip,
            user_agent=user_agent,
            resource_type="dataset",
            resource_id=dataset,
            action="query",
            details=details,
            success=success,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        
        self.log(event)
    
    def log_auth(
        self,
        event_type: AuditEventType,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        success: bool = True,
        details: Dict[str, Any] = None,
    ) -> None:
        """Log an authentication event."""
        event = AuditEvent(
            event_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:16],
            timestamp=datetime.now(),
            event_type=event_type,
            api_key_hash=self._hash_api_key(api_key),
            user_id=user_id,
            source_ip=source_ip,
            action=event_type.value,
            details=details or {},
            success=success,
        )
        
        self.log(event)
    
    def log_permission(
        self,
        granted: bool,
        resource_type: str,
        resource_id: str,
        action: str,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Log a permission check."""
        event = AuditEvent(
            event_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:16],
            timestamp=datetime.now(),
            event_type=AuditEventType.PERMISSION_GRANTED if granted else AuditEventType.PERMISSION_DENIED,
            api_key_hash=self._hash_api_key(api_key),
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details={"reason": reason} if reason else {},
            success=granted,
        )
        
        self.log(event)
    
    def get_events(
        self,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get audit events with optional filtering."""
        with self._lock:
            events = self._events.copy()
        
        # Filter
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        # Return most recent
        return [asdict(e) for e in events[-limit:]]
    
    def close(self) -> None:
        """Close file handler."""
        if self._file_handler:
            self._file_handler.close()


# =============================================================================
# Global Instances
# =============================================================================

_config: Optional[ObservabilityConfig] = None
_analytics: Optional[QueryAnalytics] = None
_metrics: Optional[PrometheusMetrics] = None
_tracer: Optional[OpenTelemetryTracer] = None
_audit: Optional[AuditLogger] = None


def init_observability(config: Optional[ObservabilityConfig] = None) -> None:
    """Initialize observability components."""
    global _config, _analytics, _metrics, _tracer, _audit
    
    _config = config or load_config_from_env()
    _analytics = QueryAnalytics(_config)
    _metrics = PrometheusMetrics(_config)
    _tracer = OpenTelemetryTracer(_config)
    _audit = AuditLogger(_config)
    
    logger.info("Observability initialized")


def load_config_from_env() -> ObservabilityConfig:
    """Load configuration from environment variables."""
    return ObservabilityConfig(
        analytics_enabled=os.getenv("ANALYTICS_ENABLED", "true").lower() == "true",
        analytics_retention_hours=int(os.getenv("ANALYTICS_RETENTION_HOURS", "168")),
        metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
        metrics_prefix=os.getenv("METRICS_PREFIX", "setupranali"),
        tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
        tracing_sample_rate=float(os.getenv("TRACING_SAMPLE_RATE", "1.0")),
        tracing_exporter=os.getenv("TRACING_EXPORTER", "otlp"),
        tracing_endpoint=os.getenv("TRACING_ENDPOINT"),
        tracing_service_name=os.getenv("TRACING_SERVICE_NAME", "setupranali"),
        audit_enabled=os.getenv("AUDIT_ENABLED", "true").lower() == "true",
        audit_log_file=os.getenv("AUDIT_LOG_FILE"),
        audit_include_query_text=os.getenv("AUDIT_INCLUDE_QUERY_TEXT", "true").lower() == "true",
    )


def get_analytics() -> Optional[QueryAnalytics]:
    """Get query analytics instance."""
    global _analytics
    if _analytics is None:
        # Auto-initialize if not already initialized
        logger.warning("Analytics not initialized, auto-initializing...")
        try:
            init_observability()
        except Exception as e:
            logger.error(f"Failed to auto-initialize analytics: {e}", exc_info=True)
    return _analytics


def get_metrics() -> Optional[PrometheusMetrics]:
    """Get metrics exporter instance."""
    return _metrics


def get_tracer() -> Optional[OpenTelemetryTracer]:
    """Get tracer instance."""
    return _tracer


def get_audit() -> Optional[AuditLogger]:
    """Get audit logger instance."""
    return _audit

