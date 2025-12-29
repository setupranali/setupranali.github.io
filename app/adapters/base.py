"""
Base Adapter Interface for SetuPranali

All database adapters must implement this interface to ensure consistent
behavior across different database engines.

DESIGN PRINCIPLES:
-----------------
1. Connection pooling handled by adapter (not caller)
2. Query parameters use ? placeholders (adapter converts as needed)
3. Results returned as list of dicts (engine-agnostic)
4. Errors wrapped in AdapterError for consistent handling
5. Adapters are stateless - connection config passed on init
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AdapterError(Exception):
    """Base exception for adapter errors."""
    
    def __init__(self, message: str, engine: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.engine = engine
        self.original_error = original_error


class ConnectionError(AdapterError):
    """Failed to connect to database."""
    pass


class QueryError(AdapterError):
    """Query execution failed."""
    pass


@dataclass
class AdapterResult:
    """
    Standardized result from query execution.
    
    Attributes:
        rows: List of result rows as dicts
        columns: List of column names
        column_types: Optional mapping of column name to type
        row_count: Number of rows returned
        execution_time_ms: Query execution time in milliseconds
        engine: Database engine name
        sql: Executed SQL (with placeholders, not values)
        metadata: Additional engine-specific metadata
    """
    rows: List[Dict[str, Any]]
    columns: List[str]
    column_types: Dict[str, str] = field(default_factory=dict)
    row_count: int = 0
    execution_time_ms: float = 0.0
    engine: str = ""
    sql: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.row_count = len(self.rows)


class BaseAdapter(ABC):
    """
    Abstract base class for database adapters.
    
    Each adapter must implement:
    - connect(): Establish database connection
    - disconnect(): Close connection
    - execute(): Run a query with parameters
    - health_check(): Verify connection is alive
    - convert_placeholders(): Convert ? to engine-specific format
    
    Usage:
        adapter = SnowflakeAdapter(config)
        adapter.connect()
        
        result = adapter.execute(
            sql="SELECT * FROM orders WHERE tenant_id = ?",
            params=["tenant_a"]
        )
        
        adapter.disconnect()
    """
    
    # Engine identifier (e.g., "snowflake", "postgres", "duckdb")
    ENGINE: str = "base"
    
    # Placeholder format used by this engine
    PLACEHOLDER: str = "?"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with connection configuration.
        
        Args:
            config: Database-specific configuration dict
                    (host, port, user, password, database, etc.)
        """
        self.config = config
        self._connection = None
        self._connected = False
        self._last_used = None
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to database.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Close database connection.
        
        Should be safe to call even if not connected.
        """
        pass
    
    @abstractmethod
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query and return results.
        
        Args:
            sql: SQL query with ? placeholders for parameters
            params: List of parameter values (order matches ? positions)
        
        Returns:
            AdapterResult with rows, columns, and metadata
        
        Raises:
            QueryError: If query execution fails
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if connection is alive and usable.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        pass
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[Any]]:
        """
        Convert ? placeholders to engine-specific format.
        
        Default implementation returns sql unchanged.
        Override in adapters that need different placeholder formats:
        - PostgreSQL: %s
        - Snowflake: %s (via format string) or :1, :2 (positional)
        - BigQuery: @param1, @param2 (named)
        
        Args:
            sql: SQL with ? placeholders
            params: Parameter values
        
        Returns:
            (converted_sql, params)
        """
        return sql, params or []
    
    def is_connected(self) -> bool:
        """Check if adapter has an active connection."""
        return self._connected
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about this adapter/engine."""
        return {
            "engine": self.ENGINE,
            "connected": self._connected,
            "placeholder": self.PLACEHOLDER,
            "last_used": self._last_used.isoformat() if self._last_used else None
        }
    
    def _update_last_used(self):
        """Update last used timestamp."""
        self._last_used = datetime.now(timezone.utc)
    
    def __enter__(self):
        """Context manager support."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.disconnect()
        return False

