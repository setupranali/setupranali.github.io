"""
Semantic Model Manager

Manages semantic layer definitions:
- Dimensions (categorical/grouping columns)
- Measures (aggregated metrics)
- Calculated fields (derived expressions)
- Time intelligence
- Validation of expressions

The semantic model sits on top of the physical schema and ERD,
providing a business-friendly view of the data.
"""

import json
import logging
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AggregationType(str, Enum):
    """Supported aggregation functions."""
    SUM = "SUM"
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT_DISTINCT"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    MEDIAN = "MEDIAN"
    STDDEV = "STDDEV"
    VARIANCE = "VARIANCE"
    FIRST = "FIRST"
    LAST = "LAST"
    NONE = "NONE"  # For calculated fields that don't aggregate


class DimensionType(str, Enum):
    """Dimension types for categorization."""
    CATEGORICAL = "categorical"
    TIME = "time"
    GEO = "geo"
    HIERARCHICAL = "hierarchical"


class TimeGranularity(str, Enum):
    """Time dimension granularities."""
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"


class FormatType(str, Enum):
    """Display format types."""
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"
    DATE = "date"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"


@dataclass
class Dimension:
    """
    A dimension (categorical column) in the semantic model.
    
    Attributes:
        id: Unique identifier
        name: Business name (display)
        source_column: Physical column reference (table.column)
        source_table: Source table (schema.table)
        description: Business description
        dimension_type: Type of dimension
        hierarchy_level: Position in hierarchy (if hierarchical)
        parent_dimension_id: Parent dimension for hierarchy
        default_format: Display format
        is_visible: Whether to show in UI
        synonyms: Alternative names for NLQ
        metadata: Additional attributes
    """
    id: str
    name: str
    source_column: str
    source_table: str
    description: Optional[str] = None
    dimension_type: DimensionType = DimensionType.CATEGORICAL
    hierarchy_level: int = 0
    parent_dimension_id: Optional[str] = None
    default_format: FormatType = FormatType.TEXT
    is_visible: bool = True
    synonyms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sourceColumn": self.source_column,
            "sourceTable": self.source_table,
            "description": self.description,
            "dimensionType": self.dimension_type.value,
            "hierarchyLevel": self.hierarchy_level,
            "parentDimensionId": self.parent_dimension_id,
            "defaultFormat": self.default_format.value,
            "isVisible": self.is_visible,
            "synonyms": self.synonyms,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Dimension":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            source_column=data.get("sourceColumn", data.get("source_column", "")),
            source_table=data.get("sourceTable", data.get("source_table", "")),
            description=data.get("description"),
            dimension_type=DimensionType(data.get("dimensionType", data.get("dimension_type", "categorical"))),
            hierarchy_level=data.get("hierarchyLevel", data.get("hierarchy_level", 0)),
            parent_dimension_id=data.get("parentDimensionId", data.get("parent_dimension_id")),
            default_format=FormatType(data.get("defaultFormat", data.get("default_format", "text"))),
            is_visible=data.get("isVisible", data.get("is_visible", True)),
            synonyms=data.get("synonyms", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Measure:
    """
    A measure (metric) in the semantic model.
    
    Attributes:
        id: Unique identifier
        name: Business name (display)
        expression: SQL expression or column reference
        aggregation: Aggregation function
        source_table: Primary source table
        description: Business description
        format_string: Display format string
        format_type: Format type
        is_visible: Whether to show in UI
        is_additive: Whether measure can be summed across dimensions
        depends_on: IDs of measures this depends on (for calculated)
        filters: Default filters to apply
        synonyms: Alternative names for NLQ
        metadata: Additional attributes
    """
    id: str
    name: str
    expression: str
    aggregation: AggregationType = AggregationType.SUM
    source_table: Optional[str] = None
    description: Optional[str] = None
    format_string: str = "#,##0.00"
    format_type: FormatType = FormatType.NUMBER
    is_visible: bool = True
    is_additive: bool = True
    depends_on: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "expression": self.expression,
            "aggregation": self.aggregation.value,
            "sourceTable": self.source_table,
            "description": self.description,
            "formatString": self.format_string,
            "formatType": self.format_type.value,
            "isVisible": self.is_visible,
            "isAdditive": self.is_additive,
            "dependsOn": self.depends_on,
            "filters": self.filters,
            "synonyms": self.synonyms,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Measure":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            expression=data.get("expression", ""),
            aggregation=AggregationType(data.get("aggregation", "SUM")),
            source_table=data.get("sourceTable", data.get("source_table")),
            description=data.get("description"),
            format_string=data.get("formatString", data.get("format_string", "#,##0.00")),
            format_type=FormatType(data.get("formatType", data.get("format_type", "number"))),
            is_visible=data.get("isVisible", data.get("is_visible", True)),
            is_additive=data.get("isAdditive", data.get("is_additive", True)),
            depends_on=data.get("dependsOn", data.get("depends_on", [])),
            filters=data.get("filters", []),
            synonyms=data.get("synonyms", []),
            metadata=data.get("metadata", {}),
        )
    
    def to_sql(self) -> str:
        """Generate SQL expression for this measure."""
        if self.aggregation == AggregationType.NONE:
            return self.expression
        elif self.aggregation == AggregationType.COUNT_DISTINCT:
            return f"COUNT(DISTINCT {self.expression})"
        else:
            return f"{self.aggregation.value}({self.expression})"


