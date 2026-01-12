"""
Adapter Factory for SetuPranali

Provides a unified interface for getting database adapters.
Handles adapter registration, caching, and lifecycle management.

Usage:
    from app.adapters import get_adapter
    
    # Get adapter for a source
    adapter = get_adapter("snowflake", config)
    
    # Or use with source registry
    adapter = get_adapter_for_source(source_id, sources_registry)
"""

import logging
from typing import Any, Dict, Optional, Type, List

from app.adapters.base import BaseAdapter, ConnectionError

logger = logging.getLogger(__name__)


# =============================================================================
# ADAPTER REGISTRY
# =============================================================================

# Map of engine name -> adapter class
_ADAPTER_REGISTRY: Dict[str, Type[BaseAdapter]] = {}

# Cache of active adapter instances (keyed by source_id or config hash)
_ADAPTER_CACHE: Dict[str, BaseAdapter] = {}


def register_adapter(engine: str, adapter_class: Type[BaseAdapter]) -> None:
    """
    Register an adapter class for an engine.
    
    Args:
        engine: Engine identifier (e.g., "snowflake", "postgres")
        adapter_class: Adapter class to use for this engine
    """
    _ADAPTER_REGISTRY[engine.lower()] = adapter_class
    logger.info(f"Registered adapter for engine: {engine}")


def list_adapters() -> List[str]:
    """Get list of registered adapter engines."""
    return list(_ADAPTER_REGISTRY.keys())


def is_engine_supported(engine: str) -> bool:
    """Check if an engine has a registered adapter."""
    return engine.lower() in _ADAPTER_REGISTRY


# =============================================================================
# ADAPTER FACTORY
# =============================================================================

def get_adapter(
    engine: str,
    config: Dict[str, Any],
    source_id: Optional[str] = None,
    use_cache: bool = True
) -> BaseAdapter:
    """
    Get an adapter instance for the specified engine.
    
    Args:
        engine: Database engine name (e.g., "snowflake", "postgres", "duckdb")
        config: Connection configuration dict
        source_id: Optional source ID for caching
        use_cache: Whether to use cached adapter (default: True)
    
    Returns:
        Connected adapter instance
    
    Raises:
        ConnectionError: If engine not supported or connection fails
    
    Example:
        adapter = get_adapter("snowflake", {
            "account": "xy12345.us-east-1",
            "user": "bi_service",
            "password": "***",
            "warehouse": "BI_WH",
            "database": "ANALYTICS"
        })
        
        result = adapter.execute("SELECT * FROM orders LIMIT 10")
    """
    engine_lower = engine.lower()
    
    # Check if engine is supported
    if engine_lower not in _ADAPTER_REGISTRY:
        available = ", ".join(list_adapters())
        raise ConnectionError(
            f"Unsupported engine: {engine}. Available: {available}",
            engine=engine
        )
    
    # Generate cache key
    cache_key = source_id or _generate_config_hash(engine, config)
    
    # Check cache
    if use_cache and cache_key in _ADAPTER_CACHE:
        adapter = _ADAPTER_CACHE[cache_key]
        if adapter.health_check():
            logger.debug(f"Using cached adapter for {engine} ({cache_key})")
            return adapter
        else:
            # Cached adapter unhealthy - remove and create new
            logger.warning(f"Cached adapter unhealthy, reconnecting: {cache_key}")
            try:
                adapter.disconnect()
            except Exception:
                pass
            del _ADAPTER_CACHE[cache_key]
    
    # Create new adapter
    adapter_class = _ADAPTER_REGISTRY[engine_lower]
    adapter = adapter_class(config)
    
    # Connect
    adapter.connect()
    
    # Cache if requested
    if use_cache:
        _ADAPTER_CACHE[cache_key] = adapter
    
    return adapter


