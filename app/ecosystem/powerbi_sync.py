"""
Power BI Dataset Sync for SetuPranali

Sync semantic models to Power BI Service.

Supports:
- Push datasets to Power BI Service
- Refresh dataset triggers
- Dataset schema updates
- Row-level security sync
- Gateway configuration
"""

import os
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import httpx
import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class PowerBIDataType(str, Enum):
    """Power BI data types."""
    STRING = "String"
    INT64 = "Int64"
    DOUBLE = "Double"
    DATETIME = "DateTime"
    BOOLEAN = "Boolean"
    DECIMAL = "Decimal"


@dataclass
class PowerBIColumn:
    """Power BI column definition."""
    name: str
    dataType: str
    formatString: Optional[str] = None
    isHidden: bool = False


@dataclass
class PowerBIMeasure:
    """Power BI measure definition."""
    name: str
    expression: str
    formatString: Optional[str] = None
    description: Optional[str] = None
    isHidden: bool = False


@dataclass
class PowerBITable:
    """Power BI table definition."""
    name: str
    columns: List[PowerBIColumn] = field(default_factory=list)
    measures: List[PowerBIMeasure] = field(default_factory=list)
    isHidden: bool = False


@dataclass
class PowerBIRelationship:
    """Power BI relationship definition."""
    name: str
    fromTable: str
    fromColumn: str
    toTable: str
    toColumn: str
    crossFilteringBehavior: str = "oneDirection"  # oneDirection, bothDirections
    isActive: bool = True


@dataclass
class PowerBIDataset:
    """Power BI dataset definition."""
    name: str
    tables: List[PowerBITable] = field(default_factory=list)
    relationships: List[PowerBIRelationship] = field(default_factory=list)
    defaultMode: str = "Push"  # Push, Streaming, PushStreaming


# =============================================================================
# Power BI REST API Client
# =============================================================================

class PowerBIClient:
    """Power BI REST API client."""
    
    BASE_URL = "https://api.powerbi.com/v1.0/myorg"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        workspace_id: Optional[str] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self._access_token: Optional[str] = None
        self._token_expires: float = 0
        self.client = httpx.Client(timeout=30.0)
    
    def _get_token(self) -> str:
        """Get OAuth access token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token
        
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        response = self.client.post(url, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://analysis.windows.net/powerbi/api/.default"
        })
        response.raise_for_status()
        
        data = response.json()
        self._access_token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 3600) - 60
        
        return self._access_token
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make authenticated request."""
        token = self._get_token()
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        
        url = f"{self.BASE_URL}{endpoint}"
        if self.workspace_id:
            url = url.replace("/myorg/", f"/myorg/groups/{self.workspace_id}/")
        
        response = self.client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        
        return response
    
    # =========================================================================
    # Workspaces
    # =========================================================================
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces."""
        response = self._request("GET", "/groups")
        return response.json().get("value", [])
    
    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace details."""
        response = self._request("GET", f"/groups/{workspace_id}")
        return response.json()
    
    # =========================================================================
    # Datasets
    # =========================================================================
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get all datasets in workspace."""
        response = self._request("GET", "/datasets")
        return response.json().get("value", [])
    
    def get_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset details."""
        response = self._request("GET", f"/datasets/{dataset_id}")
        return response.json()
    
    def create_dataset(self, dataset: PowerBIDataset) -> Dict[str, Any]:
        """Create a push dataset."""
        payload = self._dataset_to_payload(dataset)
        
        response = self._request(
            "POST",
            "/datasets",
            json=payload,
            params={"defaultRetentionPolicy": "basicFIFO"}
        )
        
        return response.json()
    
    def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset."""
        self._request("DELETE", f"/datasets/{dataset_id}")
    
    def refresh_dataset(self, dataset_id: str) -> None:
        """Trigger dataset refresh."""
        self._request("POST", f"/datasets/{dataset_id}/refreshes")
    
    def get_refresh_history(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get dataset refresh history."""
        response = self._request("GET", f"/datasets/{dataset_id}/refreshes")
        return response.json().get("value", [])
    
    # =========================================================================
    # Tables
    # =========================================================================
    
    def get_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get tables in a dataset."""
        response = self._request("GET", f"/datasets/{dataset_id}/tables")
        return response.json().get("value", [])
    
    def update_table_schema(
        self,
        dataset_id: str,
        table_name: str,
        columns: List[PowerBIColumn]
    ) -> None:
        """Update table schema."""
        payload = {
            "name": table_name,
            "columns": [
                {
                    "name": col.name,
                    "dataType": col.dataType
                }
                for col in columns
            ]
        }
        
        self._request(
            "PUT",
            f"/datasets/{dataset_id}/tables/{table_name}",
            json=payload
        )
    
    # =========================================================================
    # Rows
    # =========================================================================
    
    def push_rows(
        self,
        dataset_id: str,
        table_name: str,
        rows: List[Dict[str, Any]]
    ) -> None:
        """Push rows to a table."""
        payload = {"rows": rows}
        
        self._request(
            "POST",
            f"/datasets/{dataset_id}/tables/{table_name}/rows",
            json=payload
        )
    
    def delete_rows(self, dataset_id: str, table_name: str) -> None:
        """Delete all rows from a table."""
        self._request(
            "DELETE",
            f"/datasets/{dataset_id}/tables/{table_name}/rows"
        )
    
    # =========================================================================
    # Row-Level Security
    # =========================================================================
    
    def get_dataset_users(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get dataset users."""
        response = self._request("GET", f"/datasets/{dataset_id}/users")
        return response.json().get("value", [])
    
    def add_dataset_user(
        self,
        dataset_id: str,
        email: str,
        access_right: str = "Read"  # Read, ReadWrite, Admin
    ) -> None:
        """Add user to dataset."""
        payload = {
            "emailAddress": email,
            "datasetUserAccessRight": access_right
        }
        
        self._request("POST", f"/datasets/{dataset_id}/users", json=payload)
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _dataset_to_payload(self, dataset: PowerBIDataset) -> Dict[str, Any]:
        """Convert dataset to API payload."""
        return {
            "name": dataset.name,
            "defaultMode": dataset.defaultMode,
            "tables": [
                {
                    "name": table.name,
                    "columns": [
                        {
                            "name": col.name,
                            "dataType": col.dataType,
                            "formatString": col.formatString
                        }
                        for col in table.columns
                    ],
                    "measures": [
                        {
                            "name": measure.name,
                            "expression": measure.expression,
                            "formatString": measure.formatString
                        }
                        for measure in table.measures
                    ] if table.measures else []
                }
                for table in dataset.tables
            ],
            "relationships": [
                {
                    "name": rel.name,
                    "fromTable": rel.fromTable,
                    "fromColumn": rel.fromColumn,
                    "toTable": rel.toTable,
                    "toColumn": rel.toColumn,
                    "crossFilteringBehavior": rel.crossFilteringBehavior
                }
                for rel in dataset.relationships
            ] if dataset.relationships else []
        }


