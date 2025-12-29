"""
Advanced Data Features for SetuPranali

Provides powerful data capabilities:
- Semantic Joins: Join across datasets in the semantic layer
- Calculated Metrics: Define metrics based on other metrics
- Caching Strategies: Smart cache invalidation, pre-warming
- Query Federation: Query across multiple data sources

Features:
- Cross-dataset relationships
- Metric composition and inheritance
- Intelligent cache management
- Multi-source query execution
"""

import os
import re
import time
import asyncio
import logging
import hashlib
import threading
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class AdvancedFeaturesConfig(BaseModel):
    """Advanced features configuration."""
    
    # Semantic Joins
    joins_enabled: bool = Field(default=True)
    max_join_depth: int = Field(default=3)
    
    # Calculated Metrics
    calculated_metrics_enabled: bool = Field(default=True)
    max_metric_depth: int = Field(default=5)
    
    # Caching
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600)
    cache_max_size_mb: int = Field(default=1024)
    cache_prewarm_enabled: bool = Field(default=True)
    cache_invalidation_enabled: bool = Field(default=True)
    
    # Federation
    federation_enabled: bool = Field(default=True)
    federation_timeout_seconds: int = Field(default=60)
    federation_max_sources: int = Field(default=10)


# =============================================================================
# SEMANTIC JOINS
# =============================================================================

class JoinType(str, Enum):
    """Join types."""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"


@dataclass
class JoinDefinition:
    """Definition of a semantic join between datasets."""
    
    left_dataset: str
    right_dataset: str
    join_type: JoinType
    
    # Join keys
    left_key: str
    right_key: str
    
    # Optional: additional join conditions
    conditions: List[str] = field(default_factory=list)
    
    # Alias for joined dataset
    alias: Optional[str] = None
    
    # Cardinality hint
    cardinality: str = "many-to-one"  # one-to-one, one-to-many, many-to-one, many-to-many


@dataclass
class JoinPath:
    """Path of joins between datasets."""
    
    datasets: List[str]
    joins: List[JoinDefinition]
    
    def get_sql(self) -> str:
        """Generate SQL for join path."""
        if not self.joins:
            return ""
        
        sql_parts = []
        for join in self.joins:
            join_sql = f"{join.join_type.value.upper()} JOIN {join.right_dataset}"
            if join.alias:
                join_sql += f" AS {join.alias}"
            join_sql += f" ON {join.left_dataset}.{join.left_key} = {join.right_dataset}.{join.right_key}"
            
            if join.conditions:
                join_sql += " AND " + " AND ".join(join.conditions)
            
            sql_parts.append(join_sql)
        
        return " ".join(sql_parts)


