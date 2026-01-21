"""
Sources Domain

Data source management and catalog handling.
"""

from app.domain.sources.manager import (
    register_source,
    list_sources,
    get_source,
    get_source_with_config,
    delete_source,
    update_source,
    init_database as init_sources_db,
    SOURCES
)
from app.domain.sources.catalog import load_catalog, get_dataset

__all__ = [
    "register_source",
    "list_sources",
    "get_source",
    "get_source_with_config",
    "delete_source",
    "update_source",
    "init_sources_db",
    "SOURCES",
    "load_catalog",
    "get_dataset"
]
