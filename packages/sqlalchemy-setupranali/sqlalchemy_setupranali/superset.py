"""
Superset-specific dialect for SetuPranali

Provides the `superset://` connection URL scheme for native Superset integration.

Usage in Superset:
    superset://api_key@host:port/
    superset+http://host:port/?api_key=your-key
    superset+https://host:port/?api_key=your-key

Features:
    - Native Superset database plugin
    - Automatic schema introspection
    - Query metrics and dimensions
    - Time grain support
    - Jinja templating compatibility
"""

from sqlalchemy_setupranali.dialect import SetuPranaliDialect


class SupersetDialect(SetuPranaliDialect):
    """
    Superset-optimized dialect for SetuPranali.
    
    Registered as 'superset' and 'superset+http' and 'superset+https'.
    """
    
    name = "superset"
    
    # Superset-specific settings
    supports_multivalues_insert = False
    supports_native_decimal = True
    supports_native_boolean = True
    supports_statement_cache = True
    
    # Time grain expressions for Superset
    _time_grain_expressions = {
        None: "{col}",
        "PT1S": "DATE_TRUNC('second', {col})",
        "PT1M": "DATE_TRUNC('minute', {col})",
        "PT5M": "DATE_TRUNC('minute', {col}) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM {col})::INT % 5)",
        "PT10M": "DATE_TRUNC('minute', {col}) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM {col})::INT % 10)",
        "PT15M": "DATE_TRUNC('minute', {col}) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM {col})::INT % 15)",
        "PT30M": "DATE_TRUNC('minute', {col}) - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM {col})::INT % 30)",
        "PT1H": "DATE_TRUNC('hour', {col})",
        "P1D": "DATE_TRUNC('day', {col})",
        "P1W": "DATE_TRUNC('week', {col})",
        "P1M": "DATE_TRUNC('month', {col})",
        "P3M": "DATE_TRUNC('quarter', {col})",
        "P1Y": "DATE_TRUNC('year', {col})",
    }
    
    @classmethod
    def get_time_grain_expressions(cls):
        """Return time grain expressions for Superset."""
        return cls._time_grain_expressions
    
    def get_function_names(self, connection):
        """Return available SQL functions."""
        return [
            "SUM", "AVG", "COUNT", "MIN", "MAX",
            "COUNT_DISTINCT", "STDDEV", "VARIANCE",
            "DATE_TRUNC", "EXTRACT", "COALESCE",
            "CASE", "WHEN", "THEN", "ELSE", "END",
        ]
    
    def get_view_names(self, connection, schema=None, **kw):
        """Return datasets as views for Superset."""
        return self.get_table_names(connection, schema, **kw)


class SupersetHTTPDialect(SupersetDialect):
    """Superset dialect with HTTP scheme."""
    name = "superset+http"


class SupersetHTTPSDialect(SupersetDialect):
    """Superset dialect with HTTPS scheme."""
    name = "superset+https"