class SemanticJoinManager:
    """Manage semantic joins between datasets."""
    
    def __init__(self, config: AdvancedFeaturesConfig):
        self.config = config
        self._joins: Dict[str, List[JoinDefinition]] = defaultdict(list)
        self._graph: Dict[str, Set[str]] = defaultdict(set)
    
    def register_join(self, join: JoinDefinition) -> None:
        """Register a join between datasets."""
        key = f"{join.left_dataset}:{join.right_dataset}"
        self._joins[key].append(join)
        
        # Update graph
        self._graph[join.left_dataset].add(join.right_dataset)
        self._graph[join.right_dataset].add(join.left_dataset)
    
    def find_join_path(
        self,
        from_dataset: str,
        to_dataset: str,
        max_depth: Optional[int] = None
    ) -> Optional[JoinPath]:
        """Find shortest join path between datasets using BFS."""
        if not self.config.joins_enabled:
            return None
        
        max_depth = max_depth or self.config.max_join_depth
        
        if from_dataset == to_dataset:
            return JoinPath(datasets=[from_dataset], joins=[])
        
        # BFS to find shortest path
        queue = [(from_dataset, [from_dataset], [])]
        visited = {from_dataset}
        
        while queue:
            current, path, joins = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            for neighbor in self._graph.get(current, []):
                if neighbor in visited:
                    continue
                
                # Find the join definition
                join = self._get_join(current, neighbor)
                if not join:
                    continue
                
                new_path = path + [neighbor]
                new_joins = joins + [join]
                
                if neighbor == to_dataset:
                    return JoinPath(datasets=new_path, joins=new_joins)
                
                visited.add(neighbor)
                queue.append((neighbor, new_path, new_joins))
        
        return None
    
    def _get_join(self, dataset1: str, dataset2: str) -> Optional[JoinDefinition]:
        """Get join definition between two datasets."""
        key1 = f"{dataset1}:{dataset2}"
        key2 = f"{dataset2}:{dataset1}"
        
        if key1 in self._joins:
            return self._joins[key1][0]
        elif key2 in self._joins:
            # Reverse the join
            original = self._joins[key2][0]
            return JoinDefinition(
                left_dataset=dataset2,
                right_dataset=dataset1,
                join_type=original.join_type,
                left_key=original.right_key,
                right_key=original.left_key,
                conditions=original.conditions,
                cardinality=self._reverse_cardinality(original.cardinality)
            )
        
        return None
    
    def _reverse_cardinality(self, cardinality: str) -> str:
        """Reverse cardinality direction."""
        mapping = {
            "one-to-many": "many-to-one",
            "many-to-one": "one-to-many",
        }
        return mapping.get(cardinality, cardinality)
    
    def get_joinable_datasets(self, dataset: str) -> List[str]:
        """Get all datasets that can be joined with the given dataset."""
        reachable = set()
        queue = [dataset]
        visited = {dataset}
        depth = 0
        
        while queue and depth < self.config.max_join_depth:
            next_queue = []
            for current in queue:
                for neighbor in self._graph.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        reachable.add(neighbor)
                        next_queue.append(neighbor)
            queue = next_queue
            depth += 1
        
        return list(reachable)


# =============================================================================
# CALCULATED METRICS
# =============================================================================

class MetricOperation(str, Enum):
    """Metric calculation operations."""
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    RATIO = "ratio"
    PERCENT = "percent"
    AVG = "avg"
    GROWTH = "growth"
    CUMULATIVE = "cumulative"
    RUNNING_AVG = "running_avg"


@dataclass
class CalculatedMetric:
    """Definition of a calculated metric."""
    
    name: str
    expression: str  # Formula expression
    description: Optional[str] = None
    
    # Components
    base_metrics: List[str] = field(default_factory=list)
    
    # Formatting
    format: str = "number"  # number, percent, currency
    decimal_places: int = 2
    
    # Dependencies
    requires_dimensions: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)


