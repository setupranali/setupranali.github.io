"""
Multi-Region Deployment for SetuPranali

Geo-distributed caching and routing for global deployments.

Features:
- Region-aware request routing
- Distributed cache synchronization
- Data residency compliance
- Failover and health monitoring
- Latency-based routing
"""

import os
import time
import hashlib
import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class RegionStatus(str, Enum):
    """Region health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


@dataclass
class RegionConfig:
    """Configuration for a region."""
    region_id: str
    name: str
    endpoint: str
    cache_endpoint: Optional[str] = None
    database_endpoint: Optional[str] = None
    priority: int = 0  # Lower = higher priority
    weight: int = 100  # For weighted routing
    data_residency: List[str] = field(default_factory=list)  # Allowed countries
    is_primary: bool = False
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class RegionHealth:
    """Health status for a region."""
    region_id: str
    status: RegionStatus = RegionStatus.HEALTHY
    latency_ms: float = 0.0
    last_check: datetime = None
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    active_connections: int = 0
    consecutive_failures: int = 0


# =============================================================================
# Region Registry
# =============================================================================

class RegionRegistry:
    """Registry of available regions."""
    
    def __init__(self):
        self._regions: Dict[str, RegionConfig] = {}
        self._health: Dict[str, RegionHealth] = {}
        self._lock = threading.RLock()
    
    def register_region(self, config: RegionConfig) -> None:
        """Register a region."""
        with self._lock:
            self._regions[config.region_id] = config
            self._health[config.region_id] = RegionHealth(region_id=config.region_id)
    
    def unregister_region(self, region_id: str) -> None:
        """Unregister a region."""
        with self._lock:
            self._regions.pop(region_id, None)
            self._health.pop(region_id, None)
    
    def get_region(self, region_id: str) -> Optional[RegionConfig]:
        """Get region configuration."""
        return self._regions.get(region_id)
    
    def get_all_regions(self) -> List[RegionConfig]:
        """Get all registered regions."""
        return list(self._regions.values())
    
    def get_healthy_regions(self) -> List[RegionConfig]:
        """Get all healthy regions."""
        with self._lock:
            return [
                region for region in self._regions.values()
                if self._health.get(region.region_id, RegionHealth(region.region_id)).status == RegionStatus.HEALTHY
            ]
    
    def update_health(self, region_id: str, health: RegionHealth) -> None:
        """Update region health status."""
        with self._lock:
            self._health[region_id] = health
    
    def get_health(self, region_id: str) -> Optional[RegionHealth]:
        """Get region health status."""
        return self._health.get(region_id)
    
    def get_all_health(self) -> Dict[str, RegionHealth]:
        """Get health status for all regions."""
        return dict(self._health)


# =============================================================================
# Routing Strategies
# =============================================================================

class RoutingStrategy:
    """Base routing strategy."""
    
    def select_region(
        self,
        regions: List[RegionConfig],
        health: Dict[str, RegionHealth],
        context: Dict[str, Any]
    ) -> Optional[RegionConfig]:
        raise NotImplementedError


class PriorityRouting(RoutingStrategy):
    """Route to highest priority healthy region."""
    
    def select_region(
        self,
        regions: List[RegionConfig],
        health: Dict[str, RegionHealth],
        context: Dict[str, Any]
    ) -> Optional[RegionConfig]:
        healthy = [
            r for r in regions
            if health.get(r.region_id, RegionHealth(r.region_id)).status == RegionStatus.HEALTHY
        ]
        
        if not healthy:
            return None
        
        return min(healthy, key=lambda r: r.priority)


class LatencyRouting(RoutingStrategy):
    """Route to lowest latency region."""
    
    def select_region(
        self,
        regions: List[RegionConfig],
        health: Dict[str, RegionHealth],
        context: Dict[str, Any]
    ) -> Optional[RegionConfig]:
        healthy = [
            r for r in regions
            if health.get(r.region_id, RegionHealth(r.region_id)).status == RegionStatus.HEALTHY
        ]
        
        if not healthy:
            return None
        
        return min(
            healthy,
            key=lambda r: health.get(r.region_id, RegionHealth(r.region_id)).latency_ms
        )


class GeoRouting(RoutingStrategy):
    """Route to geographically closest region."""
    
    def select_region(
        self,
        regions: List[RegionConfig],
        health: Dict[str, RegionHealth],
        context: Dict[str, Any]
    ) -> Optional[RegionConfig]:
        healthy = [
            r for r in regions
            if health.get(r.region_id, RegionHealth(r.region_id)).status == RegionStatus.HEALTHY
        ]
        
        if not healthy:
            return None
        
        # Get client location from context
        client_lat = context.get("latitude", 0.0)
        client_lon = context.get("longitude", 0.0)
        
        if client_lat == 0.0 and client_lon == 0.0:
            # Fall back to priority routing
            return min(healthy, key=lambda r: r.priority)
        
        return min(
            healthy,
            key=lambda r: self._haversine_distance(
                client_lat, client_lon, r.latitude, r.longitude
            )
        )
    
    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate haversine distance between two points."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


class DataResidencyRouting(RoutingStrategy):
    """Route based on data residency requirements."""
    
    def select_region(
        self,
        regions: List[RegionConfig],
        health: Dict[str, RegionHealth],
        context: Dict[str, Any]
    ) -> Optional[RegionConfig]:
        required_country = context.get("country_code")
        
        # Filter by data residency
        if required_country:
            eligible = [
                r for r in regions
                if not r.data_residency or required_country in r.data_residency
            ]
        else:
            eligible = regions
        
        # Further filter by health
        healthy = [
            r for r in eligible
            if health.get(r.region_id, RegionHealth(r.region_id)).status == RegionStatus.HEALTHY
        ]
        
        if not healthy:
            return None
        
        return min(healthy, key=lambda r: r.priority)


class WeightedRouting(RoutingStrategy):
    """Route using weighted random selection."""
    
    def select_region(
        self,
        regions: List[RegionConfig],
        health: Dict[str, RegionHealth],
        context: Dict[str, Any]
    ) -> Optional[RegionConfig]:
        import random
        
        healthy = [
            r for r in regions
            if health.get(r.region_id, RegionHealth(r.region_id)).status == RegionStatus.HEALTHY
        ]
        
        if not healthy:
            return None
        
        total_weight = sum(r.weight for r in healthy)
        if total_weight == 0:
            return random.choice(healthy)
        
        rand = random.uniform(0, total_weight)
        cumulative = 0
        
        for region in healthy:
            cumulative += region.weight
            if rand <= cumulative:
                return region
        
        return healthy[-1]


# =============================================================================
# Distributed Cache
# =============================================================================

class DistributedCache:
    """Distributed cache with region awareness."""
    
    def __init__(self):
        self._local_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._region_caches: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self._lock = threading.RLock()
    
    def get(
        self,
        key: str,
        region_id: Optional[str] = None
    ) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            # Check local cache first
            if key in self._local_cache:
                value, expires = self._local_cache[key]
                if datetime.utcnow() < expires:
                    return value
                else:
                    del self._local_cache[key]
            
            # Check region-specific cache
            if region_id and key in self._region_caches.get(region_id, {}):
                return self._region_caches[region_id][key]
            
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        region_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set value in cache."""
        ttl = ttl_seconds or self._ttl_seconds
        expires = datetime.utcnow() + timedelta(seconds=ttl)
        
        with self._lock:
            self._local_cache[key] = (value, expires)
            
            if region_id:
                self._region_caches[region_id][key] = value
    
    def invalidate(
        self,
        key: str,
        region_id: Optional[str] = None,
        propagate: bool = True
    ) -> None:
        """Invalidate cache entry."""
        with self._lock:
            self._local_cache.pop(key, None)
            
            if region_id:
                self._region_caches.get(region_id, {}).pop(key, None)
            elif propagate:
                # Invalidate across all regions
                for cache in self._region_caches.values():
                    cache.pop(key, None)
    
    def invalidate_region(self, region_id: str) -> int:
        """Invalidate all cache for a region."""
        with self._lock:
            count = len(self._region_caches.get(region_id, {}))
            self._region_caches[region_id] = {}
            return count
    
    def sync_to_region(
        self,
        from_region: str,
        to_region: str,
        keys: Optional[List[str]] = None
    ) -> int:
        """Sync cache entries between regions."""
        with self._lock:
            source = self._region_caches.get(from_region, {})
            
            if keys:
                to_sync = {k: v for k, v in source.items() if k in keys}
            else:
                to_sync = source
            
            self._region_caches[to_region].update(to_sync)
            return len(to_sync)
    
    def get_stats(self, region_id: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            if region_id:
                return {
                    "region": region_id,
                    "entries": len(self._region_caches.get(region_id, {}))
                }
            
            return {
                "local_entries": len(self._local_cache),
                "regions": {
                    rid: len(cache)
                    for rid, cache in self._region_caches.items()
                }
            }


# =============================================================================
# Health Monitor
# =============================================================================

class HealthMonitor:
    """Monitor health of regions."""
    
    def __init__(
        self,
        registry: RegionRegistry,
        check_interval_seconds: int = 30
    ):
        self.registry = registry
        self.check_interval = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitor started")
    
    def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Health monitoring loop."""
        while self._running:
            try:
                for region in self.registry.get_all_regions():
                    health = self._check_region_health(region)
                    self.registry.update_health(region.region_id, health)
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_region_health(self, region: RegionConfig) -> RegionHealth:
        """Check health of a single region."""
        import httpx
        
        current = self.registry.get_health(region.region_id) or RegionHealth(region.region_id)
        
        try:
            start = time.time()
            
            # Simple health check
            response = httpx.get(
                f"{region.endpoint}/v1/health",
                timeout=5.0
            )
            
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return RegionHealth(
                    region_id=region.region_id,
                    status=RegionStatus.HEALTHY,
                    latency_ms=latency,
                    last_check=datetime.utcnow(),
                    error_rate=0.0,
                    consecutive_failures=0
                )
            else:
                return RegionHealth(
                    region_id=region.region_id,
                    status=RegionStatus.DEGRADED,
                    latency_ms=latency,
                    last_check=datetime.utcnow(),
                    consecutive_failures=current.consecutive_failures + 1
                )
                
        except Exception as e:
            failures = current.consecutive_failures + 1
            status = RegionStatus.UNHEALTHY if failures >= 3 else RegionStatus.DEGRADED
            
            return RegionHealth(
                region_id=region.region_id,
                status=status,
                latency_ms=float("inf"),
                last_check=datetime.utcnow(),
                consecutive_failures=failures
            )


# =============================================================================
# Multi-Region Service
# =============================================================================

class MultiRegionService:
    """Service for multi-region deployments."""
    
    STRATEGY_MAP = {
        "priority": PriorityRouting,
        "latency": LatencyRouting,
        "geo": GeoRouting,
        "residency": DataResidencyRouting,
        "weighted": WeightedRouting,
    }
    
    def __init__(self):
        self.registry = RegionRegistry()
        self.cache = DistributedCache()
        self.monitor = HealthMonitor(self.registry)
        self._strategy_name = os.getenv("ROUTING_STRATEGY", "priority")
        self._strategy = self.STRATEGY_MAP.get(
            self._strategy_name,
            PriorityRouting
        )()
    
    def start(self) -> None:
        """Start multi-region services."""
        self.monitor.start()
    
    def stop(self) -> None:
        """Stop multi-region services."""
        self.monitor.stop()
    
    def register_region(
        self,
        region_id: str,
        name: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Register a new region."""
        config = RegionConfig(
            region_id=region_id,
            name=name,
            endpoint=endpoint,
            **kwargs
        )
        
        self.registry.register_region(config)
        
        return {
            "status": "registered",
            "region_id": region_id
        }
    
    def unregister_region(self, region_id: str) -> Dict[str, Any]:
        """Unregister a region."""
        self.registry.unregister_region(region_id)
        self.cache.invalidate_region(region_id)
        
        return {
            "status": "unregistered",
            "region_id": region_id
        }
    
    def select_region(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select optimal region for request."""
        regions = self.registry.get_all_regions()
        health = self.registry.get_all_health()
        
        selected = self._strategy.select_region(regions, health, context)
        
        if not selected:
            return None
        
        region_health = health.get(selected.region_id, RegionHealth(selected.region_id))
        
        return {
            "region_id": selected.region_id,
            "name": selected.name,
            "endpoint": selected.endpoint,
            "latency_ms": region_health.latency_ms,
            "status": region_health.status.value
        }
    
    def get_regions(self) -> List[Dict[str, Any]]:
        """Get all regions with health status."""
        result = []
        
        for region in self.registry.get_all_regions():
            health = self.registry.get_health(region.region_id)
            
            result.append({
                "region_id": region.region_id,
                "name": region.name,
                "endpoint": region.endpoint,
                "priority": region.priority,
                "weight": region.weight,
                "is_primary": region.is_primary,
                "data_residency": region.data_residency,
                "status": health.status.value if health else "unknown",
                "latency_ms": health.latency_ms if health else None,
                "last_check": health.last_check.isoformat() if health and health.last_check else None
            })
        
        return result
    
    def get_region_health(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed health for a region."""
        health = self.registry.get_health(region_id)
        
        if not health:
            return None
        
        return {
            "region_id": health.region_id,
            "status": health.status.value,
            "latency_ms": health.latency_ms,
            "error_rate": health.error_rate,
            "cache_hit_rate": health.cache_hit_rate,
            "active_connections": health.active_connections,
            "consecutive_failures": health.consecutive_failures,
            "last_check": health.last_check.isoformat() if health.last_check else None
        }
    
    def set_routing_strategy(self, strategy: str) -> Dict[str, Any]:
        """Set routing strategy."""
        if strategy not in self.STRATEGY_MAP:
            return {
                "error": f"Unknown strategy: {strategy}",
                "available": list(self.STRATEGY_MAP.keys())
            }
        
        self._strategy_name = strategy
        self._strategy = self.STRATEGY_MAP[strategy]()
        
        return {
            "status": "updated",
            "strategy": strategy
        }
    
    def get_cache_stats(self, region_id: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats(region_id)
    
    def sync_cache(
        self,
        from_region: str,
        to_region: str,
        keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sync cache between regions."""
        count = self.cache.sync_to_region(from_region, to_region, keys)
        
        return {
            "status": "synced",
            "from_region": from_region,
            "to_region": to_region,
            "entries_synced": count
        }


# =============================================================================
# Global Service
# =============================================================================

_multi_region_service: Optional[MultiRegionService] = None


def get_multi_region_service() -> MultiRegionService:
    """Get multi-region service singleton."""
    global _multi_region_service
    if not _multi_region_service:
        _multi_region_service = MultiRegionService()
    return _multi_region_service