def get_adapter_for_source(
    source_id: str,
    sources_registry: Dict[str, Dict[str, Any]]
) -> BaseAdapter:
    """
    Get an adapter for a registered source.
    
    Args:
        source_id: Source ID from sources registry
        sources_registry: Dict of source_id -> source config
    
    Returns:
        Connected adapter instance
    
    Raises:
        ConnectionError: If source not found or connection fails
    """
    if source_id not in sources_registry:
        raise ConnectionError(
            f"Unknown source: {source_id}",
            engine="unknown"
        )
    
    source = sources_registry[source_id]
    engine = source.get("type") or source.get("engine")
    config = source.get("config", {})
    
    if not engine:
        raise ConnectionError(
            f"Source {source_id} has no engine/type specified",
            engine="unknown"
        )
    
    return get_adapter(engine, config, source_id=source_id)


def close_adapter(source_id: str) -> bool:
    """
    Close and remove a cached adapter.
    
    Args:
        source_id: Source ID or cache key
    
    Returns:
        True if adapter was found and closed
    """
    if source_id in _ADAPTER_CACHE:
        adapter = _ADAPTER_CACHE[source_id]
        try:
            adapter.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting adapter: {e}")
        del _ADAPTER_CACHE[source_id]
        return True
    return False


def close_all_adapters() -> int:
    """
    Close all cached adapters.
    
    Returns:
        Number of adapters closed
    """
    count = 0
    for key in list(_ADAPTER_CACHE.keys()):
        if close_adapter(key):
            count += 1
    return count


def _generate_config_hash(engine: str, config: Dict[str, Any]) -> str:
    """Generate a hash for adapter config (for caching)."""
    import hashlib
    import json
    
    # Create stable string from config (exclude password for safety in logs)
    safe_config = {k: v for k, v in config.items() if k != "password"}
    config_str = f"{engine}:{json.dumps(safe_config, sort_keys=True)}"
    
    return hashlib.md5(config_str.encode()).hexdigest()[:12]


# =============================================================================
# AUTO-REGISTER BUILT-IN ADAPTERS
# =============================================================================

