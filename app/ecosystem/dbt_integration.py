"""
dbt Semantic Layer Integration for SetuPranali

Import metrics, dimensions, and models from dbt projects.

Supports:
- dbt Core manifest.json parsing
- dbt Semantic Layer (MetricFlow) compatibility
- dbt Cloud API integration
- Automatic catalog generation from dbt models
"""

import os
import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class DbtColumn:
    """dbt column definition."""
    name: str
    description: Optional[str] = None
    data_type: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DbtModel:
    """dbt model definition."""
    unique_id: str
    name: str
    schema: str
    database: Optional[str] = None
    description: Optional[str] = None
    columns: List[DbtColumn] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class DbtMetric:
    """dbt metric definition (MetricFlow compatible)."""
    unique_id: str
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    type: str = "simple"  # simple, derived, cumulative, ratio
    type_params: Dict[str, Any] = field(default_factory=dict)
    filter: Optional[str] = None
    dimensions: List[str] = field(default_factory=list)
    time_grains: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class DbtSemanticModel:
    """dbt Semantic Model (MetricFlow)."""
    name: str
    model: str  # ref to dbt model
    description: Optional[str] = None
    entities: List[Dict[str, Any]] = field(default_factory=list)
    dimensions: List[Dict[str, Any]] = field(default_factory=list)
    measures: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# dbt Manifest Parser
# =============================================================================