class CalculatedMetricEngine:
    """Engine for calculated metrics."""
    
    def __init__(self, config: AdvancedFeaturesConfig):
        self.config = config
        self._metrics: Dict[str, CalculatedMetric] = {}
        self._base_metrics: Dict[str, Dict[str, Any]] = {}  # name -> definition
    
    def register_metric(self, metric: CalculatedMetric) -> None:
        """Register a calculated metric."""
        self._metrics[metric.name] = metric
    
    def register_base_metric(self, name: str, definition: Dict[str, Any]) -> None:
        """Register a base metric from catalog."""
        self._base_metrics[name] = definition
    
    def resolve_expression(
        self,
        expression: str,
        depth: int = 0
    ) -> str:
        """Resolve calculated metric expression to SQL."""
        if not self.config.calculated_metrics_enabled:
            return expression
        
        if depth > self.config.max_metric_depth:
            raise ValueError(f"Max metric depth exceeded: {expression}")
        
        # Parse expression
        result = expression
        
        # Find metric references (e.g., {revenue}, {order_count})
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, expression)
        
        for metric_name in matches:
            if metric_name in self._metrics:
                # Recursive resolution for calculated metrics
                sub_expr = self.resolve_expression(
                    self._metrics[metric_name].expression,
                    depth + 1
                )
                result = result.replace(f"{{{metric_name}}}", f"({sub_expr})")
            elif metric_name in self._base_metrics:
                # Base metric - use SQL
                base = self._base_metrics[metric_name]
                sql = base.get("sql", metric_name)
                result = result.replace(f"{{{metric_name}}}", f"({sql})")
            else:
                # Unknown metric - leave as column reference
                result = result.replace(f"{{{metric_name}}}", metric_name)
        
        return result
    
    def get_sql(self, metric_name: str) -> str:
        """Get SQL for a metric (base or calculated)."""
        if metric_name in self._metrics:
            return self.resolve_expression(self._metrics[metric_name].expression)
        elif metric_name in self._base_metrics:
            return self._base_metrics[metric_name].get("sql", metric_name)
        else:
            return metric_name
    
    def get_dependencies(self, metric_name: str) -> Set[str]:
        """Get all base metric dependencies for a calculated metric."""
        if metric_name not in self._metrics:
            return {metric_name}
        
        dependencies = set()
        expression = self._metrics[metric_name].expression
        
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, expression)
        
        for match in matches:
            if match in self._metrics:
                # Recursive dependency resolution
                dependencies.update(self.get_dependencies(match))
            else:
                dependencies.add(match)
        
        return dependencies
    
    def validate_metric(self, metric: CalculatedMetric) -> List[str]:
        """Validate a calculated metric definition."""
        errors = []
        
        # Check for circular dependencies
        if self._has_circular_dependency(metric.name, metric.expression):
            errors.append(f"Circular dependency detected in metric: {metric.name}")
        
        # Check that all referenced metrics exist
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, metric.expression)
        
        for match in matches:
            if match not in self._metrics and match not in self._base_metrics:
                errors.append(f"Unknown metric reference: {match}")
        
        return errors
    
    def _has_circular_dependency(
        self,
        metric_name: str,
        expression: str,
        visited: Optional[Set[str]] = None
    ) -> bool:
        """Check for circular dependencies."""
        visited = visited or set()
        
        if metric_name in visited:
            return True
        
        visited.add(metric_name)
        
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, expression)
        
        for match in matches:
            if match in self._metrics:
                if self._has_circular_dependency(
                    match,
                    self._metrics[match].expression,
                    visited.copy()
                ):
                    return True
        
        return False


# =============================================================================
# CACHING STRATEGIES
# =============================================================================

