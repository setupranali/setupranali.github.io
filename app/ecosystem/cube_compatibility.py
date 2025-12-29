"""
Cube.js Compatibility Layer for SetuPranali

Provides interoperability with Cube.js schemas.

Supports:
- Import Cube.js schema files (JavaScript/TypeScript)
- Export SetuPranali catalog as Cube.js schema
- Cube.js REST API compatibility mode
- Cube.js meta API emulation
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Cube.js Schema Models
# =============================================================================

@dataclass
class CubeDimension:
    """Cube.js dimension definition."""
    name: str
    sql: str
    type: str = "string"  # string, number, time, boolean, geo
    title: Optional[str] = None
    description: Optional[str] = None
    primary_key: bool = False
    shown: bool = True
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CubeMeasure:
    """Cube.js measure definition."""
    name: str
    sql: str
    type: str = "count"  # count, countDistinct, sum, avg, min, max, number
    title: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    rolling_window: Optional[Dict[str, Any]] = None
    filters: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CubeJoin:
    """Cube.js join definition."""
    name: str
    relationship: str  # belongsTo, hasOne, hasMany
    sql: str


@dataclass
class CubeDefinition:
    """Cube.js cube definition."""
    name: str
    sql: Optional[str] = None
    sql_table: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    dimensions: List[CubeDimension] = field(default_factory=list)
    measures: List[CubeMeasure] = field(default_factory=list)
    joins: List[CubeJoin] = field(default_factory=list)
    pre_aggregations: List[Dict[str, Any]] = field(default_factory=list)
    segments: List[Dict[str, Any]] = field(default_factory=list)
    data_source: Optional[str] = None


# =============================================================================
# Cube.js Schema Parser
# =============================================================================

class CubeSchemaParser:
    """Parse Cube.js schema files."""
    
    # Regex patterns for parsing JavaScript cube definitions
    CUBE_PATTERN = re.compile(
        r'cube\s*\(\s*[`\'"]([^`\'"]+)[`\'"]\s*,\s*\{(.*?)\}\s*\)',
        re.DOTALL
    )
    
    PROPERTY_PATTERN = re.compile(
        r'(\w+)\s*:\s*(?:([`\'"])([^`\'"]*)\2|(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})|(\[[^\[\]]*\])|([^,\n]+))',
        re.DOTALL
    )
    
    def __init__(self, schema_path: str):
        self.schema_path = Path(schema_path)
        self.cubes: Dict[str, CubeDefinition] = {}
    
    def load(self) -> None:
        """Load and parse Cube.js schema files."""
        if self.schema_path.is_file():
            self._parse_file(self.schema_path)
        elif self.schema_path.is_dir():
            for file in self.schema_path.glob("**/*.js"):
                self._parse_file(file)
            for file in self.schema_path.glob("**/*.ts"):
                self._parse_file(file)
        else:
            raise FileNotFoundError(f"Schema path not found: {self.schema_path}")
        
        logger.info(f"Loaded {len(self.cubes)} Cube.js cubes")
    
    def _parse_file(self, file_path: Path) -> None:
        """Parse a single Cube.js schema file."""
        try:
            content = file_path.read_text()
            
            # Find all cube definitions
            for match in self.CUBE_PATTERN.finditer(content):
                cube_name = match.group(1)
                cube_body = match.group(2)
                
                cube = self._parse_cube_body(cube_name, cube_body)
                self.cubes[cube_name] = cube
                
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
    
    def _parse_cube_body(self, name: str, body: str) -> CubeDefinition:
        """Parse cube body content."""
        cube = CubeDefinition(name=name)
        
        # Extract sql or sqlTable
        sql_match = re.search(r'sql\s*:\s*`([^`]*)`', body)
        if sql_match:
            cube.sql = sql_match.group(1)
        
        sql_table_match = re.search(r'sqlTable\s*:\s*`([^`]*)`', body)
        if sql_table_match:
            cube.sql_table = sql_table_match.group(1)
        
        # Extract title and description
        title_match = re.search(r'title\s*:\s*[`\'"]([^`\'"]*)[`\'"]', body)
        if title_match:
            cube.title = title_match.group(1)
        
        desc_match = re.search(r'description\s*:\s*[`\'"]([^`\'"]*)[`\'"]', body)
        if desc_match:
            cube.description = desc_match.group(1)
        
        # Extract dimensions
        dims_match = re.search(r'dimensions\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', body)
        if dims_match:
            cube.dimensions = self._parse_dimensions(dims_match.group(1))
        
        # Extract measures
        measures_match = re.search(r'measures\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', body)
        if measures_match:
            cube.measures = self._parse_measures(measures_match.group(1))
        
        # Extract joins
        joins_match = re.search(r'joins\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', body)
        if joins_match:
            cube.joins = self._parse_joins(joins_match.group(1))
        
        return cube
    
    def _parse_dimensions(self, content: str) -> List[CubeDimension]:
        """Parse dimensions block."""
        dimensions = []
        
        # Match dimension definitions
        dim_pattern = re.compile(r'(\w+)\s*:\s*\{([^}]*)\}', re.DOTALL)
        
        for match in dim_pattern.finditer(content):
            name = match.group(1)
            body = match.group(2)
            
            dim = CubeDimension(name=name, sql=name)
            
            # Extract sql
            sql_match = re.search(r'sql\s*:\s*`([^`]*)`', body)
            if sql_match:
                dim.sql = sql_match.group(1)
            
            # Extract type
            type_match = re.search(r'type\s*:\s*[`\'"]?(\w+)[`\'"]?', body)
            if type_match:
                dim.type = type_match.group(1)
            
            # Extract title
            title_match = re.search(r'title\s*:\s*[`\'"]([^`\'"]*)[`\'"]', body)
            if title_match:
                dim.title = title_match.group(1)
            
            # Extract primaryKey
            if 'primaryKey: true' in body:
                dim.primary_key = True
            
            dimensions.append(dim)
        
        return dimensions
    
    def _parse_measures(self, content: str) -> List[CubeMeasure]:
        """Parse measures block."""
        measures = []
        
        measure_pattern = re.compile(r'(\w+)\s*:\s*\{([^}]*)\}', re.DOTALL)
        
        for match in measure_pattern.finditer(content):
            name = match.group(1)
            body = match.group(2)
            
            measure = CubeMeasure(name=name, sql="*", type="count")
            
            # Extract sql
            sql_match = re.search(r'sql\s*:\s*`([^`]*)`', body)
            if sql_match:
                measure.sql = sql_match.group(1)
            
            # Extract type
            type_match = re.search(r'type\s*:\s*[`\'"]?(\w+)[`\'"]?', body)
            if type_match:
                measure.type = type_match.group(1)
            
            # Extract title
            title_match = re.search(r'title\s*:\s*[`\'"]([^`\'"]*)[`\'"]', body)
            if title_match:
                measure.title = title_match.group(1)
            
            measures.append(measure)
        
        return measures
    
    def _parse_joins(self, content: str) -> List[CubeJoin]:
        """Parse joins block."""
        joins = []
        
        join_pattern = re.compile(r'(\w+)\s*:\s*\{([^}]*)\}', re.DOTALL)
        
        for match in join_pattern.finditer(content):
            name = match.group(1)
            body = match.group(2)
            
            relationship = "belongsTo"
            rel_match = re.search(r'relationship\s*:\s*[`\'"]?(\w+)[`\'"]?', body)
            if rel_match:
                relationship = rel_match.group(1)
            
            sql = ""
            sql_match = re.search(r'sql\s*:\s*`([^`]*)`', body)
            if sql_match:
                sql = sql_match.group(1)
            
            joins.append(CubeJoin(name=name, relationship=relationship, sql=sql))
        
        return joins


# =============================================================================
# Cube.js to SetuPranali Converter
# =============================================================================

class CubeToSetuPranaliConverter:
    """Convert Cube.js schemas to SetuPranali catalog."""
    
    MEASURE_TYPE_MAP = {
        "count": "COUNT(*)",
        "countDistinct": "COUNT(DISTINCT {sql})",
        "sum": "SUM({sql})",
        "avg": "AVG({sql})",
        "min": "MIN({sql})",
        "max": "MAX({sql})",
        "number": "{sql}",
        "countDistinctApprox": "APPROX_COUNT_DISTINCT({sql})"
    }
    
    DIMENSION_TYPE_MAP = {
        "string": "string",
        "number": "number",
        "time": "datetime",
        "boolean": "boolean",
        "geo": "string"
    }
    
    def __init__(self, parser: CubeSchemaParser):
        self.parser = parser
    
    def convert(self) -> Dict[str, Any]:
        """Convert all cubes to SetuPranali catalog."""
        datasets = []
        joins = []
        
        for cube in self.parser.cubes.values():
            dataset = self._convert_cube(cube)
            datasets.append(dataset)
            
            # Convert joins
            for join in cube.joins:
                joins.append(self._convert_join(cube.name, join))
        
        catalog = {
            "version": "1.0",
            "generated_from": "cube.js",
            "generated_at": datetime.utcnow().isoformat(),
            "datasets": datasets
        }
        
        if joins:
            catalog["joins"] = joins
        
        return catalog
    
    def _convert_cube(self, cube: CubeDefinition) -> Dict[str, Any]:
        """Convert a Cube.js cube to SetuPranali dataset."""
        # Build SQL
        if cube.sql:
            sql = cube.sql
        elif cube.sql_table:
            sql = f"SELECT * FROM {cube.sql_table}"
        else:
            sql = f"SELECT * FROM {cube.name}"
        
        # Convert dimensions
        dimensions = []
        for dim in cube.dimensions:
            d = {
                "name": dim.name,
                "sql": self._clean_sql_reference(dim.sql, cube.name)
            }
            if dim.title:
                d["description"] = dim.title
            if dim.type:
                d["type"] = self.DIMENSION_TYPE_MAP.get(dim.type, "string")
            dimensions.append(d)
        
        # Convert measures
        metrics = []
        for measure in cube.measures:
            sql_template = self.MEASURE_TYPE_MAP.get(measure.type, "{sql}")
            sql_expr = sql_template.replace(
                "{sql}",
                self._clean_sql_reference(measure.sql, cube.name)
            )
            
            m = {
                "name": measure.name,
                "sql": sql_expr
            }
            if measure.title:
                m["description"] = measure.title
            metrics.append(m)
        
        dataset = {
            "id": cube.name.lower(),
            "name": cube.title or cube.name,
            "sql": sql,
            "dimensions": dimensions,
            "metrics": metrics if metrics else [{"name": "count", "sql": "COUNT(*)"}]
        }
        
        if cube.description:
            dataset["description"] = cube.description
        
        return dataset
    
    def _convert_join(self, cube_name: str, join: CubeJoin) -> Dict[str, Any]:
        """Convert Cube.js join to SetuPranali join."""
        # Map relationship to join type
        join_type_map = {
            "belongsTo": "left",
            "hasOne": "left",
            "hasMany": "left"
        }
        
        return {
            "left_dataset": cube_name.lower(),
            "right_dataset": join.name.lower(),
            "join_type": join_type_map.get(join.relationship, "left"),
            "sql": join.sql,
            "cardinality": self._relationship_to_cardinality(join.relationship)
        }
    
    def _relationship_to_cardinality(self, relationship: str) -> str:
        """Convert Cube.js relationship to cardinality."""
        mapping = {
            "belongsTo": "many-to-one",
            "hasOne": "one-to-one",
            "hasMany": "one-to-many"
        }
        return mapping.get(relationship, "many-to-one")
    
    def _clean_sql_reference(self, sql: str, cube_name: str) -> str:
        """Clean SQL references from Cube.js format."""
        # Remove ${CUBE} references
        sql = sql.replace("${CUBE}", cube_name)
        sql = re.sub(r'\$\{([^}]+)\}', r'\1', sql)
        return sql
    
    def save_catalog(self, output_path: str) -> None:
        """Generate and save catalog to file."""
        catalog = self.convert()
        
        with open(output_path, "w") as f:
            yaml.dump(catalog, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved Cube.js-converted catalog to {output_path}")


# =============================================================================
# SetuPranali to Cube.js Exporter
# =============================================================================

class SetuPranaliToCubeExporter:
    """Export SetuPranali catalog to Cube.js schema."""
    
    def __init__(self, catalog_path: str):
        self.catalog_path = Path(catalog_path)
        self.catalog: Dict[str, Any] = {}
    
    def load(self) -> None:
        """Load SetuPranali catalog."""
        with open(self.catalog_path) as f:
            self.catalog = yaml.safe_load(f)
    
    def export(self, output_dir: str) -> None:
        """Export catalog to Cube.js schema files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for dataset in self.catalog.get("datasets", []):
            cube_content = self._dataset_to_cube(dataset)
            
            file_path = output_path / f"{dataset['id']}.js"
            file_path.write_text(cube_content)
        
        logger.info(f"Exported {len(self.catalog.get('datasets', []))} cubes to {output_dir}")
    
    def _dataset_to_cube(self, dataset: Dict[str, Any]) -> str:
        """Convert dataset to Cube.js schema."""
        cube_name = dataset["id"].title().replace("_", "")
        
        lines = [f"cube(`{cube_name}`, {{"]
        
        # SQL
        sql = dataset.get("sql", f"SELECT * FROM {dataset['id']}")
        lines.append(f"  sql: `{sql}`,")
        
        # Title
        if dataset.get("name"):
            lines.append(f'  title: `{dataset["name"]}`,')
        
        # Description
        if dataset.get("description"):
            lines.append(f'  description: `{dataset["description"]}`,')
        
        # Dimensions
        if dataset.get("dimensions"):
            lines.append("  dimensions: {")
            for dim in dataset["dimensions"]:
                lines.append(f"    {dim['name']}: {{")
                lines.append(f"      sql: `{dim.get('sql', dim['name'])}`,")
                dim_type = self._map_to_cube_type(dim.get("type", "string"))
                lines.append(f"      type: `{dim_type}`")
                lines.append("    },")
            lines.append("  },")
        
        # Measures
        if dataset.get("metrics"):
            lines.append("  measures: {")
            for metric in dataset["metrics"]:
                measure_type, sql = self._parse_metric_sql(metric.get("sql", "COUNT(*)"))
                lines.append(f"    {metric['name']}: {{")
                lines.append(f"      sql: `{sql}`,")
                lines.append(f"      type: `{measure_type}`")
                lines.append("    },")
            lines.append("  }")
        
        lines.append("});")
        
        return "\n".join(lines)
    
    def _map_to_cube_type(self, setu_type: str) -> str:
        """Map SetuPranali type to Cube.js type."""
        mapping = {
            "string": "string",
            "number": "number",
            "date": "time",
            "datetime": "time",
            "boolean": "boolean"
        }
        return mapping.get(setu_type, "string")
    
    def _parse_metric_sql(self, sql: str) -> tuple:
        """Parse metric SQL to determine Cube.js measure type."""
        sql_upper = sql.upper()
        
        if sql_upper.startswith("COUNT(DISTINCT"):
            return "countDistinct", re.sub(r'COUNT\s*\(\s*DISTINCT\s*', '', sql, flags=re.I).rstrip(')')
        elif sql_upper.startswith("COUNT"):
            return "count", "*"
        elif sql_upper.startswith("SUM"):
            return "sum", re.sub(r'SUM\s*\(', '', sql, flags=re.I).rstrip(')')
        elif sql_upper.startswith("AVG"):
            return "avg", re.sub(r'AVG\s*\(', '', sql, flags=re.I).rstrip(')')
        elif sql_upper.startswith("MIN"):
            return "min", re.sub(r'MIN\s*\(', '', sql, flags=re.I).rstrip(')')
        elif sql_upper.startswith("MAX"):
            return "max", re.sub(r'MAX\s*\(', '', sql, flags=re.I).rstrip(')')
        else:
            return "number", sql


