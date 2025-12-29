"""
Database Adapters for SetuPranali

This package provides a unified interface for connecting to different databases.
Each adapter handles:
- Connection management
- Query execution
- Parameter placeholder conversion
- Result formatting

Supported Engines:
- DuckDB (built-in, for demos)
- PostgreSQL
- MySQL / MariaDB
- Snowflake (TB-scale)
- BigQuery
- Databricks
- Redshift
- ClickHouse
- Trino / Presto (federated queries)
- SQL Server / Azure SQL
- Oracle Database / Oracle Cloud (ATP/ADW)
- SQLite (built-in, zero dependencies)
- TimescaleDB (time-series on PostgreSQL)
- CockroachDB (distributed SQL)
"""

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError
from app.adapters.factory import (
    get_adapter,
    get_adapter_for_source,
    register_adapter,
    list_adapters,
    close_adapter,
    close_all_adapters,
    get_adapters_status
)

__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "ConnectionError",
    "QueryError",
    "get_adapter",
    "get_adapter_for_source",
    "register_adapter",
    "list_adapters",
    "close_adapter",
    "close_all_adapters",
    "get_adapters_status"
]

