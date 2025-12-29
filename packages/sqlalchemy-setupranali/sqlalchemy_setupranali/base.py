"""
DBAPI 2.0 compatible interface for SetuPranali

This module implements a PEP 249 (DB-API 2.0) compatible interface
for connecting to SetuPranali via HTTP/HTTPS.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

# DB-API 2.0 globals
apilevel = "2.0"
threadsafety = 2  # Connections may be shared between threads
paramstyle = "qmark"  # Question mark style: WHERE name=?


class Error(Exception):
    """Base exception for DB-API errors."""
    pass


class Warning(Exception):
    """Exception raised for warnings."""
    pass


class InterfaceError(Error):
    """Exception for interface errors."""
    pass


class DatabaseError(Error):
    """Exception for database errors."""
    pass


class DataError(DatabaseError):
    """Exception for data errors."""
    pass


class OperationalError(DatabaseError):
    """Exception for operational errors."""
    pass


class IntegrityError(DatabaseError):
    """Exception for integrity errors."""
    pass


class InternalError(DatabaseError):
    """Exception for internal errors."""
    pass


class ProgrammingError(DatabaseError):
    """Exception for programming errors."""
    pass


class NotSupportedError(DatabaseError):
    """Exception for unsupported operations."""
    pass


class SetuPranaliCursor:
    """
    DB-API 2.0 Cursor implementation for SetuPranali.
    """
    
    def __init__(self, connection: "SetuPranaliConnection"):
        self.connection = connection
        self.description: Optional[List[Tuple]] = None
        self.rowcount: int = -1
        self.arraysize: int = 1
        self._results: List[Dict[str, Any]] = []
        self._position: int = 0
        self._closed: bool = False
    
    def close(self) -> None:
        """Close the cursor."""
        self._closed = True
        self._results = []
        self.description = None
    
    def execute(
        self,
        operation: str,
        parameters: Optional[Union[Tuple, Dict]] = None
    ) -> "SetuPranaliCursor":
        """
        Execute a SQL query.
        
        Args:
            operation: SQL query string
            parameters: Query parameters (optional)
        
        Returns:
            Self for chaining
        """
        if self._closed:
            raise ProgrammingError("Cursor is closed")
        
        # Substitute parameters
        sql = self._substitute_parameters(operation, parameters)
        
        # Execute via connection
        result = self.connection._execute_sql(sql)
        
        # Process results
        self._results = result.get("rows", [])
        self.rowcount = len(self._results)
        self._position = 0
        
        # Build description from columns
        columns = result.get("columns", [])
        column_types = result.get("column_types", {})
        
        if columns:
            self.description = [
                (
                    col,  # name
                    self._map_type(column_types.get(col, "string")),  # type_code
                    None,  # display_size
                    None,  # internal_size
                    None,  # precision
                    None,  # scale
                    True,  # null_ok
                )
                for col in columns
            ]
        else:
            self.description = None
        
        return self
    
    def executemany(
        self,
        operation: str,
        seq_of_parameters: List[Union[Tuple, Dict]]
    ) -> "SetuPranaliCursor":
        """Execute a query with multiple parameter sets."""
        for parameters in seq_of_parameters:
            self.execute(operation, parameters)
        return self
    
    def fetchone(self) -> Optional[Tuple]:
        """Fetch the next row."""
        if self._closed:
            raise ProgrammingError("Cursor is closed")
        
        if self._position >= len(self._results):
            return None
        
        row = self._results[self._position]
        self._position += 1
        
        # Convert dict to tuple in column order
        if self.description:
            return tuple(row.get(desc[0]) for desc in self.description)
        return tuple(row.values())
    
    def fetchmany(self, size: Optional[int] = None) -> List[Tuple]:
        """Fetch multiple rows."""
        if size is None:
            size = self.arraysize
        
        rows = []
        for _ in range(size):
            row = self.fetchone()
            if row is None:
                break
            rows.append(row)
        return rows
    
    def fetchall(self) -> List[Tuple]:
        """Fetch all remaining rows."""
        rows = []
        while True:
            row = self.fetchone()
            if row is None:
                break
            rows.append(row)
        return rows
    
    def setinputsizes(self, sizes: List) -> None:
        """Set input sizes (no-op for SetuPranali)."""
        pass
    
    def setoutputsize(self, size: int, column: Optional[int] = None) -> None:
        """Set output size (no-op for SetuPranali)."""
        pass
    
    def _substitute_parameters(
        self,
        sql: str,
        parameters: Optional[Union[Tuple, Dict]]
    ) -> str:
        """Substitute parameters in SQL query."""
        if parameters is None:
            return sql
        
        if isinstance(parameters, dict):
            # Named parameters
            for key, value in parameters.items():
                placeholder = f":{key}"
                sql = sql.replace(placeholder, self._format_value(value))
        else:
            # Positional parameters
            for value in parameters:
                sql = sql.replace("?", self._format_value(value), 1)
        
        return sql
    
    def _format_value(self, value: Any) -> str:
        """Format a value for SQL."""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
    
    def _map_type(self, type_name: str) -> str:
        """Map SetuPranali type to DB-API type."""
        type_map = {
            "string": "STRING",
            "varchar": "STRING",
            "text": "STRING",
            "number": "NUMBER",
            "integer": "NUMBER",
            "int": "NUMBER",
            "bigint": "NUMBER",
            "float": "NUMBER",
            "double": "NUMBER",
            "decimal": "NUMBER",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "timestamp": "DATETIME",
            "datetime": "DATETIME",
        }
        return type_map.get(type_name.lower(), "STRING")
    
    def __iter__(self):
        """Make cursor iterable."""
        return self
    
    def __next__(self):
        """Get next row."""
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class SetuPranaliConnection:
    """
    DB-API 2.0 Connection implementation for SetuPranali.
    """
    
    def __init__(
        self,
        host: str,
        port: int = 8080,
        api_key: str = "",
        scheme: str = "http",
        database: str = "",
        timeout: int = 30,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.scheme = scheme
        self.database = database  # Default dataset for RLS context
        self.timeout = timeout
        self._closed = False
        
        # Build base URL
        self.base_url = f"{scheme}://{host}"
        if port and port not in (80, 443):
            self.base_url += f":{port}"
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        })
    
    def close(self) -> None:
        """Close the connection."""
        self._closed = True
        self.session.close()
    
    def commit(self) -> None:
        """Commit transaction (no-op for read-only SetuPranali)."""
        pass
    
    def rollback(self) -> None:
        """Rollback transaction (no-op for read-only SetuPranali)."""
        pass
    
    def cursor(self) -> SetuPranaliCursor:
        """Create a new cursor."""
        if self._closed:
            raise ProgrammingError("Connection is closed")
        return SetuPranaliCursor(self)
    
    def _execute_sql(self, sql: str) -> Dict[str, Any]:
        """Execute SQL via SetuPranali API."""
        if self._closed:
            raise ProgrammingError("Connection is closed")
        
        url = f"{self.base_url}/v1/sql"
        
        payload = {
            "sql": sql,
        }
        
        # Add dataset context if available
        if self.database:
            payload["dataset"] = self.database
        
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            raise OperationalError(f"Query timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise OperationalError(f"Connection failed: {e}")
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text if e.response else str(e)
            raise DatabaseError(f"Query failed: {error_msg}")
    
    def _get_tables(self) -> List[str]:
        """Get list of tables (datasets)."""
        url = f"{self.base_url}/v1/introspection/datasets"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return [item["id"] for item in data.get("items", [])]
        except Exception as e:
            logger.warning(f"Failed to get tables: {e}")
            return []
    
    def _get_columns(self, table: str) -> List[Dict[str, Any]]:
        """Get columns for a table (dataset)."""
        url = f"{self.base_url}/v1/introspection/datasets/{table}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            columns = []
            
            # Add dimensions
            for dim in data.get("dimensions", []):
                columns.append({
                    "name": dim["name"],
                    "type": dim.get("type", "string"),
                    "nullable": True,
                    "is_dimension": True,
                })
            
            # Add metrics
            for metric in data.get("metrics", []):
                columns.append({
                    "name": metric["name"],
                    "type": "number",
                    "nullable": True,
                    "is_metric": True,
                })
            
            return columns
        except Exception as e:
            logger.warning(f"Failed to get columns for {table}: {e}")
            return []


class SetuPranaliDBAPI:
    """
    DB-API 2.0 module-level interface.
    """
    
    # Module globals
    apilevel = apilevel
    threadsafety = threadsafety
    paramstyle = paramstyle
    
    # Exceptions
    Error = Error
    Warning = Warning
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    DataError = DataError
    OperationalError = OperationalError
    IntegrityError = IntegrityError
    InternalError = InternalError
    ProgrammingError = ProgrammingError
    NotSupportedError = NotSupportedError
    
    @staticmethod
    def connect(
        host: str = "localhost",
        port: int = 8080,
        api_key: str = "",
        scheme: str = "http",
        database: str = "",
        **kwargs
    ) -> SetuPranaliConnection:
        """
        Create a connection to SetuPranali.
        
        Args:
            host: Server hostname
            port: Server port (default: 8080)
            api_key: API key for authentication
            scheme: http or https (default: http)
            database: Default dataset for RLS context
            **kwargs: Additional connection options
        
        Returns:
            SetuPranaliConnection instance
        """
        return SetuPranaliConnection(
            host=host,
            port=port,
            api_key=api_key,
            scheme=scheme,
            database=database,
            **kwargs
        )


# Convenience function
def connect(**kwargs) -> SetuPranaliConnection:
    """Create a SetuPranali connection."""
    return SetuPranaliDBAPI.connect(**kwargs)

