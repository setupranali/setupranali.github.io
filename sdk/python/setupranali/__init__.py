"""
SetuPranali Python SDK

A Python client for the SetuPranali semantic analytics layer.

Example:
    from setupranali import SetuPranali
    
    client = SetuPranali(
        url="http://localhost:8080",
        api_key="your-api-key"
    )
    
    # List datasets
    datasets = client.datasets()
    
    # Query data
    result = client.query(
        dataset="orders",
        dimensions=["city"],
        metrics=["total_revenue"],
        filters=[{"field": "order_date", "operator": "gte", "value": "2024-01-01"}]
    )
    
    # Get as DataFrame
    df = result.to_dataframe()
"""

from .client import SetuPranali, SetuPranaliAsync
from .models import QueryResult, Dataset, Dimension, Metric
from .exceptions import (
    SetuPranaliError,
    AuthenticationError,
    DatasetNotFoundError,
    QueryError,
    ConnectionError
)

# Jupyter widgets (optional import)
try:
    from .jupyter import DatasetExplorer, QuickQuery, explore
    _JUPYTER_AVAILABLE = True
except ImportError:
    _JUPYTER_AVAILABLE = False
    DatasetExplorer = None
    QuickQuery = None
    explore = None

__version__ = "1.0.0"
__all__ = [
    "SetuPranali",
    "SetuPranaliAsync",
    "QueryResult",
    "Dataset",
    "Dimension",
    "Metric",
    "SetuPranaliError",
    "AuthenticationError",
    "DatasetNotFoundError",
    "QueryError",
    "ConnectionError",
    # Jupyter
    "DatasetExplorer",
    "QuickQuery",
    "explore",
]

