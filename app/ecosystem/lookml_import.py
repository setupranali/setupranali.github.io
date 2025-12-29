"""
LookML Import for SetuPranali

Import Looker/LookML models into SetuPranali catalog.

Supports:
- LookML view files parsing
- LookML model files parsing
- Dimension and measure extraction
- Join relationships
- Derived tables
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# LookML Data Models
# =============================================================================

@dataclass
class LookMLDimension:
    """LookML dimension definition."""
    name: str
    sql: Optional[str] = None
    type: str = "string"
    label: Optional[str] = None
    description: Optional[str] = None
    primary_key: bool = False
    hidden: bool = False
    group_label: Optional[str] = None
    drill_fields: List[str] = field(default_factory=list)


@dataclass
class LookMLMeasure:
    """LookML measure definition."""
    name: str
    sql: Optional[str] = None
    type: str = "count"  # count, count_distinct, sum, average, min, max, number
    label: Optional[str] = None
    description: Optional[str] = None
    value_format: Optional[str] = None
    drill_fields: List[str] = field(default_factory=list)
    filters: Dict[str, str] = field(default_factory=dict)


@dataclass
class LookMLJoin:
    """LookML join definition."""
    name: str
    from_view: Optional[str] = None
    relationship: str = "many_to_one"  # one_to_one, many_to_one, one_to_many, many_to_many
    type: str = "left_outer"  # left_outer, inner, full_outer, cross
    sql_on: Optional[str] = None
    foreign_key: Optional[str] = None


@dataclass
class LookMLView:
    """LookML view definition."""
    name: str
    sql_table_name: Optional[str] = None
    derived_table: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    description: Optional[str] = None
    dimensions: List[LookMLDimension] = field(default_factory=list)
    measures: List[LookMLMeasure] = field(default_factory=list)
    dimension_groups: List[Dict[str, Any]] = field(default_factory=list)
    sets: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class LookMLExplore:
    """LookML explore definition."""
    name: str
    view_name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    joins: List[LookMLJoin] = field(default_factory=list)
    access_filters: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LookMLModel:
    """LookML model definition."""
    name: str
    connection: Optional[str] = None
    includes: List[str] = field(default_factory=list)
    explores: List[LookMLExplore] = field(default_factory=list)


# =============================================================================
# LookML Parser
# =============================================================================

class LookMLParser:
    """Parse LookML files."""
    
    # Token patterns
    BLOCK_START = re.compile(r'(\w+)\s*:\s*(\w+)?\s*\{')
    PROPERTY = re.compile(r'(\w+)\s*:\s*(.+)')
    STRING_VALUE = re.compile(r'^"([^"]*)"$|^\'([^\']*)\'$')
    SQL_VALUE = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.views: Dict[str, LookMLView] = {}
        self.models: Dict[str, LookMLModel] = {}
        self.explores: Dict[str, LookMLExplore] = {}
    
    def load(self) -> None:
        """Load and parse all LookML files."""
        if not self.project_path.exists():
            raise FileNotFoundError(f"LookML project not found: {self.project_path}")
        
        # Parse view files
        for file in self.project_path.glob("**/*.view.lkml"):
            self._parse_view_file(file)
        
        # Parse model files
        for file in self.project_path.glob("**/*.model.lkml"):
            self._parse_model_file(file)
        
        # Also check for .lookml extension (older format)
        for file in self.project_path.glob("**/*.view.lookml"):
            self._parse_view_file(file)
        
        for file in self.project_path.glob("**/*.model.lookml"):
            self._parse_model_file(file)
        
        logger.info(
            f"Loaded LookML project: {len(self.views)} views, "
            f"{len(self.models)} models, {len(self.explores)} explores"
        )
    
    def _parse_view_file(self, file_path: Path) -> None:
        """Parse a LookML view file."""
        try:
            content = file_path.read_text()
            parsed = self._parse_lookml(content)
            
            for view_data in parsed.get("view", []):
                view = self._extract_view(view_data)
                self.views[view.name] = view
                
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
    
    def _parse_model_file(self, file_path: Path) -> None:
        """Parse a LookML model file."""
        try:
            content = file_path.read_text()
            parsed = self._parse_lookml(content)
            
            model = LookMLModel(name=file_path.stem.replace(".model", ""))
            
            if "connection" in parsed:
                model.connection = parsed["connection"]
            
            if "include" in parsed:
                model.includes = parsed["include"] if isinstance(parsed["include"], list) else [parsed["include"]]
            
            for explore_data in parsed.get("explore", []):
                explore = self._extract_explore(explore_data)
                model.explores.append(explore)
                self.explores[explore.name] = explore
            
            self.models[model.name] = model
            
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
    
    def _parse_lookml(self, content: str) -> Dict[str, Any]:
        """Parse LookML content to dictionary."""
        result = {}
        
        # Remove comments
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        
        # Simple recursive descent parser
        lines = content.split('\n')
        return self._parse_block(lines, 0, len(lines))[0]
    
    def _parse_block(
        self,
        lines: List[str],
        start: int,
        end: int
    ) -> Tuple[Dict[str, Any], int]:
        """Parse a block of LookML."""
        result = {}
        i = start
        
        while i < end:
            line = lines[i].strip()
            
            if not line or line.startswith('#'):
                i += 1
                continue
            
            if line == '}':
                return result, i
            
            # Check for block start (e.g., "view: my_view {")
            block_match = re.match(r'(\w+)\s*:\s*(\w+)?\s*\{', line)
            if block_match:
                block_type = block_match.group(1)
                block_name = block_match.group(2)
                
                # Find matching closing brace
                brace_count = 1
                j = i + 1
                while j < end and brace_count > 0:
                    for char in lines[j]:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                    if brace_count > 0:
                        j += 1
                
                # Parse inner block
                inner, _ = self._parse_block(lines, i + 1, j)
                if block_name:
                    inner["_name"] = block_name
                
                if block_type not in result:
                    result[block_type] = []
                if isinstance(result[block_type], list):
                    result[block_type].append(inner)
                else:
                    result[block_type] = [result[block_type], inner]
                
                i = j + 1
                continue
            
            # Check for simple property
            prop_match = re.match(r'(\w+)\s*:\s*(.+)', line)
            if prop_match:
                key = prop_match.group(1)
                value = prop_match.group(2).strip()
                
                # Handle multi-line SQL
                if value.endswith(';;'):
                    value = value[:-2].strip()
                elif not value.endswith('"') and not value.endswith("'"):
                    # Collect multi-line value
                    j = i + 1
                    while j < end and ';;' not in lines[j]:
                        value += '\n' + lines[j]
                        j += 1
                    if j < end:
                        value += '\n' + lines[j].replace(';;', '')
                    i = j
                
                # Clean value
                value = self._clean_value(value)
                result[key] = value
            
            i += 1
        
        return result, i
    
    def _clean_value(self, value: str) -> str:
        """Clean a LookML value."""
        value = value.strip()
        
        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        
        return value
    
    def _extract_view(self, data: Dict[str, Any]) -> LookMLView:
        """Extract view from parsed data."""
        view = LookMLView(name=data.get("_name", "unknown"))
        
        view.sql_table_name = data.get("sql_table_name")
        view.label = data.get("label")
        view.description = data.get("description")
        
        # Derived table
        if "derived_table" in data:
            view.derived_table = data["derived_table"]
        
        # Dimensions
        for dim_data in data.get("dimension", []):
            if isinstance(dim_data, dict):
                dim = LookMLDimension(
                    name=dim_data.get("_name", "unknown"),
                    sql=dim_data.get("sql"),
                    type=dim_data.get("type", "string"),
                    label=dim_data.get("label"),
                    description=dim_data.get("description"),
                    primary_key=dim_data.get("primary_key") == "yes",
                    hidden=dim_data.get("hidden") == "yes"
                )
                view.dimensions.append(dim)
        
        # Measures
        for measure_data in data.get("measure", []):
            if isinstance(measure_data, dict):
                measure = LookMLMeasure(
                    name=measure_data.get("_name", "unknown"),
                    sql=measure_data.get("sql"),
                    type=measure_data.get("type", "count"),
                    label=measure_data.get("label"),
                    description=measure_data.get("description"),
                    value_format=measure_data.get("value_format")
                )
                view.measures.append(measure)
        
        # Dimension groups (time-based dimensions)
        for dg_data in data.get("dimension_group", []):
            if isinstance(dg_data, dict):
                view.dimension_groups.append(dg_data)
        
        return view
    
    def _extract_explore(self, data: Dict[str, Any]) -> LookMLExplore:
        """Extract explore from parsed data."""
        explore = LookMLExplore(name=data.get("_name", "unknown"))
        
        explore.view_name = data.get("view_name") or data.get("from")
        explore.label = data.get("label")
        explore.description = data.get("description")
        
        # Joins
        for join_data in data.get("join", []):
            if isinstance(join_data, dict):
                join = LookMLJoin(
                    name=join_data.get("_name", "unknown"),
                    from_view=join_data.get("from"),
                    relationship=join_data.get("relationship", "many_to_one"),
                    type=join_data.get("type", "left_outer"),
                    sql_on=join_data.get("sql_on"),
                    foreign_key=join_data.get("foreign_key")
                )
                explore.joins.append(join)
        
        return explore


# =============================================================================
# LookML to SetuPranali Converter
# =============================================================================

class LookMLToSetuPranaliConverter:
    """Convert LookML to SetuPranali catalog."""
    
    MEASURE_TYPE_MAP = {
        "count": "COUNT(*)",
        "count_distinct": "COUNT(DISTINCT {sql})",
        "sum": "SUM({sql})",
        "average": "AVG({sql})",
        "min": "MIN({sql})",
        "max": "MAX({sql})",
        "number": "{sql}",
        "sum_distinct": "SUM(DISTINCT {sql})",
        "median": "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {sql})"
    }
    
    DIMENSION_TYPE_MAP = {
        "string": "string",
        "number": "number",
        "date": "date",
        "datetime": "datetime",
        "time": "datetime",
        "yesno": "boolean",
        "tier": "string",
        "zipcode": "string",
        "location": "string"
    }
    
    def __init__(self, parser: LookMLParser):
        self.parser = parser
    
    def convert(self) -> Dict[str, Any]:
        """Convert LookML to SetuPranali catalog."""
        datasets = []
        joins = []
        
        # Convert views to datasets
        for view in self.parser.views.values():
            dataset = self._convert_view(view)
            datasets.append(dataset)
        
        # Convert explore joins
        for explore in self.parser.explores.values():
            for join in explore.joins:
                j = self._convert_join(explore, join)
                if j:
                    joins.append(j)
        
        catalog = {
            "version": "1.0",
            "generated_from": "lookml",
            "generated_at": datetime.utcnow().isoformat(),
            "datasets": datasets
        }
        
        if joins:
            catalog["joins"] = joins
        
        return catalog
    
    def _convert_view(self, view: LookMLView) -> Dict[str, Any]:
        """Convert LookML view to SetuPranali dataset."""
        # Build SQL
        if view.sql_table_name:
            sql = f"SELECT * FROM {view.sql_table_name}"
        elif view.derived_table:
            sql_content = view.derived_table.get("sql", "")
            sql = self._clean_sql(sql_content)
        else:
            sql = f"SELECT * FROM {view.name}"
        
        # Convert dimensions
        dimensions = []
        for dim in view.dimensions:
            if dim.hidden:
                continue
            
            d = {
                "name": dim.name,
                "sql": self._clean_sql(dim.sql) if dim.sql else dim.name
            }
            if dim.label:
                d["description"] = dim.label
            elif dim.description:
                d["description"] = dim.description
            if dim.type:
                d["type"] = self.DIMENSION_TYPE_MAP.get(dim.type, "string")
            dimensions.append(d)
        
        # Add dimension groups as dimensions
        for dg in view.dimension_groups:
            name = dg.get("_name", "unknown")
            sql = dg.get("sql", name)
            timeframes = dg.get("timeframes", ["date", "month", "year"])
            
            for tf in timeframes:
                dimensions.append({
                    "name": f"{name}_{tf}",
                    "sql": self._time_dimension_sql(sql, tf),
                    "type": "date" if tf in ["date", "week", "month", "year"] else "datetime"
                })
        
        # Convert measures
        metrics = []
        for measure in view.measures:
            sql_template = self.MEASURE_TYPE_MAP.get(measure.type, "{sql}")
            measure_sql = self._clean_sql(measure.sql) if measure.sql else "*"
            sql_expr = sql_template.replace("{sql}", measure_sql)
            
            m = {
                "name": measure.name,
                "sql": sql_expr
            }
            if measure.label:
                m["description"] = measure.label
            elif measure.description:
                m["description"] = measure.description
            metrics.append(m)
        
        dataset = {
            "id": view.name,
            "name": view.label or view.name.replace("_", " ").title(),
            "sql": sql,
            "dimensions": dimensions,
            "metrics": metrics if metrics else [{"name": "count", "sql": "COUNT(*)"}]
        }
        
        if view.description:
            dataset["description"] = view.description
        
        return dataset
    
    def _convert_join(
        self,
        explore: LookMLExplore,
        join: LookMLJoin
    ) -> Optional[Dict[str, Any]]:
        """Convert LookML join to SetuPranali join."""
        base_view = explore.view_name or explore.name
        joined_view = join.from_view or join.name
        
        # Map relationship
        relationship_map = {
            "one_to_one": "one-to-one",
            "many_to_one": "many-to-one",
            "one_to_many": "one-to-many",
            "many_to_many": "many-to-many"
        }
        
        # Map join type
        type_map = {
            "left_outer": "left",
            "inner": "inner",
            "full_outer": "full",
            "cross": "cross"
        }
        
        return {
            "left_dataset": base_view,
            "right_dataset": joined_view,
            "join_type": type_map.get(join.type, "left"),
            "cardinality": relationship_map.get(join.relationship, "many-to-one"),
            "sql_on": self._clean_sql(join.sql_on) if join.sql_on else None
        }
    
    def _clean_sql(self, sql: str) -> str:
        """Clean LookML SQL syntax."""
        if not sql:
            return ""
        
        # Replace ${TABLE}.field with field
        sql = re.sub(r'\$\{TABLE\}\.(\w+)', r'\1', sql)
        
        # Replace ${view_name.field} with view_name.field
        sql = re.sub(r'\$\{(\w+)\.(\w+)\}', r'\1.\2', sql)
        
        # Replace ${field} with field
        sql = re.sub(r'\$\{(\w+)\}', r'\1', sql)
        
        return sql.strip()
    
    def _time_dimension_sql(self, sql: str, timeframe: str) -> str:
        """Generate SQL for time dimension."""
        clean = self._clean_sql(sql)
        
        timeframe_sql = {
            "raw": clean,
            "date": f"DATE({clean})",
            "week": f"DATE_TRUNC('week', {clean})",
            "month": f"DATE_TRUNC('month', {clean})",
            "quarter": f"DATE_TRUNC('quarter', {clean})",
            "year": f"DATE_TRUNC('year', {clean})",
            "hour": f"DATE_TRUNC('hour', {clean})",
            "day_of_week": f"EXTRACT(DOW FROM {clean})",
            "day_of_month": f"EXTRACT(DAY FROM {clean})",
            "month_name": f"TO_CHAR({clean}, 'Month')"
        }
        
        return timeframe_sql.get(timeframe, clean)
    
    def save_catalog(self, output_path: str) -> None:
        """Save generated catalog."""
        catalog = self.convert()
        
        with open(output_path, "w") as f:
            yaml.dump(catalog, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved LookML-converted catalog to {output_path}")


# =============================================================================
# LookML Import Service
# =============================================================================

class LookMLImportService:
    """Service for importing LookML projects."""
    
    def __init__(self):
        self.parser: Optional[LookMLParser] = None
    
    def import_project(
        self,
        project_path: str,
        output_path: str = "catalog.yaml"
    ) -> Dict[str, Any]:
        """Import LookML project to SetuPranali catalog."""
        self.parser = LookMLParser(project_path)
        self.parser.load()
        
        converter = LookMLToSetuPranaliConverter(self.parser)
        catalog = converter.convert()
        converter.save_catalog(output_path)
        
        return {
            "status": "imported",
            "views": len(self.parser.views),
            "explores": len(self.parser.explores),
            "datasets": len(catalog.get("datasets", [])),
            "output_path": output_path
        }
    
    def get_views(self) -> List[Dict[str, Any]]:
        """Get list of available views."""
        if not self.parser:
            return []
        
        return [
            {
                "name": v.name,
                "label": v.label,
                "dimensions": len(v.dimensions),
                "measures": len(v.measures)
            }
            for v in self.parser.views.values()
        ]
    
    def get_explores(self) -> List[Dict[str, Any]]:
        """Get list of available explores."""
        if not self.parser:
            return []
        
        return [
            {
                "name": e.name,
                "view": e.view_name,
                "joins": len(e.joins)
            }
            for e in self.parser.explores.values()
        ]


# Global instance
_lookml_service: Optional[LookMLImportService] = None


def get_lookml_service() -> LookMLImportService:
    """Get LookML import service singleton."""
    global _lookml_service
    if not _lookml_service:
        _lookml_service = LookMLImportService()
    return _lookml_service

