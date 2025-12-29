from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from datetime import date, datetime

FieldType = Literal[
    "string","int32","int64","float","double","decimal","boolean",
    "date","datetime","timestamp","json","bytes"
]
SemanticType = Literal[
    "dimension","metric","time","identifier","geo_country","geo_state","geo_city",
    "currency","percent","url","email","phone"
]
TimeGrain = Literal["minute","hour","day","week","month","quarter","year"]
AggFn = Literal["sum","avg","min","max","count","count_distinct","stddev","variance"]

# =============================================================================
# INCREMENTAL REFRESH TYPES
# =============================================================================
# These define the incremental refresh configuration from catalog.yaml

IncrementalType = Literal["date", "datetime", "int"]
IncrementalMode = Literal["append", "upsert"]


class IncrementalConfig(BaseModel):
    """
    Incremental refresh configuration for a dataset.
    
    Defined in catalog.yaml per dataset. Enables BI tools to fetch
    only new/changed data instead of full table scans.
    """
    enabled: bool = False
    column: Optional[str] = None          # Column to filter on (e.g., order_date)
    type: IncrementalType = "datetime"    # Data type of the column
    mode: IncrementalMode = "append"      # append = new rows only
    maxWindowDays: int = 90               # Safety limit for date ranges

class FilterCondition(BaseModel):
    field: str
    op: Literal["eq","ne","gt","gte","lt","lte","in","not_in","between","contains",
               "starts_with","ends_with","is_null","is_not_null"]
    value: Optional[Any] = None
    values: Optional[List[Any]] = None
    from_: Optional[Any] = Field(default=None, alias="from")
    to: Optional[Any] = None
    caseInsensitive: bool = False

class FilterAnd(BaseModel):
    and_: List["FilterGroup"] = Field(alias="and")

class FilterOr(BaseModel):
    or_: List["FilterGroup"] = Field(alias="or")

class FilterNot(BaseModel):
    not_: "FilterGroup" = Field(alias="not")

FilterGroup = Union[FilterAnd, FilterOr, FilterNot, FilterCondition]

class QueryDimension(BaseModel):
    name: str
    timeGrain: Optional[TimeGrain] = None
    alias: Optional[str] = None

class QueryMetric(BaseModel):
    name: str
    alias: Optional[str] = None
    where: Optional[FilterGroup] = None

class OrderBy(BaseModel):
    field: str
    direction: Literal["asc","desc"]
    nulls: Optional[Literal["first","last"]] = None

class QueryRequest(BaseModel):
    """
    Semantic query request supporting full and incremental refresh.
    
    INCREMENTAL REFRESH:
    When incremental=True and the dataset has incremental config enabled:
    - incrementalFrom: Fetch rows where column >= this value
    - incrementalTo: Fetch rows where column < this value (optional)
    
    How BI tools use this:
    - Power BI: Passes $filter with ge/lt on incremental column
    - Tableau: Passes lastExtractValue as incrementalFrom
    - REST API: Explicitly sets incremental fields
    
    Safety:
    - maxWindowDays from dataset config limits range
    - If dataset doesn't support incremental, fields are ignored
    """
    dataset: str
    dimensions: List[QueryDimension] = []
    metrics: List[QueryMetric] = []
    filters: Optional[FilterGroup] = None
    orderBy: List[OrderBy] = []
    limit: int = 10000
    offset: int = 0
    timezone: Optional[str] = None
    resultFormat: Literal["json_rows","json_columns"] = "json_rows"
    options: Dict[str, Any] = {}
    
    # =========================================================================
    # INCREMENTAL REFRESH FIELDS (Optional, backward-compatible)
    # =========================================================================
    # These fields are optional and ignored if the dataset doesn't support
    # incremental refresh (incremental.enabled=false in catalog.yaml).
    
    incremental: bool = False
    """Enable incremental mode. If True, incrementalFrom/To are used."""
    
    incrementalFrom: Optional[Union[str, int, float, date, datetime]] = None
    """Inclusive lower bound: column >= incrementalFrom"""
    
    incrementalTo: Optional[Union[str, int, float, date, datetime]] = None
    """Exclusive upper bound: column < incrementalTo"""

class ResultColumn(BaseModel):
    name: str
    type: FieldType
    semanticType: Optional[SemanticType] = None

class QueryResponse(BaseModel):
    dataset: str
    columns: List[ResultColumn]
    rows: List[Dict[str, Any]]
    stats: Dict[str, Any] = {}
    warnings: List[str] = []
