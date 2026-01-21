"""
SQLite Adapter for SetuPranali

SQLite is ideal for:
- Local development and testing
- Single-file embedded databases
- Edge computing and IoT
- Mobile and desktop applications
- Quick prototyping

Features:
- Zero configuration (built into Python)
- In-memory databases
- Read-only mode for safety
- WAL mode for concurrent reads
- Full-text search support

Requirements:
    None - sqlite3 is included in Python standard library
"""

import os
import time
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from app.infrastructure.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class SQLiteAdapter(BaseAdapter):
    """
    Adapter for SQLite databases.
    
    Supports file-based and in-memory SQLite databases.
    
    Config options:
        database: Path to SQLite file or ':memory:' (required)
        read_only: Open in read-only mode (default: True)
        timeout: Connection timeout in seconds (default: 30)
        isolation_level: Transaction isolation (default: None for autocommit)
        check_same_thread: Allow multi-threaded access (default: False)
        journal_mode: WAL, DELETE, TRUNCATE, etc. (default: WAL for files)
        cache_size: Page cache size in KB (default: 2000)
        foreign_keys: Enable foreign key constraints (default: True)
        
    Example (File):
        adapter = SQLiteAdapter({
            "database": "/path/to/data.db"
        })
        
    Example (In-Memory):
        adapter = SQLiteAdapter({
            "database": ":memory:"
        })
        
    Example (Read-Write):
        adapter = SQLiteAdapter({
            "database": "/path/to/data.db",
            "read_only": False
        })
    """
    
    ENGINE = "sqlite"
    PLACEHOLDER = "?"  # SQLite uses ? for parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SQLite adapter."""
        super().__init__(config)
        
        # Validate required config
        if "database" not in config:
            raise ConnectionError(
                "Missing required config: database",
                engine=self.ENGINE
            )
        
        # Database path
        self.database = config["database"]
        self.is_memory = self.database == ":memory:"
        
        # Validate file exists (unless in-memory or creating new)
        if not self.is_memory and not config.get("create", False):
            if not os.path.exists(self.database):
                raise ConnectionError(
                    f"Database file not found: {self.database}",
                    engine=self.ENGINE
                )
        
        # Connection options
        self.read_only = config.get("read_only", True)
        self.timeout = config.get("timeout", 30.0)
        self.isolation_level = config.get("isolation_level", None)
        self.check_same_thread = config.get("check_same_thread", False)
        
        # Performance options
        self.journal_mode = config.get("journal_mode", "WAL" if not self.is_memory else None)
        self.cache_size = config.get("cache_size", 2000)
        self.foreign_keys = config.get("foreign_keys", True)
        
        # Extensions
        self.extensions = config.get("extensions", [])
    
    def _get_uri(self) -> str:
        """Build SQLite URI for connection."""
        if self.is_memory:
            # Shared in-memory database
            return "file::memory:?cache=shared"
        
        # File-based database
        path = Path(self.database).absolute()
        uri = f"file:{path}"
        
        if self.read_only:
            uri += "?mode=ro"
        
        return uri
    
    def connect(self) -> None:
        """Connect to SQLite database."""
        try:
            # Build connection
            if self.read_only and not self.is_memory:
                # Use URI for read-only mode
                self._connection = sqlite3.connect(
                    self._get_uri(),
                    uri=True,
                    timeout=self.timeout,
                    isolation_level=self.isolation_level,
                    check_same_thread=self.check_same_thread,
                )
            else:
                self._connection = sqlite3.connect(
                    self.database,
                    timeout=self.timeout,
                    isolation_level=self.isolation_level,
                    check_same_thread=self.check_same_thread,
                )
            
            # Enable row factory for dict-like access
            self._connection.row_factory = sqlite3.Row
            
            # Configure database
            cursor = self._connection.cursor()
            
            # Set journal mode (for file-based DBs)
            if self.journal_mode and not self.is_memory:
                cursor.execute(f"PRAGMA journal_mode = {self.journal_mode}")
            
            # Set cache size
            cursor.execute(f"PRAGMA cache_size = -{self.cache_size}")  # Negative = KB
            
            # Enable foreign keys
            if self.foreign_keys:
                cursor.execute("PRAGMA foreign_keys = ON")
            
            # Load extensions if any
            if self.extensions:
                self._connection.enable_load_extension(True)
                for ext in self.extensions:
                    self._connection.load_extension(ext)
            
            cursor.close()
            
            # Test connection
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            self._connected = True
            logger.info(f"SQLite connected: {self.database}")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to SQLite: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close SQLite connection."""
        try:
            if self._connection:
                self._connection.close()
                self._connection = None
        except Exception as e:
            logger.warning(f"Error closing SQLite connection: {e}")
        finally:
            self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert placeholders for SQLite.
        
        SQLite uses ? for positional parameters (same as our format).
        """
        return sql, params or []
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on SQLite.
        """
        if not self._connected:
            raise QueryError(
                "Not connected to SQLite",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        cursor = None
        
        try:
            cursor = self._connection.cursor()
            
            # Execute query
            if params:
                cursor.execute(sql, tuple(params))
            else:
                cursor.execute(sql)
            
            # Fetch results
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = cursor.fetchall() if cursor.description else []
            
            # Convert sqlite3.Row to dict
            rows = [dict(row) for row in data]
            
            # SQLite doesn't provide type info in description
            column_types = {col: "text" for col in columns}
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=sql,
                metadata={
                    "database": self.database,
                    "read_only": self.read_only,
                    "journal_mode": self.journal_mode
                }
            )
            
        except Exception as e:
            raise QueryError(
                f"SQLite query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def health_check(self) -> bool:
        """Check SQLite connection health."""
        if not self._connected:
            return False
        
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def get_tables(self) -> List[str]:
        """Get list of tables in the database."""
        if not self._connected:
            return []
        
        result = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row.get("name", "") for row in result.rows]
    
    def get_views(self) -> List[str]:
        """Get list of views in the database."""
        if not self._connected:
            return []
        
        result = self.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        )
        return [row.get("name", "") for row in result.rows]
    
    def get_columns(self, table: str) -> List[Dict[str, Any]]:
        """Get columns for a table."""
        if not self._connected:
            return []
        
        result = self.execute(f"PRAGMA table_info('{table}')")
        return [
            {
                "name": row.get("name", ""),
                "type": row.get("type", ""),
                "nullable": not row.get("notnull", 0),
                "default": row.get("dflt_value"),
                "primary_key": bool(row.get("pk", 0))
            }
            for row in result.rows
        ]
    
    def get_indexes(self, table: str) -> List[Dict[str, Any]]:
        """Get indexes for a table."""
        if not self._connected:
            return []
        
        result = self.execute(f"PRAGMA index_list('{table}')")
        return result.rows
    
    def get_version(self) -> str:
        """Get SQLite version."""
        if not self._connected:
            return ""
        
        result = self.execute("SELECT sqlite_version() as version")
        if result.rows:
            return result.rows[0].get("version", "")
        return ""
    
    def get_db_size(self) -> int:
        """Get database file size in bytes."""
        if self.is_memory:
            # Approximate size for in-memory
            result = self.execute("PRAGMA page_count")
            page_count = result.rows[0].get("page_count", 0) if result.rows else 0
            result = self.execute("PRAGMA page_size")
            page_size = result.rows[0].get("page_size", 4096) if result.rows else 4096
            return page_count * page_size
        else:
            return os.path.getsize(self.database) if os.path.exists(self.database) else 0
    
    def vacuum(self) -> None:
        """Compact the database file."""
        if not self._connected or self.read_only:
            return
        
        cursor = self._connection.cursor()
        cursor.execute("VACUUM")
        cursor.close()
    
    def analyze(self) -> None:
        """Update query optimizer statistics."""
        if not self._connected or self.read_only:
            return
        
        cursor = self._connection.cursor()
        cursor.execute("ANALYZE")
        cursor.close()


# Aliases
SQLite3Adapter = SQLiteAdapter

