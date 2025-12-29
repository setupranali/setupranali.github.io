"""
DuckDB Adapter for SetuPranali

DuckDB is an embedded analytical database, perfect for:
- Local development and demos
- Testing without infrastructure
- Small to medium datasets (up to ~100GB)

Connection modes:
- In-memory (default): Fast, ephemeral
- File-based: Persistent, shareable
"""

import time
import logging
from typing import Any, Dict, List, Optional

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class DuckDBAdapter(BaseAdapter):
    """
    Adapter for DuckDB embedded database.
    
    Config options:
        database: Path to database file, or ":memory:" (default)
        read_only: Open in read-only mode (default: False)
    
    Example:
        adapter = DuckDBAdapter({"database": ":memory:"})
        adapter.connect()
        result = adapter.execute("SELECT 1 + 1 AS answer")
    """
    
    ENGINE = "duckdb"
    PLACEHOLDER = "?"  # DuckDB uses ? natively
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize DuckDB adapter."""
        super().__init__(config or {})
        
        if not DUCKDB_AVAILABLE:
            raise ConnectionError(
                "DuckDB not installed. Run: pip install duckdb",
                engine=self.ENGINE
            )
        
        self.database = self.config.get("database", ":memory:")
        self.read_only = self.config.get("read_only", False)
    
    def connect(self) -> None:
        """Connect to DuckDB database."""
        try:
            self._connection = duckdb.connect(
                database=self.database,
                read_only=self.read_only
            )
            self._connected = True
            logger.info(f"DuckDB connected: {self.database}")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to DuckDB: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close DuckDB connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing DuckDB connection: {e}")
            finally:
                self._connection = None
                self._connected = False
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on DuckDB.
        
        DuckDB returns results as a pandas DataFrame via fetchdf(),
        which we convert to list of dicts for consistency.
        """
        if not self._connected or not self._connection:
            raise QueryError(
                "Not connected to DuckDB",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        try:
            # Execute query
            result = self._connection.execute(sql, params or [])
            
            # Fetch as DataFrame and convert to records
            df = result.fetchdf()
            rows = df.to_dict(orient="records")
            columns = list(df.columns)
            
            # Get column types from DataFrame
            column_types = {
                col: str(df[col].dtype) for col in columns
            }
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=sql,
                metadata={"database": self.database}
            )
            
        except Exception as e:
            raise QueryError(
                f"DuckDB query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def health_check(self) -> bool:
        """Check DuckDB connection health."""
        if not self._connected or not self._connection:
            return False
        
        try:
            self._connection.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False
    
    def execute_script(self, script: str) -> None:
        """
        Execute multiple SQL statements (for setup/seeding).
        
        Useful for creating tables and inserting demo data.
        """
        if not self._connected or not self._connection:
            raise QueryError("Not connected to DuckDB", engine=self.ENGINE)
        
        try:
            self._connection.execute(script)
        except Exception as e:
            raise QueryError(
                f"DuckDB script execution failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )


# Singleton for shared in-memory instance (backward compatibility)
_shared_instance: Optional[DuckDBAdapter] = None


def get_shared_duckdb() -> DuckDBAdapter:
    """
    Get shared in-memory DuckDB instance.
    
    This provides backward compatibility with the existing
    DUCKDB_CONN global connection.
    """
    global _shared_instance
    
    if _shared_instance is None:
        _shared_instance = DuckDBAdapter({"database": ":memory:"})
        _shared_instance.connect()
    
    return _shared_instance


def reset_shared_duckdb() -> None:
    """Reset shared DuckDB instance (for testing)."""
    global _shared_instance
    
    if _shared_instance:
        _shared_instance.disconnect()
        _shared_instance = None