@dataclass
class CalculatedField:
    """
    A calculated field that derives from other measures/dimensions.
    
    Supports expressions like:
    - [Revenue] / [Orders]  -> Average Order Value
    - [Revenue] - [Cost]    -> Profit
    - CASE WHEN [Status] = 'Active' THEN 1 ELSE 0 END
    """
    id: str
    name: str
    expression: str
    result_type: str = "number"  # number, string, date, boolean
    description: Optional[str] = None
    format_string: str = "#,##0.00"
    format_type: FormatType = FormatType.NUMBER
    is_visible: bool = True
    referenced_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "expression": self.expression,
            "resultType": self.result_type,
            "description": self.description,
            "formatString": self.format_string,
            "formatType": self.format_type.value,
            "isVisible": self.is_visible,
            "referencedFields": self.referenced_fields,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CalculatedField":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            expression=data.get("expression", ""),
            result_type=data.get("resultType", data.get("result_type", "number")),
            description=data.get("description"),
            format_string=data.get("formatString", data.get("format_string", "#,##0.00")),
            format_type=FormatType(data.get("formatType", data.get("format_type", "number"))),
            is_visible=data.get("isVisible", data.get("is_visible", True)),
            referenced_fields=data.get("referencedFields", data.get("referenced_fields", [])),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TimeIntelligence:
    """
    Time intelligence configuration for a time dimension.
    
    Enables automatic time-based calculations like:
    - Year-to-Date (YTD)
    - Month-over-Month (MoM)
    - Same Period Last Year (SPLY)
    """
    dimension_id: str
    date_column: str
    fiscal_year_start_month: int = 1
    week_start_day: int = 1  # 1=Monday, 7=Sunday
    enabled_calculations: List[str] = field(default_factory=lambda: [
        "YTD", "QTD", "MTD", "WTD",
        "YoY", "QoQ", "MoM", "WoW",
        "SPLY", "Rolling7", "Rolling30", "Rolling90"
    ])
    
    def to_dict(self) -> dict:
        return {
            "dimensionId": self.dimension_id,
            "dateColumn": self.date_column,
            "fiscalYearStartMonth": self.fiscal_year_start_month,
            "weekStartDay": self.week_start_day,
            "enabledCalculations": self.enabled_calculations,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TimeIntelligence":
        return cls(
            dimension_id=data.get("dimensionId", data.get("dimension_id", "")),
            date_column=data.get("dateColumn", data.get("date_column", "")),
            fiscal_year_start_month=data.get("fiscalYearStartMonth", data.get("fiscal_year_start_month", 1)),
            week_start_day=data.get("weekStartDay", data.get("week_start_day", 1)),
            enabled_calculations=data.get("enabledCalculations", data.get("enabled_calculations", [])),
        )


@dataclass
class SemanticModel:
    """
    Complete semantic model for a data source.
    
    Contains all dimensions, measures, calculated fields,
    and time intelligence configurations.
    """
    id: str
    name: str
    source_id: str
    erd_model_id: Optional[str] = None
    dimensions: List[Dimension] = field(default_factory=list)
    measures: List[Measure] = field(default_factory=list)
    calculated_fields: List[CalculatedField] = field(default_factory=list)
    time_intelligence: List[TimeIntelligence] = field(default_factory=list)
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sourceId": self.source_id,
            "erdModelId": self.erd_model_id,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "measures": [m.to_dict() for m in self.measures],
            "calculatedFields": [c.to_dict() for c in self.calculated_fields],
            "timeIntelligence": [t.to_dict() for t in self.time_intelligence],
            "description": self.description,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SemanticModel":
        created_at = data.get("createdAt") or data.get("created_at")
        updated_at = data.get("updatedAt") or data.get("updated_at")
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled"),
            source_id=data.get("sourceId", data.get("source_id", "")),
            erd_model_id=data.get("erdModelId", data.get("erd_model_id")),
            dimensions=[Dimension.from_dict(d) for d in data.get("dimensions", [])],
            measures=[Measure.from_dict(m) for m in data.get("measures", [])],
            calculated_fields=[CalculatedField.from_dict(c) for c in data.get("calculatedFields", data.get("calculated_fields", []))],
            time_intelligence=[TimeIntelligence.from_dict(t) for t in data.get("timeIntelligence", data.get("time_intelligence", []))],
            description=data.get("description"),
            created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
            updated_at=datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else updated_at,
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
        )
    
    def get_dimension(self, id_or_name: str) -> Optional[Dimension]:
        """Get dimension by ID or name."""
        for d in self.dimensions:
            if d.id == id_or_name or d.name == id_or_name:
                return d
        return None
    
    def get_measure(self, id_or_name: str) -> Optional[Measure]:
        """Get measure by ID or name."""
        for m in self.measures:
            if m.id == id_or_name or m.name == id_or_name:
                return m
        return None
    
    def get_calculated_field(self, id_or_name: str) -> Optional[CalculatedField]:
        """Get calculated field by ID or name."""
        for c in self.calculated_fields:
            if c.id == id_or_name or c.name == id_or_name:
                return c
        return None
    
    def get_time_dimensions(self) -> List[Dimension]:
        """Get all time-type dimensions."""
        return [d for d in self.dimensions if d.dimension_type == DimensionType.TIME]
    
    def validate(self) -> List[str]:
        """
        Validate the semantic model.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check for duplicate names
        dim_names = [d.name for d in self.dimensions]
        measure_names = [m.name for m in self.measures]
        calc_names = [c.name for c in self.calculated_fields]
        
        all_names = dim_names + measure_names + calc_names
        duplicates = [n for n in set(all_names) if all_names.count(n) > 1]
        for dup in duplicates:
            errors.append(f"Duplicate name: {dup}")
        
        # Validate calculated field references
        valid_refs = set(dim_names + measure_names + calc_names)
        for calc in self.calculated_fields:
            for ref in calc.referenced_fields:
                if ref not in valid_refs:
                    errors.append(f"Calculated field '{calc.name}' references unknown field: {ref}")
        
        # Validate hierarchy relationships
        dim_ids = {d.id for d in self.dimensions}
        for dim in self.dimensions:
            if dim.parent_dimension_id and dim.parent_dimension_id not in dim_ids:
                errors.append(f"Dimension '{dim.name}' references unknown parent: {dim.parent_dimension_id}")
        
        # Validate time intelligence configurations
        for ti in self.time_intelligence:
            if not self.get_dimension(ti.dimension_id):
                errors.append(f"Time intelligence references unknown dimension: {ti.dimension_id}")
        
        return errors


class SemanticModelManager:
    """
    Manages semantic model persistence.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize manager.
        
        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "db"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "semantic.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    erd_model_id TEXT,
                    description TEXT,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_source_id 
                ON semantic_models(source_id)
            """)
            conn.commit()
    
    def create(self, model: SemanticModel) -> SemanticModel:
        """Create a new semantic model."""
        if not model.id:
            model.id = str(uuid.uuid4())
        
        model.created_at = datetime.now(timezone.utc)
        model.updated_at = model.created_at
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO semantic_models 
                (id, name, source_id, erd_model_id, description, data, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model.id,
                model.name,
                model.source_id,
                model.erd_model_id,
                model.description,
                json.dumps(model.to_dict()),
                model.version,
                model.created_at.isoformat(),
                model.updated_at.isoformat(),
            ))
            conn.commit()
        
        logger.info(f"Created semantic model: {model.id}")
        return model
    
    def get(self, model_id: str) -> Optional[SemanticModel]:
        """Get semantic model by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT data FROM semantic_models WHERE id = ?",
                (model_id,)
            ).fetchone()
        
        if row:
            return SemanticModel.from_dict(json.loads(row["data"]))
        return None
    
    def update(self, model: SemanticModel) -> SemanticModel:
        """Update an existing semantic model."""
        model.updated_at = datetime.now(timezone.utc)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE semantic_models 
                SET name = ?, erd_model_id = ?, description = ?, data = ?, version = ?, updated_at = ?
                WHERE id = ?
            """, (
                model.name,
                model.erd_model_id,
                model.description,
                json.dumps(model.to_dict()),
                model.version,
                model.updated_at.isoformat(),
                model.id,
            ))
            conn.commit()
        
        logger.info(f"Updated semantic model: {model.id}")
        return model
    
    def delete(self, model_id: str) -> bool:
        """Delete a semantic model."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM semantic_models WHERE id = ?",
                (model_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"Deleted semantic model: {model_id}")
        return deleted
    
    def list_by_source(self, source_id: str) -> List[SemanticModel]:
        """List all semantic models for a source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT data FROM semantic_models WHERE source_id = ? ORDER BY updated_at DESC",
                (source_id,)
            ).fetchall()
        
        return [SemanticModel.from_dict(json.loads(row["data"])) for row in rows]
    
    def list_all(self) -> List[SemanticModel]:
        """List all semantic models."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT data FROM semantic_models ORDER BY updated_at DESC"
            ).fetchall()
        
        return [SemanticModel.from_dict(json.loads(row["data"])) for row in rows]


