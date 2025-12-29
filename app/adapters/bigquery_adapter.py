"""
BigQuery Adapter for SetuPranali

Google BigQuery is ideal for:
- TB to PB scale analytics
- Serverless architecture (no infrastructure to manage)
- Cost-effective with on-demand pricing
- Native ML and geospatial support

Features:
- Service account authentication
- Application default credentials support
- Query result caching (BigQuery-side)
- Dry run support for cost estimation
- Location-aware queries
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from google.api_core.exceptions import GoogleAPIError
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    bigquery = None
    service_account = None

from app.adapters.base import BaseAdapter, AdapterResult, ConnectionError, QueryError

logger = logging.getLogger(__name__)


class BigQueryAdapter(BaseAdapter):
    """
    Adapter for Google BigQuery.
    
    Config options:
        project: GCP project ID (required)
        
        # Authentication (one of these required)
        credentials_path: Path to service account JSON key file
        credentials_json: Service account JSON as string
        credentials_dict: Service account credentials as dict
        # If none provided, uses Application Default Credentials (ADC)
        
        # Optional settings
        location: Default dataset location (default: US)
        dataset: Default dataset name
        timeout: Query timeout in seconds (default: 300)
        max_results: Maximum results per page (default: 10000)
        use_legacy_sql: Use legacy SQL syntax (default: False)
        
        # Cost control
        maximum_bytes_billed: Max bytes to scan (prevents runaway queries)
        dry_run: If True, estimate cost without running (default: False)
        
        # Labels for billing/tracking
        labels: Dict of labels to attach to queries
    
    Example:
        # Using service account file
        adapter = BigQueryAdapter({
            "project": "my-gcp-project",
            "credentials_path": "/path/to/service-account.json",
            "location": "US",
            "dataset": "analytics"
        })
        
        # Using Application Default Credentials
        adapter = BigQueryAdapter({
            "project": "my-gcp-project"
        })
        
        adapter.connect()
        result = adapter.execute(
            "SELECT * FROM `my-project.analytics.orders` WHERE tenant_id = ?",
            ["tenant_a"]
        )
    """
    
    ENGINE = "bigquery"
    PLACEHOLDER = "@param"  # BigQuery uses named parameters
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize BigQuery adapter."""
        super().__init__(config)
        
        if not BIGQUERY_AVAILABLE:
            raise ConnectionError(
                "google-cloud-bigquery not installed. "
                "Run: pip install google-cloud-bigquery google-cloud-bigquery-storage",
                engine=self.ENGINE
            )
        
        # Validate required config
        if "project" not in config:
            raise ConnectionError(
                "Missing required config: project",
                engine=self.ENGINE
            )
        
        # Store config
        self.project = config["project"]
        self.location = config.get("location", "US")
        self.dataset = config.get("dataset")
        self.timeout = config.get("timeout", 300)
        self.max_results = config.get("max_results", 10000)
        self.use_legacy_sql = config.get("use_legacy_sql", False)
        self.maximum_bytes_billed = config.get("maximum_bytes_billed")
        self.dry_run = config.get("dry_run", False)
        self.labels = config.get("labels", {"source": "universal_bi_connector"})
        
        # Credentials options
        self.credentials_path = config.get("credentials_path")
        self.credentials_json = config.get("credentials_json")
        self.credentials_dict = config.get("credentials_dict")
        
        self._client = None
    
    def _build_credentials(self):
        """Build credentials from config."""
        if self.credentials_path:
            # Load from file
            return service_account.Credentials.from_service_account_file(
                self.credentials_path
            )
        elif self.credentials_json:
            # Parse JSON string
            import json
            creds_dict = json.loads(self.credentials_json)
            return service_account.Credentials.from_service_account_info(creds_dict)
        elif self.credentials_dict:
            # Use dict directly
            return service_account.Credentials.from_service_account_info(
                self.credentials_dict
            )
        else:
            # Use Application Default Credentials
            return None
    
    def connect(self) -> None:
        """Connect to BigQuery."""
        try:
            credentials = self._build_credentials()
            
            logger.info(f"Connecting to BigQuery: project={self.project}")
            
            self._client = bigquery.Client(
                project=self.project,
                credentials=credentials,
                location=self.location
            )
            
            # Test connection by getting project info
            self._client.get_service_account_email()
            
            self._connected = True
            logger.info(f"BigQuery connected: {self.project} (location: {self.location})")
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to BigQuery: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def disconnect(self) -> None:
        """Close BigQuery client."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing BigQuery client: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def convert_placeholders(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[str, List[bigquery.ScalarQueryParameter]]:
        """
        Convert ? placeholders to BigQuery named parameters.
        
        BigQuery uses @param_name syntax for parameters.
        We convert positional ? to @p0, @p1, @p2, etc.
        
        Returns:
            (converted_sql, list of BigQuery query parameters)
        """
        if not params:
            return sql, []
        
        bq_params = []
        param_index = 0
        converted_sql = ""
        i = 0
        
        while i < len(sql):
            if sql[i] == '?':
                param_name = f"p{param_index}"
                converted_sql += f"@{param_name}"
                
                # Determine parameter type
                value = params[param_index]
                param_type = self._infer_bq_type(value)
                
                bq_params.append(
                    bigquery.ScalarQueryParameter(param_name, param_type, value)
                )
                param_index += 1
            else:
                converted_sql += sql[i]
            i += 1
        
        return converted_sql, bq_params
    
    def _infer_bq_type(self, value: Any) -> str:
        """Infer BigQuery type from Python value."""
        if value is None:
            return "STRING"  # Default to STRING for NULL
        elif isinstance(value, bool):
            return "BOOL"
        elif isinstance(value, int):
            return "INT64"
        elif isinstance(value, float):
            return "FLOAT64"
        elif isinstance(value, bytes):
            return "BYTES"
        else:
            # Default to STRING (handles str, date, datetime via conversion)
            return "STRING"
    
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AdapterResult:
        """
        Execute SQL query on BigQuery.
        
        Supports:
        - Parameterized queries with ? placeholders
        - Standard SQL (default) or Legacy SQL
        - Cost estimation via dry_run
        - Query result caching
        """
        if not self._connected or not self._client:
            raise QueryError(
                "Not connected to BigQuery",
                engine=self.ENGINE
            )
        
        self._update_last_used()
        start_time = time.perf_counter()
        
        # Convert placeholders
        bq_sql, bq_params = self.convert_placeholders(sql, params)
        
        try:
            # Build job config
            job_config = bigquery.QueryJobConfig(
                use_legacy_sql=self.use_legacy_sql,
                labels=self.labels,
                dry_run=self.dry_run,
            )
            
            # Add parameters if any
            if bq_params:
                job_config.query_parameters = bq_params
            
            # Cost control
            if self.maximum_bytes_billed:
                job_config.maximum_bytes_billed = self.maximum_bytes_billed
            
            # Execute query
            query_job = self._client.query(
                bq_sql,
                job_config=job_config,
                timeout=self.timeout
            )
            
            # If dry run, return estimation
            if self.dry_run:
                return AdapterResult(
                    rows=[],
                    columns=[],
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    engine=self.ENGINE,
                    sql=bq_sql,
                    metadata={
                        "dry_run": True,
                        "total_bytes_processed": query_job.total_bytes_processed,
                        "estimated_cost_usd": self._estimate_cost(query_job.total_bytes_processed)
                    }
                )
            
            # Wait for results
            result = query_job.result(timeout=self.timeout)
            
            # Convert to list of dicts
            rows = [dict(row) for row in result]
            
            # Get column info
            columns = []
            column_types = {}
            if result.schema:
                for field in result.schema:
                    columns.append(field.name)
                    column_types[field.name] = field.field_type
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Build metadata
            metadata = {
                "project": self.project,
                "location": self.location,
                "job_id": query_job.job_id,
                "total_bytes_processed": query_job.total_bytes_processed,
                "total_bytes_billed": query_job.total_bytes_billed,
                "cache_hit": query_job.cache_hit,
                "slot_millis": query_job.slot_millis,
            }
            
            # Add cost estimate
            if query_job.total_bytes_billed:
                metadata["estimated_cost_usd"] = self._estimate_cost(
                    query_job.total_bytes_billed
                )
            
            return AdapterResult(
                rows=rows,
                columns=columns,
                column_types=column_types,
                execution_time_ms=execution_time,
                engine=self.ENGINE,
                sql=bq_sql,
                metadata=metadata
            )
            
        except GoogleAPIError as e:
            raise QueryError(
                f"BigQuery query failed: {e.message if hasattr(e, 'message') else str(e)}",
                engine=self.ENGINE,
                original_error=e
            )
        except Exception as e:
            raise QueryError(
                f"BigQuery query failed: {e}",
                engine=self.ENGINE,
                original_error=e
            )
    
    def _estimate_cost(self, bytes_processed: int) -> float:
        """
        Estimate query cost in USD.
        
        BigQuery on-demand pricing: $5 per TB (as of 2024)
        First 1 TB/month is free, but we estimate full cost.
        """
        if not bytes_processed:
            return 0.0
        
        tb = bytes_processed / (1024 ** 4)
        return round(tb * 5.0, 6)
    
    def health_check(self) -> bool:
        """Check BigQuery connection health."""
        if not self._connected or not self._client:
            return False
        
        try:
            # Simple query to verify connectivity
            query = "SELECT 1 as health"
            job = self._client.query(query)
            list(job.result())
            return True
        except Exception:
            return False
    
    def get_datasets(self) -> List[str]:
        """List datasets in the project."""
        if not self._client:
            raise QueryError("Not connected", engine=self.ENGINE)
        
        datasets = list(self._client.list_datasets())
        return [ds.dataset_id for ds in datasets]
    
    def get_tables(self, dataset: Optional[str] = None) -> List[str]:
        """List tables in a dataset."""
        if not self._client:
            raise QueryError("Not connected", engine=self.ENGINE)
        
        ds = dataset or self.dataset
        if not ds:
            raise QueryError("No dataset specified", engine=self.ENGINE)
        
        tables = list(self._client.list_tables(ds))
        return [t.table_id for t in tables]
    
    def get_table_schema(self, table: str, dataset: Optional[str] = None) -> List[Dict]:
        """Get schema for a table."""
        if not self._client:
            raise QueryError("Not connected", engine=self.ENGINE)
        
        ds = dataset or self.dataset
        table_ref = f"{self.project}.{ds}.{table}"
        
        tbl = self._client.get_table(table_ref)
        
        return [
            {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "description": field.description
            }
            for field in tbl.schema
        ]
    
    def estimate_query_cost(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Estimate query cost without running it.
        
        Returns:
            Dict with bytes_processed, estimated_cost_usd, etc.
        """
        # Temporarily enable dry run
        original_dry_run = self.dry_run
        self.dry_run = True
        
        try:
            result = self.execute(sql, params)
            return result.metadata
        finally:
            self.dry_run = original_dry_run