# =============================================================================
# SetuPranali to Power BI Converter
# =============================================================================

class SetuPranaliToPowerBIConverter:
    """Convert SetuPranali catalog to Power BI dataset."""
    
    TYPE_MAP = {
        "string": PowerBIDataType.STRING,
        "number": PowerBIDataType.DOUBLE,
        "integer": PowerBIDataType.INT64,
        "date": PowerBIDataType.DATETIME,
        "datetime": PowerBIDataType.DATETIME,
        "boolean": PowerBIDataType.BOOLEAN,
        "decimal": PowerBIDataType.DECIMAL
    }
    
    def __init__(self, catalog_path: str):
        self.catalog_path = catalog_path
        self.catalog: Dict[str, Any] = {}
    
    def load(self) -> None:
        """Load SetuPranali catalog."""
        with open(self.catalog_path) as f:
            self.catalog = yaml.safe_load(f)
    
    def convert(self, dataset_name: Optional[str] = None) -> PowerBIDataset:
        """Convert catalog to Power BI dataset."""
        name = dataset_name or self.catalog.get("name", "SetuPranali Dataset")
        
        tables = []
        relationships = []
        
        for ds in self.catalog.get("datasets", []):
            table = self._convert_dataset(ds)
            tables.append(table)
        
        # Convert joins to relationships
        for join in self.catalog.get("joins", []):
            rel = self._convert_join(join)
            if rel:
                relationships.append(rel)
        
        return PowerBIDataset(
            name=name,
            tables=tables,
            relationships=relationships,
            defaultMode="Push"
        )
    
    def _convert_dataset(self, dataset: Dict[str, Any]) -> PowerBITable:
        """Convert dataset to Power BI table."""
        columns = []
        measures = []
        
        # Convert dimensions to columns
        for dim in dataset.get("dimensions", []):
            col_type = self.TYPE_MAP.get(
                dim.get("type", "string"),
                PowerBIDataType.STRING
            )
            
            columns.append(PowerBIColumn(
                name=dim["name"],
                dataType=col_type.value
            ))
        
        # Convert metrics to measures
        for metric in dataset.get("metrics", []):
            # Create DAX expression
            dax = self._sql_to_dax(metric.get("sql", ""))
            
            measures.append(PowerBIMeasure(
                name=metric["name"],
                expression=dax,
                description=metric.get("description")
            ))
        
        return PowerBITable(
            name=dataset["id"],
            columns=columns,
            measures=measures
        )
    
    def _convert_join(self, join: Dict[str, Any]) -> Optional[PowerBIRelationship]:
        """Convert join to Power BI relationship."""
        left_key = join.get("left_key")
        right_key = join.get("right_key")
        
        if not left_key or not right_key:
            return None
        
        # Map cardinality to cross-filter behavior
        cardinality = join.get("cardinality", "many-to-one")
        cross_filter = "oneDirection"
        if cardinality in ["one-to-one", "many-to-many"]:
            cross_filter = "bothDirections"
        
        return PowerBIRelationship(
            name=f"{join['left_dataset']}_{join['right_dataset']}",
            fromTable=join["left_dataset"],
            fromColumn=left_key,
            toTable=join["right_dataset"],
            toColumn=right_key,
            crossFilteringBehavior=cross_filter
        )
    
    def _sql_to_dax(self, sql: str) -> str:
        """Convert SQL aggregation to DAX."""
        sql_upper = sql.upper().strip()
        
        if sql_upper.startswith("COUNT(DISTINCT"):
            col = sql[15:-1].strip()
            return f"DISTINCTCOUNT([{col}])"
        elif sql_upper.startswith("COUNT("):
            return "COUNTROWS()"
        elif sql_upper.startswith("SUM("):
            col = sql[4:-1].strip()
            return f"SUM([{col}])"
        elif sql_upper.startswith("AVG("):
            col = sql[4:-1].strip()
            return f"AVERAGE([{col}])"
        elif sql_upper.startswith("MIN("):
            col = sql[4:-1].strip()
            return f"MIN([{col}])"
        elif sql_upper.startswith("MAX("):
            col = sql[4:-1].strip()
            return f"MAX([{col}])"
        else:
            return sql