class CacheStrategy(str, Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"  # Time-based expiration
    LRU = "lru"  # Least recently used
    LFU = "lfu"  # Least frequently used
    WRITE_THROUGH = "write_through"  # Invalidate on write
    MANUAL = "manual"  # Manual invalidation only


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    
    # Source tracking
    dataset: Optional[str] = None
    query_hash: Optional[str] = None


@dataclass
class CacheStats:
    """Cache statistics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class SmartCache:
    """Smart caching with multiple strategies."""
    
    def __init__(self, config: AdvancedFeaturesConfig):
        self.config = config
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        # Pre-warm queue
        self._prewarm_queue: List[Dict[str, Any]] = []
        
        # Invalidation patterns
        self._invalidation_patterns: Dict[str, List[str]] = defaultdict(list)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.config.cache_enabled:
            return None
        
        with self._lock:
            entry = self._cache.get(key)
            
            if not entry:
                self._stats.misses += 1
                return None
            
            # Check expiration
            if datetime.now() > entry.expires_at:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            # Update access stats
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._stats.hits += 1
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: List[str] = None,
        dataset: Optional[str] = None
    ) -> None:
        """Set value in cache."""
        if not self.config.cache_enabled:
            return
        
        ttl = ttl_seconds or self.config.cache_ttl_seconds
        
        with self._lock:
            # Calculate size
            size_bytes = len(str(value).encode())
            
            # Check max size
            self._ensure_capacity(size_bytes)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl),
                size_bytes=size_bytes,
                tags=tags or [],
                dataset=dataset,
                query_hash=hashlib.sha256(key.encode()).hexdigest()[:16]
            )
            
            self._cache[key] = entry
            self._stats.size_bytes += size_bytes
            self._stats.entry_count = len(self._cache)
            
            # Register invalidation patterns
            if dataset:
                self._invalidation_patterns[dataset].append(key)
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._stats.size_bytes -= entry.size_bytes
                del self._cache[key]
                self._stats.evictions += 1
                self._stats.entry_count = len(self._cache)
                return True
            return False
    
    def invalidate_by_dataset(self, dataset: str) -> int:
        """Invalidate all cache entries for a dataset."""
        count = 0
        with self._lock:
            keys = self._invalidation_patterns.get(dataset, []).copy()
            for key in keys:
                if self.invalidate(key):
                    count += 1
            self._invalidation_patterns[dataset] = []
        return count
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag."""
        count = 0
        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if tag in entry.tags
            ]
            for key in keys_to_remove:
                if self.invalidate(key):
                    count += 1
        return count
    
    def prewarm(self, queries: List[Dict[str, Any]], executor: Callable) -> int:
        """Pre-warm cache with common queries."""
        if not self.config.cache_prewarm_enabled:
            return 0
        
        count = 0
        for query in queries:
            try:
                # Generate cache key
                key = self._generate_key(query)
                
                # Skip if already cached
                if key in self._cache:
                    continue
                
                # Execute query
                result = executor(query)
                
                # Cache result
                self.set(
                    key=key,
                    value=result,
                    dataset=query.get("dataset"),
                    tags=["prewarm"]
                )
                count += 1
                
            except Exception as e:
                logger.warning(f"Prewarm failed for query: {e}")
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "hit_rate": self._stats.hit_rate,
                "evictions": self._stats.evictions,
                "size_bytes": self._stats.size_bytes,
                "size_mb": self._stats.size_bytes / (1024 * 1024),
                "entry_count": self._stats.entry_count,
                "max_size_mb": self.config.cache_max_size_mb,
            }
    
    def _ensure_capacity(self, needed_bytes: int) -> None:
        """Ensure cache has capacity for new entry."""
        max_bytes = self.config.cache_max_size_mb * 1024 * 1024
        
        while self._stats.size_bytes + needed_bytes > max_bytes and self._cache:
            # Evict LRU entry
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed or self._cache[k].created_at
            )
            self.invalidate(oldest_key)
    
    def _generate_key(self, query: Dict[str, Any]) -> str:
        """Generate cache key for query."""
        key_parts = [
            query.get("dataset", ""),
            str(sorted(query.get("dimensions", []))),
            str(sorted(query.get("metrics", []))),
            str(query.get("filters", {})),
        ]
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()


# =============================================================================
# QUERY FEDERATION
# =============================================================================

@dataclass
class FederatedSource:
    """A federated data source."""
    
    id: str
    name: str
    type: str  # postgres, mysql, bigquery, etc.
    connection: Dict[str, Any]
    
    # Source metadata
    datasets: List[str] = field(default_factory=list)
    priority: int = 0  # Lower = higher priority
    
    # Health
    healthy: bool = True
    last_check: Optional[datetime] = None
    error_count: int = 0


@dataclass
class FederatedQuery:
    """A query spanning multiple sources."""
    
    id: str
    sources: List[FederatedSource]
    sub_queries: Dict[str, Dict[str, Any]]  # source_id -> query
    join_strategy: str = "merge"  # merge, union, join
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    timing: Dict[str, float] = field(default_factory=dict)


