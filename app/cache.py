"""
Query Cache & Deduplication Layer for SetuPranali

This module provides:
1. Redis-based query result caching
2. In-flight query deduplication (prevents thundering herd)
3. Tenant-scoped cache keys (security-first design)

ARCHITECTURE:
-------------
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  BI Tools   │────▶│ Cache Layer │────▶│Query Engine │
│             │◀────│             │◀────│             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │    Redis    │
                    └─────────────┘

KEY DESIGN PRINCIPLES:
----------------------
1. Cache is an OPTIMIZATION, not a source of truth
2. Security first: no cross-tenant cache leakage
3. Graceful degradation: system works without Redis
4. Zero BI tool configuration required

CACHE KEY STRUCTURE:
--------------------
Key: ubi:cache:{sha256_hash}

The hash is computed from:
- tenant (CRITICAL for RLS)
- role (admin may see different data)
- dataset
- sourceId
- engine type
- normalized query (dimensions, metrics, filters, orderBy, limit, offset)
- incremental window (from/to)

This ensures:
- Different tenants NEVER share cache
- Admin bypass results cached separately
- Incremental windows cached separately

DEDUPLICATION:
--------------
When the same query is in-flight (being executed):
- Subsequent requests wait for the first execution
- All waiting requests receive the same result
- Prevents "thundering herd" during BI refresh storms

Uses Redis SETNX (set if not exists) for distributed locking.
Falls back to in-memory asyncio locks if Redis unavailable.
"""