# =============================================================================
# Cube.js API Compatibility
# =============================================================================

class CubeApiEmulator:
    """Emulate Cube.js REST API for compatibility."""
    
    def __init__(self, catalog: Dict[str, Any]):
        self.catalog = catalog
    
    def get_meta(self) -> Dict[str, Any]:
        """Return Cube.js compatible meta response."""
        cubes = []
        
        for dataset in self.catalog.get("datasets", []):
            cube = {
                "name": dataset["id"].title().replace("_", ""),
                "title": dataset.get("name", dataset["id"]),
                "measures": [
                    {
                        "name": f"{dataset['id'].title().replace('_', '')}.{m['name']}",
                        "title": m.get("description", m["name"]),
                        "shortTitle": m["name"],
                        "type": self._infer_measure_type(m.get("sql", "")),
                        "aggType": self._infer_agg_type(m.get("sql", ""))
                    }
                    for m in dataset.get("metrics", [])
                ],
                "dimensions": [
                    {
                        "name": f"{dataset['id'].title().replace('_', '')}.{d['name']}",
                        "title": d.get("description", d["name"]),
                        "shortTitle": d["name"],
                        "type": self._map_dimension_type(d.get("type", "string"))
                    }
                    for d in dataset.get("dimensions", [])
                ],
                "segments": []
            }
            cubes.append(cube)
        
        return {"cubes": cubes}
    
    def _infer_measure_type(self, sql: str) -> str:
        """Infer measure type from SQL."""
        sql_upper = sql.upper()
        if "COUNT" in sql_upper:
            return "number"
        elif "SUM" in sql_upper or "AVG" in sql_upper:
            return "number"
        return "number"
    
    def _infer_agg_type(self, sql: str) -> str:
        """Infer aggregation type from SQL."""
        sql_upper = sql.upper()
        if sql_upper.startswith("COUNT(DISTINCT"):
            return "countDistinct"
        elif sql_upper.startswith("COUNT"):
            return "count"
        elif sql_upper.startswith("SUM"):
            return "sum"
        elif sql_upper.startswith("AVG"):
            return "avg"
        return "number"
    
    def _map_dimension_type(self, setu_type: str) -> str:
        """Map to Cube.js dimension type."""
        mapping = {
            "string": "string",
            "number": "number",
            "date": "time",
            "datetime": "time",
            "boolean": "boolean"
        }
        return mapping.get(setu_type, "string")


