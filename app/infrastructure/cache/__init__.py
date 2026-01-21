"""
Cache Infrastructure

Redis and in-memory caching implementations.
"""

# Backwards compatibility imports
from app.infrastructure.cache.redis_cache import (
    get_cache_config,
    get_cache_stats,
    execute_with_cache,
    build_cache_components_from_request
)

__all__ = [
    "get_cache_config",
    "get_cache_stats",
    "execute_with_cache",
    "build_cache_components_from_request"
]