class ExpressionValidator:
    """
    Validates SQL expressions for measures and calculated fields.
    """
    
    # Allowed SQL functions (whitelist)
    ALLOWED_FUNCTIONS = {
        # Aggregation
        "SUM", "COUNT", "AVG", "MIN", "MAX", "MEDIAN", "STDDEV", "VARIANCE",
        # String
        "UPPER", "LOWER", "TRIM", "LTRIM", "RTRIM", "SUBSTRING", "CONCAT", "LENGTH", "REPLACE",
        # Math
        "ABS", "ROUND", "FLOOR", "CEIL", "CEILING", "POWER", "SQRT", "LOG", "LN", "EXP", "MOD",
        # Date
        "DATE", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND", "DATEADD", "DATEDIFF",
        "DATE_TRUNC", "EXTRACT", "NOW", "CURRENT_DATE", "CURRENT_TIMESTAMP",
        # Conditional
        "CASE", "WHEN", "THEN", "ELSE", "END", "COALESCE", "NULLIF", "IIF", "IF",
        # Type conversion
        "CAST", "CONVERT", "TRY_CAST",
    }
    
    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bTRUNCATE\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
        r"\bEXEC\b",
        r"\bEXECUTE\b",
        r"--",  # SQL comments
        r"/\*",  # Block comments
        r";",   # Statement separator
    ]
    
    @classmethod
    def validate(cls, expression: str) -> tuple[bool, List[str]]:
        """
        Validate an expression.
        
        Args:
            expression: SQL expression to validate
        
        Returns:
            (is_valid, list of error messages)
        """
        errors = []
        
        # Check for blocked patterns
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, expression, re.IGNORECASE):
                errors.append(f"Blocked pattern detected: {pattern}")
        
        # Check bracket balance
        open_parens = expression.count("(")
        close_parens = expression.count(")")
        if open_parens != close_parens:
            errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
        
        # Check bracket references [field_name]
        bracket_refs = re.findall(r"\[([^\]]+)\]", expression)
        # These will be validated against actual fields later
        
        # Check for unknown functions
        func_pattern = r"\b([A-Z_][A-Z0-9_]*)\s*\("
        functions_used = re.findall(func_pattern, expression, re.IGNORECASE)
        for func in functions_used:
            if func.upper() not in cls.ALLOWED_FUNCTIONS:
                errors.append(f"Unknown or disallowed function: {func}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def extract_field_references(cls, expression: str) -> List[str]:
        """
        Extract field references from an expression.
        
        Field references are in brackets: [Revenue], [Order Count]
        
        Returns:
            List of field names referenced
        """
        return re.findall(r"\[([^\]]+)\]", expression)
    
    @classmethod
    def substitute_fields(
        cls, 
        expression: str, 
        field_map: Dict[str, str]
    ) -> str:
        """
        Substitute field references with actual column expressions.
        
        Args:
            expression: Expression with [field] references
            field_map: Mapping of field names to SQL expressions
        
        Returns:
            Expression with substituted values
        """
        result = expression
        for field_name, sql_expr in field_map.items():
            result = result.replace(f"[{field_name}]", f"({sql_expr})")
        return result