# =============================================================================
# Global Service
# =============================================================================

_cube_service: Optional["CubeCompatibilityService"] = None


class CubeCompatibilityService:
    """Service for Cube.js compatibility operations."""
    
    def __init__(self):
        self.parser: Optional[CubeSchemaParser] = None
        self.catalog: Optional[Dict[str, Any]] = None
    
    def import_cube_schema(self, schema_path: str) -> Dict[str, Any]:
        """Import Cube.js schema to SetuPranali catalog."""
        self.parser = CubeSchemaParser(schema_path)
        self.parser.load()
        
        converter = CubeToSetuPranaliConverter(self.parser)
        self.catalog = converter.convert()
        
        return {
            "status": "imported",
            "cubes": len(self.parser.cubes),
            "datasets": len(self.catalog.get("datasets", []))
        }
    
    def export_to_cube(self, catalog_path: str, output_dir: str) -> Dict[str, Any]:
        """Export SetuPranali catalog to Cube.js schema."""
        exporter = SetuPranaliToCubeExporter(catalog_path)
        exporter.load()
        exporter.export(output_dir)
        
        return {
            "status": "exported",
            "datasets": len(exporter.catalog.get("datasets", [])),
            "output_dir": output_dir
        }
    
    def get_cube_meta(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        """Get Cube.js compatible meta response."""
        emulator = CubeApiEmulator(catalog)
        return emulator.get_meta()


def get_cube_service() -> CubeCompatibilityService:
    """Get Cube.js compatibility service singleton."""
    global _cube_service
    if not _cube_service:
        _cube_service = CubeCompatibilityService()
    return _cube_service

