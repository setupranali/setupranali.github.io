"""
Connection Manager for SetuPranali

This module provides a unified interface for getting database connections
across different engines. It bridges the old connection style with the
new adapter-based architecture.

MIGRATION PATH:
--------------
The original code used:
    engine, conn = get_engine_and_conn(dataset_source, sources_registry)
    
The new adapter-based approach:
    adapter = get_adapter_for_dataset(dataset, sources_registry)
    result = adapter.execute(sql, params)

For backward compatibility, both styles are supported.
"""

import logging
from typing import Any, Dict, Optional, Tuple, Union

# Import adapters
from app.adapters import get_adapter, get_adapter_for_source, list_adapters
from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError
from app.adapters.duckdb_adapter import get_shared_duckdb

logger = logging.getLogger(__name__)


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================
# These maintain compatibility with existing code that expects (engine, conn)

# Shared DuckDB connection (for demo mode)
DUCKDB_CONN = None


def _get_duckdb_conn():
    """Get shared DuckDB connection (lazy init)."""
    global DUCKDB_CONN
    if DUCKDB_CONN is None:
        adapter = get_shared_duckdb()
        DUCKDB_CONN = adapter._connection
    return DUCKDB_CONN


def get_engine_and_conn(
    dataset_source: dict,
    sources_registry: dict
) -> Tuple[str, Any]:
    """
    Get engine type and connection from dataset source.
    
    DEPRECATED: Use get_adapter_for_dataset() instead.
    
    This function maintains backward compatibility with the original
    query engine that expects (engine, conn) tuples.
    
    Args:
        dataset_source: The "source" block from dataset definition
        sources_registry: Dict of registered sources (from /v1/sources)
    
    Returns:
        (engine_name, connection_object) tuple
    
    Raises:
        ValueError: If source configuration is invalid
    """
    # Case 1: Explicit engine (inline source)
    if "engine" in dataset_source:
        engine = dataset_source["engine"].lower()
        
        if engine == "duckdb":
            return "duckdb", _get_duckdb_conn()
        
        # For other inline engines, create adapter
        config = dataset_source.get("config", {})
        adapter = get_adapter(engine, config)
        return engine, adapter
    
    # Case 2: Referenced source (via sourceId)
    if "sourceId" in dataset_source:
        source_id = dataset_source["sourceId"]
        
        if source_id not in sources_registry:
            raise ValueError(f"Unknown sourceId: {source_id}")
        
        source = sources_registry[source_id]
        engine = source.get("type", source.get("engine", "")).lower()
        
        if not engine:
            raise ValueError(f"Source {source_id} has no type/engine specified")
        
        adapter = get_adapter_for_source(source_id, sources_registry)
        return engine, adapter
    
    raise ValueError("Dataset source must have 'engine' or 'sourceId'")


# =============================================================================
# NEW ADAPTER-BASED API
# =============================================================================

def get_adapter_for_dataset(
    dataset: Dict[str, Any],
    sources_registry: Optional[Dict[str, Dict]] = None
) -> BaseAdapter:
    """
    Get the appropriate adapter for a dataset.
    
    This is the preferred way to get database connections.
    
    Args:
        dataset: Full dataset definition from catalog
        sources_registry: Dict of registered sources
    
    Returns:
        Connected adapter instance
    
    Example:
        adapter = get_adapter_for_dataset(dataset, sources)
        result = adapter.execute("SELECT * FROM orders WHERE id = ?", [123])
    """
    source = dataset.get("source", {})
    
    # Case 1: Explicit engine (inline)
    if "engine" in source:
        engine = source["engine"].lower()
        
        if engine == "duckdb":
            return get_shared_duckdb()
        
        config = source.get("config", {})
        return get_adapter(engine, config)
    
    # Case 2: Referenced source
    if "sourceId" in source:
        source_id = source["sourceId"]
        
        if not sources_registry:
            raise ConnectionError(
                f"Source registry required to resolve sourceId: {source_id}",
                engine="unknown"
            )
        
        return get_adapter_for_source(source_id, sources_registry)
    
    raise ConnectionError(
        "Dataset source must have 'engine' or 'sourceId'",
        engine="unknown"
    )


def execute_on_dataset(
    dataset: Dict[str, Any],
    sql: str,
    params: Optional[list] = None,
    sources_registry: Optional[Dict[str, Dict]] = None
) -> AdapterResult:
    """
    Execute SQL on the appropriate database for a dataset.
    
    Convenience function that gets adapter and executes in one call.
    
    Args:
        dataset: Dataset definition from catalog
        sql: SQL query with ? placeholders
        params: Query parameters
        sources_registry: Registered sources dict
    
    Returns:
        AdapterResult with rows and metadata
    """
    adapter = get_adapter_for_dataset(dataset, sources_registry)
    return adapter.execute(sql, params)


# =============================================================================
# SUPPORTED ENGINES
# =============================================================================

def get_supported_engines() -> list:
    """Get list of supported database engines."""
    return list_adapters()


def is_engine_supported(engine: str) -> bool:
    """Check if a database engine is supported."""
    return engine.lower() in [e.lower() for e in list_adapters()]


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_demo_data():
    """
    Initialize demo data in shared DuckDB instance.
    
    Creates sample 'orders' table for testing.
    """
    adapter = get_shared_duckdb()
    
    # Create orders table with multi-tenant demo data
    adapter.execute_script("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR,
            tenant_id VARCHAR,
            order_date DATE,
            city VARCHAR,
            revenue DOUBLE,
            qty INTEGER
        );
        
        DELETE FROM orders;
        
        INSERT INTO orders VALUES
            ('ORD001', 'tenantA', '2025-12-01', 'Bhopal', 500, 10),
            ('ORD002', 'tenantB', '2025-12-02', 'Indore', 250, 5),
            ('ORD003', 'tenantA', '2025-12-02', 'Mumbai', 800, 15),
            ('ORD004', 'tenantA', '2025-12-01', 'Indore', 1000, 20),
            ('ORD005', 'tenantB', '2025-12-03', 'Delhi', 1200, 25),
            ('ORD006', 'tenantC', '2025-12-03', 'Chennai', 600, 12);
    """)
    
    logger.info("Demo data initialized in DuckDB")


# Initialize demo data on import (if DuckDB available)
try:
    init_demo_data()
except Exception as e:
    logger.warning(f"Could not initialize demo data: {e}")