def _register_builtin_adapters():
    """Register all built-in adapters."""
    
    # DuckDB
    try:
        from app.adapters.duckdb_adapter import DuckDBAdapter
        register_adapter("duckdb", DuckDBAdapter)
    except ImportError as e:
        logger.debug(f"DuckDB adapter not available: {e}")
    
    # PostgreSQL
    try:
        from app.adapters.postgres_adapter import PostgresAdapter
        register_adapter("postgres", PostgresAdapter)
        register_adapter("postgresql", PostgresAdapter)  # Alias
    except ImportError as e:
        logger.debug(f"PostgreSQL adapter not available: {e}")
    
    # Snowflake
    try:
        from app.adapters.snowflake_adapter import SnowflakeAdapter
        register_adapter("snowflake", SnowflakeAdapter)
    except ImportError as e:
        logger.debug(f"Snowflake adapter not available: {e}")
    
    # BigQuery
    try:
        from app.adapters.bigquery_adapter import BigQueryAdapter
        register_adapter("bigquery", BigQueryAdapter)
        register_adapter("bq", BigQueryAdapter)  # Alias
    except ImportError as e:
        logger.debug(f"BigQuery adapter not available: {e}")
    
    # Databricks
    try:
        from app.adapters.databricks_adapter import DatabricksAdapter
        register_adapter("databricks", DatabricksAdapter)
        register_adapter("dbx", DatabricksAdapter)  # Alias
    except ImportError as e:
        logger.debug(f"Databricks adapter not available: {e}")
    
    # ClickHouse
    try:
        from app.adapters.clickhouse_adapter import ClickHouseAdapter
        register_adapter("clickhouse", ClickHouseAdapter)
        register_adapter("ch", ClickHouseAdapter)  # Alias
    except ImportError as e:
        logger.debug(f"ClickHouse adapter not available: {e}")
    
    # Redshift
    try:
        from app.adapters.redshift_adapter import RedshiftAdapter
        register_adapter("redshift", RedshiftAdapter)
        register_adapter("rs", RedshiftAdapter)  # Alias
    except ImportError as e:
        logger.debug(f"Redshift adapter not available: {e}")
    
    # MySQL
    try:
        from app.adapters.mysql_adapter import MySQLAdapter
        register_adapter("mysql", MySQLAdapter)
        register_adapter("mariadb", MySQLAdapter)  # MariaDB compatible
        register_adapter("starrocks", MySQLAdapter)  # StarRocks uses MySQL protocol
        register_adapter("doris", MySQLAdapter)  # Apache Doris uses MySQL protocol
    except ImportError as e:
        logger.debug(f"MySQL adapter not available: {e}")
    
    # Trino / Presto
    try:
        from app.adapters.trino_adapter import TrinoAdapter, PrestoAdapter
        register_adapter("trino", TrinoAdapter)
        register_adapter("presto", PrestoAdapter)  # Alias for Presto mode
        register_adapter("prestodb", PrestoAdapter)  # Another alias
    except ImportError as e:
        logger.debug(f"Trino/Presto adapter not available: {e}")
    
    # SQL Server / Azure SQL
    try:
        from app.adapters.sqlserver_adapter import SQLServerAdapter, MSSQLAdapter, AzureSQLAdapter
        register_adapter("sqlserver", SQLServerAdapter)
        register_adapter("mssql", MSSQLAdapter)  # Alias
        register_adapter("azuresql", AzureSQLAdapter)  # Azure SQL alias
        register_adapter("azure-sql", AzureSQLAdapter)  # Another Azure alias
    except ImportError as e:
        logger.debug(f"SQL Server adapter not available: {e}")
    
    # Oracle Database / Oracle Cloud
    try:
        from app.adapters.oracle_adapter import OracleAdapter, OracleDBAdapter, OCIAdapter, ATPAdapter, ADWAdapter
        register_adapter("oracle", OracleAdapter)
        register_adapter("oracledb", OracleDBAdapter)  # Alias
        register_adapter("oci", OCIAdapter)  # Oracle Cloud Infrastructure
        register_adapter("atp", ATPAdapter)  # Autonomous Transaction Processing
        register_adapter("adw", ADWAdapter)  # Autonomous Data Warehouse
    except ImportError as e:
        logger.debug(f"Oracle adapter not available: {e}")
    
    # SQLite (built-in, no dependencies)
    try:
        from app.adapters.sqlite_adapter import SQLiteAdapter, SQLite3Adapter
        register_adapter("sqlite", SQLiteAdapter)
        register_adapter("sqlite3", SQLite3Adapter)  # Alias
    except ImportError as e:
        logger.debug(f"SQLite adapter not available: {e}")
    
    # TimescaleDB (PostgreSQL extension for time-series)
    try:
        from app.adapters.timescaledb_adapter import TimescaleDBAdapter, TSDBAdapter, TimeScaleAdapter
        register_adapter("timescaledb", TimescaleDBAdapter)
        register_adapter("timescale", TimescaleDBAdapter)  # Alias
        register_adapter("tsdb", TSDBAdapter)  # Short alias
    except ImportError as e:
        logger.debug(f"TimescaleDB adapter not available: {e}")
    
    # CockroachDB (distributed SQL)
    try:
        from app.adapters.cockroachdb_adapter import CockroachDBAdapter, CRDBAdapter, RoachAdapter
        register_adapter("cockroachdb", CockroachDBAdapter)
        register_adapter("cockroach", CockroachDBAdapter)  # Alias
        register_adapter("crdb", CRDBAdapter)  # Short alias
    except ImportError as e:
        logger.debug(f"CockroachDB adapter not available: {e}")


# Register on module load
_register_builtin_adapters()


# =============================================================================
# STATUS / HEALTH
# =============================================================================

def get_adapters_status() -> Dict[str, Any]:
    """Get status of all registered and cached adapters."""
    return {
        "registered_engines": list_adapters(),
        "cached_adapters": {
            key: adapter.get_engine_info()
            for key, adapter in _ADAPTER_CACHE.items()
        },
        "cache_count": len(_ADAPTER_CACHE)
    }

