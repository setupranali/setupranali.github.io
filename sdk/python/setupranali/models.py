"""
SetuPranali SDK Data Models
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class Dimension:
    """A dimension (groupable field) in a dataset."""
    name: str
    label: Optional[str] = None
    type: str = "string"
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Dimension":
        return cls(
            name=data["name"],
            label=data.get("label"),
            type=data.get("type", "string"),
            description=data.get("description")
        )


@dataclass
class Metric:
    """A metric (aggregatable measure) in a dataset."""
    name: str
    label: Optional[str] = None
    type: str = "number"
    sql: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Metric":
        return cls(
            name=data["name"],
            label=data.get("label"),
            type=data.get("type", "number"),
            sql=data.get("sql"),
            description=data.get("description")
        )


@dataclass
class Dataset:
    """A semantic dataset definition."""
    id: str
    name: str
    description: Optional[str] = None
    source: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dimensions: List[Dimension] = field(default_factory=list)
    metrics: List[Metric] = field(default_factory=list)
    default_timezone: str = "UTC"
    
    @classmethod
    def from_dict(cls, data: dict) -> "Dataset":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description"),
            source=data.get("source"),
            tags=data.get("tags", []),
            dimensions=[Dimension.from_dict(d) for d in data.get("dimensions", [])],
            metrics=[Metric.from_dict(m) for m in data.get("metrics", [])],
            default_timezone=data.get("defaultTimezone", "UTC")
        )
    
    def dimension_names(self) -> List[str]:
        """Get list of dimension names."""
        return [d.name for d in self.dimensions]
    
    def metric_names(self) -> List[str]:
        """Get list of metric names."""
        return [m.name for m in self.metrics]


@dataclass
class Column:
    """A column in query results."""
    name: str
    type: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "Column":
        return cls(name=data["name"], type=data["type"])


@dataclass
class QueryResult:
    """Result of a semantic query."""
    columns: List[Column]
    data: List[Dict[str, Any]]
    row_count: int
    cached: bool = False
    execution_time_ms: Optional[int] = None
    query_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "QueryResult":
        return cls(
            columns=[Column.from_dict(c) for c in data.get("columns", [])],
            data=data.get("data", []),
            row_count=data.get("rowCount", len(data.get("data", []))),
            cached=data.get("cached", False),
            execution_time_ms=data.get("executionTimeMs"),
            query_id=data.get("queryId")
        )
    
    def to_dataframe(self):
        """
        Convert result to pandas DataFrame.
        
        Requires pandas to be installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install it with: pip install pandas"
            )
        
        return pd.DataFrame(self.data)
    
    def to_records(self) -> List[Dict[str, Any]]:
        """Return data as list of dictionaries."""
        return self.data
    
    def to_tuples(self) -> List[tuple]:
        """Return data as list of tuples."""
        if not self.data:
            return []
        keys = list(self.data[0].keys())
        return [tuple(row[k] for k in keys) for row in self.data]
    
    def column_names(self) -> List[str]:
        """Get list of column names."""
        return [c.name for c in self.columns]
    
    def __len__(self) -> int:
        return self.row_count
    
    def __iter__(self):
        return iter(self.data)
    
    def __getitem__(self, index):
        return self.data[index]


@dataclass
class HealthStatus:
    """System health status."""
    status: str
    version: str
    cache_enabled: bool
    redis_available: bool
    timestamp: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "HealthStatus":
        return cls(
            status=data["status"],
            version=data.get("version", "unknown"),
            cache_enabled=data.get("cache", {}).get("enabled", False),
            redis_available=data.get("cache", {}).get("redis_available", False),
            timestamp=datetime.fromisoformat(data["time"]) if "time" in data else None
        )
    
    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"