# =============================================================================
# Sync Service
# =============================================================================

class PowerBISyncService:
    """Service for syncing SetuPranali to Power BI."""
    
    def __init__(self):
        self.client: Optional[PowerBIClient] = None
        self.converter: Optional[SetuPranaliToPowerBIConverter] = None
    
    def configure(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        workspace_id: Optional[str] = None
    ) -> None:
        """Configure Power BI connection."""
        self.client = PowerBIClient(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            workspace_id=workspace_id
        )
    
    def sync_catalog(
        self,
        catalog_path: str,
        dataset_name: Optional[str] = None,
        replace_existing: bool = False
    ) -> Dict[str, Any]:
        """Sync SetuPranali catalog to Power BI."""
        if not self.client:
            raise ValueError("Configure Power BI connection first")
        
        # Load and convert catalog
        self.converter = SetuPranaliToPowerBIConverter(catalog_path)
        self.converter.load()
        
        pbi_dataset = self.converter.convert(dataset_name)
        
        # Check for existing dataset
        existing = None
        if replace_existing:
            for ds in self.client.get_datasets():
                if ds["name"] == pbi_dataset.name:
                    existing = ds
                    break
            
            if existing:
                self.client.delete_dataset(existing["id"])
        
        # Create dataset
        result = self.client.create_dataset(pbi_dataset)
        
        return {
            "status": "synced",
            "dataset_id": result.get("id"),
            "dataset_name": pbi_dataset.name,
            "tables": len(pbi_dataset.tables),
            "relationships": len(pbi_dataset.relationships),
            "replaced_existing": existing is not None
        }
    
    def push_data(
        self,
        dataset_id: str,
        table_name: str,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Push data to Power BI dataset."""
        if not self.client:
            raise ValueError("Configure Power BI connection first")
        
        # Push in batches of 10,000 rows
        batch_size = 10000
        total_rows = len(data)
        batches_pushed = 0
        
        for i in range(0, total_rows, batch_size):
            batch = data[i:i + batch_size]
            self.client.push_rows(dataset_id, table_name, batch)
            batches_pushed += 1
        
        return {
            "status": "pushed",
            "total_rows": total_rows,
            "batches": batches_pushed
        }
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get available workspaces."""
        if not self.client:
            raise ValueError("Configure Power BI connection first")
        
        return self.client.get_workspaces()
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get datasets in workspace."""
        if not self.client:
            raise ValueError("Configure Power BI connection first")
        
        return self.client.get_datasets()
    
    def refresh_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Trigger dataset refresh."""
        if not self.client:
            raise ValueError("Configure Power BI connection first")
        
        self.client.refresh_dataset(dataset_id)
        
        return {
            "status": "refresh_triggered",
            "dataset_id": dataset_id
        }


# Global instance
_powerbi_service: Optional[PowerBISyncService] = None


def get_powerbi_service() -> PowerBISyncService:
    """Get Power BI sync service singleton."""
    global _powerbi_service
    if not _powerbi_service:
        _powerbi_service = PowerBISyncService()
    return _powerbi_service