class QueryFederator:
    """Execute queries across multiple data sources."""
    
    def __init__(self, config: AdvancedFeaturesConfig):
        self.config = config
        self._sources: Dict[str, FederatedSource] = {}
        self._dataset_source_map: Dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=config.federation_max_sources)
    
    def register_source(self, source: FederatedSource) -> None:
        """Register a federated data source."""
        self._sources[source.id] = source
        
        # Map datasets to source
        for dataset in source.datasets:
            self._dataset_source_map[dataset] = source.id
    
    def get_source_for_dataset(self, dataset: str) -> Optional[FederatedSource]:
        """Get the source containing a dataset."""
        source_id = self._dataset_source_map.get(dataset)
        return self._sources.get(source_id) if source_id else None
    
    async def execute_federated(
        self,
        query: Dict[str, Any],
        source_executors: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """Execute a federated query across multiple sources."""
        if not self.config.federation_enabled:
            raise ValueError("Federation is disabled")
        
        dataset = query.get("dataset")
        
        # Simple case: single source
        source = self.get_source_for_dataset(dataset)
        if source:
            executor = source_executors.get(source.id)
            if executor:
                return await self._execute_single(query, source, executor)
        
        # Complex case: cross-source query
        return await self._execute_cross_source(query, source_executors)
    
    async def _execute_single(
        self,
        query: Dict[str, Any],
        source: FederatedSource,
        executor: Callable
    ) -> Dict[str, Any]:
        """Execute query on a single source."""
        start = time.time()
        
        try:
            result = await executor(query)
            
            return {
                "data": result.get("data", []),
                "source": source.id,
                "timing_ms": (time.time() - start) * 1000,
                "federated": False
            }
            
        except Exception as e:
            source.error_count += 1
            raise
    
    async def _execute_cross_source(
        self,
        query: Dict[str, Any],
        source_executors: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """Execute query spanning multiple sources."""
        # Identify required sources
        datasets = self._identify_datasets(query)
        source_queries = self._split_query(query, datasets)
        
        start = time.time()
        results = {}
        errors = {}
        timing = {}
        
        # Execute queries in parallel
        futures = {}
        for source_id, sub_query in source_queries.items():
            if source_id in source_executors:
                future = self._executor.submit(
                    self._run_sync,
                    source_executors[source_id],
                    sub_query
                )
                futures[source_id] = future
        
        # Collect results
        for source_id, future in futures.items():
            try:
                sub_start = time.time()
                result = future.result(timeout=self.config.federation_timeout_seconds)
                results[source_id] = result.get("data", [])
                timing[source_id] = (time.time() - sub_start) * 1000
            except Exception as e:
                errors[source_id] = str(e)
                logger.error(f"Federation query failed for {source_id}: {e}")
        
        # Merge results
        merged_data = self._merge_results(results, query)
        
        return {
            "data": merged_data,
            "federated": True,
            "sources": list(results.keys()),
            "timing_ms": (time.time() - start) * 1000,
            "sub_timing": timing,
            "errors": errors if errors else None
        }
    
    def _run_sync(self, executor: Callable, query: Dict[str, Any]) -> Any:
        """Run async executor synchronously."""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(executor(query))
        finally:
            loop.close()
    
    def _identify_datasets(self, query: Dict[str, Any]) -> List[str]:
        """Identify all datasets referenced in query."""
        datasets = []
        
        # Main dataset
        if "dataset" in query:
            datasets.append(query["dataset"])
        
        # Joined datasets
        if "joins" in query:
            for join in query["joins"]:
                if "dataset" in join:
                    datasets.append(join["dataset"])
        
        return datasets
    
    def _split_query(
        self,
        query: Dict[str, Any],
        datasets: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Split query into per-source sub-queries."""
        source_queries = {}
        
        for dataset in datasets:
            source_id = self._dataset_source_map.get(dataset)
            if not source_id:
                continue
            
            # Create sub-query for this source
            sub_query = {
                "dataset": dataset,
                "dimensions": query.get("dimensions", []),
                "metrics": query.get("metrics", []),
                "filters": query.get("filters", {}),
            }
            
            source_queries[source_id] = sub_query
        
        return source_queries
    
    def _merge_results(
        self,
        results: Dict[str, List[Dict]],
        query: Dict[str, Any]
    ) -> List[Dict]:
        """Merge results from multiple sources."""
        if not results:
            return []
        
        # Simple merge: concatenate and deduplicate
        all_rows = []
        for source_id, rows in results.items():
            for row in rows:
                row["_source"] = source_id
                all_rows.append(row)
        
        # Group by dimensions
        dimensions = query.get("dimensions", [])
        if not dimensions:
            return all_rows
        
        grouped = defaultdict(list)
        for row in all_rows:
            key = tuple(row.get(d) for d in dimensions)
            grouped[key].append(row)
        
        # Aggregate metrics
        metrics = query.get("metrics", [])
        merged = []
        
        for key, rows in grouped.items():
            merged_row = {d: k for d, k in zip(dimensions, key)}
            
            for metric in metrics:
                values = [r.get(metric, 0) for r in rows if metric in r]
                if values:
                    # Sum by default
                    merged_row[metric] = sum(values)
            
            merged.append(merged_row)
        
        return merged
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all federated sources."""
        health = {}
        
        for source_id, source in self._sources.items():
            # Simple health check
            source.last_check = datetime.now()
            health[source_id] = source.healthy
        
        return health


# =============================================================================
# UNIFIED SERVICE
# =============================================================================

class AdvancedDataService:
    """Unified service for advanced data features."""
    
    def __init__(self, config: AdvancedFeaturesConfig):
        self.config = config
        self.join_manager = SemanticJoinManager(config)
        self.metric_engine = CalculatedMetricEngine(config)
        self.cache = SmartCache(config)
        self.federator = QueryFederator(config)
    
    def register_join(self, join: JoinDefinition) -> None:
        """Register a semantic join."""
        self.join_manager.register_join(join)
    
    def register_metric(self, metric: CalculatedMetric) -> None:
        """Register a calculated metric."""
        self.metric_engine.register_metric(metric)
    
    def register_base_metric(self, name: str, definition: Dict[str, Any]) -> None:
        """Register a base metric."""
        self.metric_engine.register_base_metric(name, definition)
    
    def register_source(self, source: FederatedSource) -> None:
        """Register a federated source."""
        self.federator.register_source(source)
    
    def find_join_path(self, from_ds: str, to_ds: str) -> Optional[JoinPath]:
        """Find join path between datasets."""
        return self.join_manager.find_join_path(from_ds, to_ds)
    
    def resolve_metric(self, metric_name: str) -> str:
        """Resolve metric to SQL."""
        return self.metric_engine.get_sql(metric_name)
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        return self.cache.get(key)
    
    def cache_set(self, key: str, value: Any, **kwargs) -> None:
        """Set in cache."""
        self.cache.set(key, value, **kwargs)
    
    def invalidate_cache(self, dataset: str) -> int:
        """Invalidate cache for dataset."""
        return self.cache.invalidate_by_dataset(dataset)
    
    async def federated_query(
        self,
        query: Dict[str, Any],
        executors: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """Execute federated query."""
        return await self.federator.execute_federated(query, executors)


# =============================================================================
# Global Instance
# =============================================================================

_service: Optional[AdvancedDataService] = None


def init_advanced_features(config: Optional[AdvancedFeaturesConfig] = None) -> AdvancedDataService:
    """Initialize advanced features service."""
    global _service
    
    config = config or load_config_from_env()
    _service = AdvancedDataService(config)
    
    logger.info("Advanced data features initialized")
    return _service


def get_advanced_service() -> Optional[AdvancedDataService]:
    """Get advanced features service."""
    return _service


def load_config_from_env() -> AdvancedFeaturesConfig:
    """Load configuration from environment."""
    return AdvancedFeaturesConfig(
        joins_enabled=os.getenv("JOINS_ENABLED", "true").lower() == "true",
        max_join_depth=int(os.getenv("MAX_JOIN_DEPTH", "3")),
        calculated_metrics_enabled=os.getenv("CALCULATED_METRICS_ENABLED", "true").lower() == "true",
        cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
        cache_max_size_mb=int(os.getenv("CACHE_MAX_SIZE_MB", "1024")),
        cache_prewarm_enabled=os.getenv("CACHE_PREWARM_ENABLED", "true").lower() == "true",
        federation_enabled=os.getenv("FEDERATION_ENABLED", "true").lower() == "true",
        federation_timeout_seconds=int(os.getenv("FEDERATION_TIMEOUT_SECONDS", "60")),
    )