import os
import json
import hashlib
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Redis is optional - graceful fallback if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class CacheConfig:
    """
    Cache configuration loaded from environment variables.
    
    Environment variables:
    - CACHE_ENABLED: Enable/disable caching (default: true)
    - REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    - CACHE_TTL_SECONDS: Default TTL in seconds (default: 60)
    - CACHE_MAX_ROWS: Skip caching results larger than this (default: 10000)
    - CACHE_ADMIN_BYPASS: Cache results for admin bypass queries (default: false)
    """
    enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    ttl_seconds: int = 60
    max_rows: int = 10000
    cache_admin_bypass: bool = False
    lock_timeout_seconds: int = 30  # How long to wait for in-flight query
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Load configuration from environment variables."""
        return cls(
            enabled=os.environ.get("CACHE_ENABLED", "true").lower() == "true",
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            ttl_seconds=int(os.environ.get("CACHE_TTL_SECONDS", "60")),
            max_rows=int(os.environ.get("CACHE_MAX_ROWS", "10000")),
            cache_admin_bypass=os.environ.get("CACHE_ADMIN_BYPASS", "false").lower() == "true",
            lock_timeout_seconds=int(os.environ.get("CACHE_LOCK_TIMEOUT", "30"))
        )


# Global configuration
_config: Optional[CacheConfig] = None


def get_cache_config() -> CacheConfig:
    """Get or create cache configuration."""
    global _config
    if _config is None:
        _config = CacheConfig.from_env()
    return _config


# =============================================================================
# REDIS CLIENT
# =============================================================================

_redis_client: Optional["redis.Redis"] = None
_redis_connection_failed: bool = False


def get_redis_client() -> Optional["redis.Redis"]:
    """
    Get Redis client with graceful fallback.
    
    If Redis is unavailable:
    - Returns None
    - Logs warning once
    - System continues without caching
    
    This ensures BI tools never fail due to cache infrastructure.
    """
    global _redis_client, _redis_connection_failed
    
    config = get_cache_config()
    
    if not config.enabled:
        return None
    
    if not REDIS_AVAILABLE:
        if not _redis_connection_failed:
            logger.warning("redis-py not installed. Caching disabled. pip install redis")
            _redis_connection_failed = True
        return None
    
    if _redis_connection_failed:
        # Don't retry every request if we already failed
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                config.redis_url,
                socket_connect_timeout=2,  # Fast fail
                socket_timeout=5
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis connected: {config.redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Caching disabled.")
            _redis_connection_failed = True
            _redis_client = None
    
    return _redis_client


def reset_redis_client():
    """Reset Redis client (for testing or reconnection)."""
    global _redis_client, _redis_connection_failed
    _redis_client = None
    _redis_connection_failed = False


# =============================================================================
# CACHE KEY BUILDER
# =============================================================================

@dataclass
class CacheKeyComponents:
    """
    All components that form a unique cache key.
    
    SECURITY: tenant and role are REQUIRED to prevent cross-tenant leakage.
    """
    tenant: str
    role: str
    dataset: str
    source_id: Optional[str] = None
    engine: str = "duckdb"
    dimensions: List[Dict] = field(default_factory=list)
    metrics: List[Dict] = field(default_factory=list)
    filters: Optional[Dict] = None
    order_by: List[Dict] = field(default_factory=list)
    limit: int = 10000
    offset: int = 0
    incremental: bool = False
    incremental_from: Optional[str] = None
    incremental_to: Optional[str] = None


def normalize_for_cache(obj: Any) -> Any:
    """
    Normalize an object for stable JSON serialization.
    
    - Sorts dictionary keys
    - Converts dates/datetimes to ISO strings
    - Removes None values
    
    This ensures identical queries produce identical cache keys.
    """
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        # Sort keys and recursively normalize values
        return {k: normalize_for_cache(v) for k, v in sorted(obj.items()) if v is not None}
    
    if isinstance(obj, (list, tuple)):
        return [normalize_for_cache(item) for item in obj]
    
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    if hasattr(obj, 'isoformat'):  # date, time
        return obj.isoformat()
    
    if hasattr(obj, 'model_dump'):  # Pydantic model
        return normalize_for_cache(obj.model_dump(by_alias=True, exclude_none=True))
    
    if hasattr(obj, '__dict__'):  # Dataclass or similar
        return normalize_for_cache(obj.__dict__)
    
    return obj


def build_cache_key(components: CacheKeyComponents) -> str:
    """
    Build a cache key from query components.
    
    Key structure: ubi:cache:{sha256_hash}
    
    The hash includes ALL security-relevant components:
    - tenant (CRITICAL)
    - role (admin sees different data)
    - dataset, source, engine
    - full normalized query
    
    Returns a short, safe key suitable for Redis.
    """
    # Build canonical representation
    canonical = {
        "tenant": components.tenant,
        "role": components.role,
        "dataset": components.dataset,
        "source_id": components.source_id,
        "engine": components.engine,
        "dimensions": normalize_for_cache(components.dimensions),
        "metrics": normalize_for_cache(components.metrics),
        "filters": normalize_for_cache(components.filters),
        "order_by": normalize_for_cache(components.order_by),
        "limit": components.limit,
        "offset": components.offset,
        "incremental": components.incremental,
        "incremental_from": components.incremental_from,
        "incremental_to": components.incremental_to
    }
    
    # Create stable JSON (sorted keys)
    json_str = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
    
    # SHA256 hash for compact key
    hash_bytes = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    return f"ubi:cache:{hash_bytes}"


def get_short_key(cache_key: str) -> str:
    """Get short version of cache key for logging/stats."""
    if cache_key.startswith("ubi:cache:"):
        return cache_key[10:18]  # First 8 chars of hash
    return cache_key[:8]


# =============================================================================
# IN-FLIGHT DEDUPLICATION
# =============================================================================
# Prevents "thundering herd" when multiple BI tools refresh simultaneously.
# Uses Redis SETNX for distributed locking with graceful fallback to asyncio.

_in_flight_locks: Dict[str, asyncio.Event] = {}
_in_flight_results: Dict[str, Tuple[bool, Any]] = {}  # (success, result_or_error)


class InFlightLock:
    """
    Manages in-flight query deduplication.
    
    When the same query is executing:
    - First caller acquires lock and executes
    - Subsequent callers wait for result
    - All receive the same cached result
    
    Uses Redis SETNX for distributed coordination.
    Falls back to in-memory locks if Redis unavailable.
    """
    
    def __init__(self, cache_key: str, ttl_seconds: int = 30):
        self.cache_key = cache_key
        self.lock_key = f"ubi:lock:{cache_key[10:]}"  # ubi:lock:{hash}
        self.ttl_seconds = ttl_seconds
        self.is_owner = False
        self._redis = get_redis_client()
    
    def acquire(self) -> bool:
        """
        Try to acquire the in-flight lock.
        
        Returns True if this caller should execute the query.
        Returns False if another caller is already executing.
        """
        if self._redis:
            # Distributed lock via Redis SETNX
            acquired = self._redis.set(
                self.lock_key,
                "1",
                nx=True,  # Only set if not exists
                ex=self.ttl_seconds  # Auto-expire
            )
            self.is_owner = bool(acquired)
            return self.is_owner
        else:
            # In-memory fallback
            if self.cache_key not in _in_flight_locks:
                _in_flight_locks[self.cache_key] = asyncio.Event()
                self.is_owner = True
                return True
            return False
    
    def release(self, success: bool, result: Any):
        """
        Release the lock and store result for waiting callers.
        
        Args:
            success: Whether query succeeded
            result: Query result (or error if failed)
        """
        if self._redis and self.is_owner:
            # Delete lock key
            self._redis.delete(self.lock_key)
        
        if self.cache_key in _in_flight_locks:
            # Store result for waiters
            _in_flight_results[self.cache_key] = (success, result)
            # Signal waiters
            _in_flight_locks[self.cache_key].set()
    
    async def wait_for_result(self, timeout: float = 30.0) -> Tuple[bool, Any]:
        """
        Wait for another caller to finish executing.
        
        Returns (success, result) from the executing caller.
        """
        if self._redis:
            # Poll Redis for result
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                # Check if lock is released
                if not self._redis.exists(self.lock_key):
                    # Try to get cached result
                    cached = self._redis.get(self.cache_key)
                    if cached:
                        return True, json.loads(cached)
                    # Lock released but no cache - query failed or wasn't cached
                    break
                await asyncio.sleep(0.1)  # Poll interval
            
            # Timeout or no result - execute ourselves
            return False, None
        else:
            # In-memory wait
            if self.cache_key in _in_flight_locks:
                try:
                    await asyncio.wait_for(
                        _in_flight_locks[self.cache_key].wait(),
                        timeout=timeout
                    )
                    if self.cache_key in _in_flight_results:
                        return _in_flight_results.pop(self.cache_key)
                except asyncio.TimeoutError:
                    pass
                finally:
                    # Cleanup
                    _in_flight_locks.pop(self.cache_key, None)
            
            return False, None


# =============================================================================
# CACHE OPERATIONS
# =============================================================================

@dataclass
class CacheResult:
    """Result of a cache operation."""
    hit: bool = False
    key: str = ""
    ttl: int = 0
    deduplicated: bool = False
    data: Optional[Dict] = None
    error: Optional[str] = None


def get_from_cache(cache_key: str) -> Optional[Dict]:
    """
    Get cached query result.
    
    Returns None if:
    - Cache disabled
    - Redis unavailable
    - Key not found
    - Deserialization error
    """
    redis_client = get_redis_client()
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    
    return None


def _serialize_for_cache(obj: Any) -> Any:
    """
    Recursively serialize an object for JSON/Redis storage.
    
    Handles:
    - Pydantic models (model_dump)
    - Dataclasses
    - datetime/date objects
    - Lists and dicts (recursively)
    """
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        return {k: _serialize_for_cache(v) for k, v in obj.items()}
    
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_cache(item) for item in obj]
    
    if hasattr(obj, 'model_dump'):  # Pydantic model
        return obj.model_dump(by_alias=True, exclude_none=True)
    
    if hasattr(obj, '__dataclass_fields__'):  # Dataclass
        from dataclasses import asdict
        return asdict(obj)
    
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    if hasattr(obj, 'isoformat'):  # date, time
        return obj.isoformat()
    
    return obj


def set_in_cache(
    cache_key: str,
    columns: List[Dict],
    rows: List[Dict],
    stats: Dict,
    ttl_seconds: Optional[int] = None
) -> bool:
    """
    Store query result in cache.
    
    Skips caching if:
    - Cache disabled
    - Redis unavailable
    - Result too large (exceeds max_rows)
    - Admin bypass result (unless explicitly allowed)
    
    Returns True if cached successfully.
    """
    config = get_cache_config()
    redis_client = get_redis_client()
    
    if not redis_client:
        return False
    
    # Check result size
    if len(rows) > config.max_rows:
        logger.debug(f"Skipping cache: {len(rows)} rows > max {config.max_rows}")
        return False
    
    # Check admin bypass policy
    if stats.get("rlsBypassed") and not config.cache_admin_bypass:
        logger.debug("Skipping cache: admin bypass result")
        return False
    
    ttl = ttl_seconds or config.ttl_seconds
    
    # Serialize Pydantic models and other non-JSON types
    cache_value = {
        "columns": _serialize_for_cache(columns),
        "rows": _serialize_for_cache(rows),
        "stats": _serialize_for_cache(stats),
        "cachedAt": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        redis_client.set(cache_key, json.dumps(cache_value), ex=ttl)
        return True
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
        return False


# =============================================================================
# QUERY EXECUTION WITH CACHING
# =============================================================================

def execute_with_cache(
    execute_fn: Callable[[], Tuple[List, List, Dict]],
    cache_components: CacheKeyComponents,
    ttl_seconds: Optional[int] = None
) -> Tuple[List, List, Dict]:
    """
    Execute a query with caching and deduplication.
    
    Flow:
    1. Check if caching is enabled
    2. Build cache key (tenant-scoped)
    3. Check cache for existing result
    4. If cache hit: return cached result
    5. If cache miss: execute query and cache result
    
    Deduplication:
    - If same query is in-flight, waits for result
    - Prevents thundering herd during BI refresh
    
    Args:
        execute_fn: Function that executes the actual query
        cache_components: Components for building cache key
        ttl_seconds: Optional override for cache TTL
    
    Returns:
        (columns, rows, stats) with cache metadata added to stats
    """
    config = get_cache_config()
    
    # Caching disabled - execute directly
    if not config.enabled:
        columns, rows, stats = execute_fn()
        stats["cacheEnabled"] = False
        return columns, rows, stats
    
    # Build cache key
    cache_key = build_cache_key(cache_components)
    short_key = get_short_key(cache_key)
    
    # Check cache
    cached = get_from_cache(cache_key)
    if cached:
        # Cache HIT
        columns = cached["columns"]
        rows = cached["rows"]
        stats = cached["stats"].copy()
        stats["cacheHit"] = True
        stats["cacheKey"] = short_key
        stats["cachedAt"] = cached.get("cachedAt")
        stats["deduplicated"] = False
        return columns, rows, stats
    
    # Cache MISS - execute query
    # Note: Deduplication is complex with sync execution
    # For MVP, we cache results but skip distributed deduplication
    # Full async deduplication requires refactoring to async handlers
    
    try:
        columns, rows, stats = execute_fn()
        
        # Cache successful result
        ttl = ttl_seconds or config.ttl_seconds
        cached_successfully = set_in_cache(cache_key, columns, rows, stats, ttl)
        
        # Add cache metadata to stats
        stats["cacheHit"] = False
        stats["cacheKey"] = short_key
        stats["cacheTTL"] = ttl if cached_successfully else 0
        stats["deduplicated"] = False
        
        return columns, rows, stats
        
    except Exception as e:
        # Don't cache errors
        raise


def build_cache_components_from_request(
    req: "QueryRequest",
    dataset: Dict,
    engine: str,
    tenant: str,
    role: str
) -> CacheKeyComponents:
    """
    Build cache key components from a query request.
    
    This helper extracts all relevant fields for cache key generation.
    """
    from app.models import QueryRequest
    
    # Get source ID if available
    source_id = dataset.get("source", {}).get("sourceId")
    
    # Normalize request fields
    dimensions = [
        {"name": d.name, "timeGrain": d.timeGrain, "alias": d.alias}
        for d in req.dimensions
    ]
    
    metrics = [
        {"name": m.name, "alias": m.alias}
        for m in req.metrics
    ]
    
    order_by = [
        {"field": o.field, "direction": o.direction, "nulls": o.nulls}
        for o in req.orderBy
    ]
    
    # Convert filters to dict
    filters_dict = None
    if req.filters:
        if hasattr(req.filters, 'model_dump'):
            filters_dict = req.filters.model_dump(by_alias=True, exclude_none=True)
        else:
            filters_dict = req.filters
    
    # Convert incremental values to strings
    inc_from = str(req.incrementalFrom) if req.incrementalFrom else None
    inc_to = str(req.incrementalTo) if req.incrementalTo else None
    
    return CacheKeyComponents(
        tenant=tenant,
        role=role,
        dataset=req.dataset,
        source_id=source_id,
        engine=engine,
        dimensions=dimensions,
        metrics=metrics,
        filters=filters_dict,
        order_by=order_by,
        limit=req.limit,
        offset=req.offset,
        incremental=req.incremental,
        incremental_from=inc_from,
        incremental_to=inc_to
    )


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

def clear_cache(pattern: str = "ubi:cache:*") -> int:
    """
    Clear cached entries matching pattern.
    
    Use with caution in production!
    
    Returns count of keys deleted.
    """
    redis_client = get_redis_client()
    if not redis_client:
        return 0
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache clear error: {e}")
    
    return 0


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    config = get_cache_config()
    redis_client = get_redis_client()
    
    stats = {
        "enabled": config.enabled,
        "redis_available": redis_client is not None,
        "ttl_seconds": config.ttl_seconds,
        "max_rows": config.max_rows
    }
    
    if redis_client:
        try:
            info = redis_client.info("memory")
            stats["redis_memory_used"] = info.get("used_memory_human")
            
            # Count cache keys
            keys = redis_client.keys("ubi:cache:*")
            stats["cached_queries"] = len(keys)
        except Exception as e:
            stats["error"] = str(e)
    
    return stats

