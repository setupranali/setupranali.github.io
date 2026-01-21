"""
Database Adapters

Database-specific adapter implementations.
"""

# Re-export all adapters for backwards compatibility
from app.infrastructure.adapters.base import BaseAdapter, AdapterResult
from app.infrastructure.adapters.factory import get_adapter, is_engine_supported
from app.infrastructure.adapters.duckdb_adapter import get_shared_duckdb

__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "get_adapter",
    "is_engine_supported",
    "get_shared_duckdb"
]