class DbtManifestParser:
    """Parse dbt manifest.json files."""
    
    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)
        self.manifest: Dict[str, Any] = {}
        self.models: Dict[str, DbtModel] = {}
        self.metrics: Dict[str, DbtMetric] = {}
        self.semantic_models: Dict[str, DbtSemanticModel] = {}
    
    def load(self) -> None:
        """Load and parse the manifest."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        
        with open(self.manifest_path) as f:
            self.manifest = json.load(f)
        
        self._parse_models()
        self._parse_metrics()
        self._parse_semantic_models()
        
        logger.info(
            f"Loaded dbt manifest: {len(self.models)} models, "
            f"{len(self.metrics)} metrics, {len(self.semantic_models)} semantic models"
        )
    
    def _parse_models(self) -> None:
        """Parse models from manifest."""
        nodes = self.manifest.get("nodes", {})
        
        for unique_id, node in nodes.items():
            if node.get("resource_type") != "model":
                continue
            
            columns = []
            for col_name, col_data in node.get("columns", {}).items():
                columns.append(DbtColumn(
                    name=col_name,
                    description=col_data.get("description"),
                    data_type=col_data.get("data_type"),
                    meta=col_data.get("meta", {})
                ))
            
            model = DbtModel(
                unique_id=unique_id,
                name=node.get("name", ""),
                schema=node.get("schema", ""),
                database=node.get("database"),
                description=node.get("description"),
                columns=columns,
                tags=node.get("tags", []),
                meta=node.get("meta", {}),
                depends_on=node.get("depends_on", {}).get("nodes", [])
            )
            
            self.models[unique_id] = model
    
    def _parse_metrics(self) -> None:
        """Parse metrics from manifest."""
        metrics = self.manifest.get("metrics", {})
        
        for unique_id, metric_data in metrics.items():
            metric = DbtMetric(
                unique_id=unique_id,
                name=metric_data.get("name", ""),
                label=metric_data.get("label"),
                description=metric_data.get("description"),
                type=metric_data.get("type", "simple"),
                type_params=metric_data.get("type_params", {}),
                filter=metric_data.get("filter"),
                dimensions=metric_data.get("dimensions", []),
                time_grains=metric_data.get("time_grains", []),
                tags=metric_data.get("tags", [])
            )
            
            self.metrics[unique_id] = metric
    
    def _parse_semantic_models(self) -> None:
        """Parse semantic models (MetricFlow) from manifest."""
        semantic_models = self.manifest.get("semantic_models", {})
        
        for name, sm_data in semantic_models.items():
            sm = DbtSemanticModel(
                name=name,
                description=sm_data.get("description"),
                model=sm_data.get("model", ""),
                entities=sm_data.get("entities", []),
                dimensions=sm_data.get("defaults", {}).get("dimensions", []),
                measures=sm_data.get("measures", [])
            )
            
            self.semantic_models[name] = sm


# =============================================================================
# dbt Cloud Integration
# =============================================================================

class DbtCloudClient:
    """dbt Cloud API client."""
    
    def __init__(
        self,
        account_id: str,
        api_token: str,
        base_url: str = "https://cloud.getdbt.com/api/v2"
    ):
        self.account_id = account_id
        self.api_token = api_token
        self.base_url = base_url
        self.client = httpx.Client(
            headers={"Authorization": f"Token {api_token}"},
            timeout=30.0
        )
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects in the account."""
        url = f"{self.base_url}/accounts/{self.account_id}/projects/"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json().get("data", [])
    
    def get_jobs(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all jobs for a project."""
        url = f"{self.base_url}/accounts/{self.account_id}/jobs/"
        params = {"project_id": project_id}
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])
    
    def get_run_artifacts(self, run_id: int) -> Dict[str, Any]:
        """Get artifacts from a run (including manifest)."""
        url = f"{self.base_url}/accounts/{self.account_id}/runs/{run_id}/artifacts/"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json().get("data", [])
    
    def download_manifest(self, run_id: int) -> Dict[str, Any]:
        """Download manifest.json from a run."""
        url = f"{self.base_url}/accounts/{self.account_id}/runs/{run_id}/artifacts/manifest.json"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_latest_run(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get the latest successful run for a job."""
        url = f"{self.base_url}/accounts/{self.account_id}/runs/"
        params = {"job_definition_id": job_id, "status": 10, "limit": 1}  # 10 = success
        response = self.client.get(url, params=params)
        response.raise_for_status()
        runs = response.json().get("data", [])
        return runs[0] if runs else None


# =============================================================================
# Catalog Generator
# =============================================================================

class DbtCatalogGenerator:
    """Generate SetuPranali catalog from dbt artifacts."""
    
    def __init__(self, parser: DbtManifestParser):
        self.parser = parser
    
    def generate_catalog(
        self,
        include_models: Optional[List[str]] = None,
        exclude_models: Optional[List[str]] = None,
        include_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate SetuPranali catalog.yaml content."""
        
        datasets = []
        
        for unique_id, model in self.parser.models.items():
            # Filter models
            if include_models and model.name not in include_models:
                continue
            if exclude_models and model.name in exclude_models:
                continue
            if include_tags and not set(model.tags).intersection(include_tags):
                continue
            
            dataset = self._model_to_dataset(model)
            datasets.append(dataset)
        
        # Add calculated metrics from dbt metrics
        calculated_metrics = []
        for unique_id, metric in self.parser.metrics.items():
            calc_metric = self._metric_to_calculated(metric)
            if calc_metric:
                calculated_metrics.append(calc_metric)
        
        catalog = {
            "version": "1.0",
            "generated_from": "dbt",
            "generated_at": datetime.utcnow().isoformat(),
            "datasets": datasets
        }
        
        if calculated_metrics:
            catalog["calculated_metrics"] = calculated_metrics
        
        return catalog
    
    def _model_to_dataset(self, model: DbtModel) -> Dict[str, Any]:
        """Convert dbt model to SetuPranali dataset."""
        
        # Build SQL reference
        if model.database:
            sql = f"SELECT * FROM {model.database}.{model.schema}.{model.name}"
        else:
            sql = f"SELECT * FROM {model.schema}.{model.name}"
        
        # Extract dimensions and metrics from columns
        dimensions = []
        metrics = []
        
        for col in model.columns:
            col_meta = col.meta or {}
            
            # Check if column is marked as metric in meta
            if col_meta.get("is_metric") or col_meta.get("metric"):
                agg = col_meta.get("aggregation", "SUM")
                metrics.append({
                    "name": col.name,
                    "sql": f"{agg}({col.name})",
                    "description": col.description
                })
            else:
                dim = {
                    "name": col.name,
                    "sql": col.name
                }
                if col.description:
                    dim["description"] = col.description
                if col.data_type:
                    dim["type"] = self._map_data_type(col.data_type)
                dimensions.append(dim)
        
        # Look for metrics defined in dbt metrics that reference this model
        for metric_id, metric in self.parser.metrics.items():
            if model.name in str(metric.type_params.get("model", "")):
                metrics.append({
                    "name": metric.name,
                    "sql": self._metric_to_sql(metric),
                    "description": metric.description
                })
        
        dataset = {
            "id": model.name,
            "name": model.name.replace("_", " ").title(),
            "sql": sql,
            "dimensions": dimensions,
            "metrics": metrics if metrics else [{"name": "row_count", "sql": "COUNT(*)"}]
        }
        
        if model.description:
            dataset["description"] = model.description
        if model.tags:
            dataset["tags"] = model.tags
        
        return dataset
    
    def _metric_to_calculated(self, metric: DbtMetric) -> Optional[Dict[str, Any]]:
        """Convert dbt metric to calculated metric."""
        if metric.type not in ["derived", "ratio"]:
            return None
        
        return {
            "name": metric.name,
            "expression": self._build_metric_expression(metric),
            "description": metric.description
        }
    
    def _metric_to_sql(self, metric: DbtMetric) -> str:
        """Convert dbt metric to SQL."""
        type_params = metric.type_params
        
        if metric.type == "simple":
            measure = type_params.get("measure", {})
            agg = measure.get("agg", "SUM")
            expr = measure.get("expr", "1")
            return f"{agg}({expr})"
        elif metric.type == "cumulative":
            measure = type_params.get("measure", {})
            return f"SUM({measure.get('expr', '1')}) OVER (ORDER BY date)"
        else:
            return "COUNT(*)"
    
    def _build_metric_expression(self, metric: DbtMetric) -> str:
        """Build expression for derived/ratio metrics."""
        type_params = metric.type_params
        
        if metric.type == "ratio":
            numerator = type_params.get("numerator", "")
            denominator = type_params.get("denominator", "")
            return f"{{{numerator}}} / NULLIF({{{denominator}}}, 0)"
        elif metric.type == "derived":
            expr = type_params.get("expr", "")
            # Replace metric references
            return expr.replace("metric('", "{").replace("')", "}")
        
        return f"{{{metric.name}}}"
    
    def _map_data_type(self, dbt_type: str) -> str:
        """Map dbt data types to SetuPranali types."""
        type_lower = dbt_type.lower()
        
        if "int" in type_lower or "number" in type_lower:
            return "number"
        elif "date" in type_lower:
            return "date"
        elif "time" in type_lower:
            return "datetime"
        elif "bool" in type_lower:
            return "boolean"
        else:
            return "string"
    
    def save_catalog(self, output_path: str) -> None:
        """Generate and save catalog to file."""
        catalog = self.generate_catalog()
        
        with open(output_path, "w") as f:
            yaml.dump(catalog, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved dbt-generated catalog to {output_path}")


# =============================================================================
# Sync Service
# =============================================================================

class DbtSyncService:
    """Service to sync dbt artifacts with SetuPranali."""
    
    def __init__(self):
        self.parser: Optional[DbtManifestParser] = None
        self.cloud_client: Optional[DbtCloudClient] = None
    
    def configure_local(self, manifest_path: str) -> None:
        """Configure for local dbt project."""
        self.parser = DbtManifestParser(manifest_path)
        self.parser.load()
    
    def configure_cloud(
        self,
        account_id: str,
        api_token: str,
        job_id: int
    ) -> None:
        """Configure for dbt Cloud."""
        self.cloud_client = DbtCloudClient(account_id, api_token)
        
        # Get latest run
        run = self.cloud_client.get_latest_run(job_id)
        if not run:
            raise ValueError(f"No successful runs found for job {job_id}")
        
        # Download manifest
        manifest = self.cloud_client.download_manifest(run["id"])
        
        # Parse manifest
        self.parser = DbtManifestParser.__new__(DbtManifestParser)
        self.parser.manifest = manifest
        self.parser.models = {}
        self.parser.metrics = {}
        self.parser.semantic_models = {}
        self.parser._parse_models()
        self.parser._parse_metrics()
        self.parser._parse_semantic_models()
    
    def sync(
        self,
        output_path: str = "catalog.yaml",
        include_models: Optional[List[str]] = None,
        exclude_models: Optional[List[str]] = None,
        include_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sync dbt artifacts to SetuPranali catalog."""
        if not self.parser:
            raise ValueError("Configure local or cloud first")
        
        generator = DbtCatalogGenerator(self.parser)
        catalog = generator.generate_catalog(
            include_models=include_models,
            exclude_models=exclude_models,
            include_tags=include_tags
        )
        
        generator.save_catalog(output_path)
        
        return {
            "status": "synced",
            "datasets": len(catalog.get("datasets", [])),
            "calculated_metrics": len(catalog.get("calculated_metrics", [])),
            "output_path": output_path
        }
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Get list of available dbt models."""
        if not self.parser:
            return []
        
        return [
            {
                "name": m.name,
                "schema": m.schema,
                "description": m.description,
                "tags": m.tags,
                "columns": len(m.columns)
            }
            for m in self.parser.models.values()
        ]
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get list of available dbt metrics."""
        if not self.parser:
            return []
        
        return [
            {
                "name": m.name,
                "type": m.type,
                "description": m.description,
                "dimensions": m.dimensions
            }
            for m in self.parser.metrics.values()
        ]


# =============================================================================
# Global Instance
# =============================================================================

_sync_service: Optional[DbtSyncService] = None


def get_dbt_sync_service() -> DbtSyncService:
    """Get dbt sync service singleton."""
    global _sync_service
    if not _sync_service:
        _sync_service = DbtSyncService()
    return _sync_service

