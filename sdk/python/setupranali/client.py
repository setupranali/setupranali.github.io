"""
SetuPranali SDK Client

Synchronous and asynchronous clients for the SetuPranali API.
"""

from typing import List, Dict, Any, Optional, Union
import json

from .models import Dataset, QueryResult, HealthStatus
from .exceptions import (
    SetuPranaliError,
    AuthenticationError,
    DatasetNotFoundError,
    QueryError,
    ValidationError,
    RateLimitError,
    ConnectionError,
    TimeoutError
)


class SetuPranali:
    """
    Synchronous client for SetuPranali API.
    
    Example:
        client = SetuPranali(
            url="http://localhost:8080",
            api_key="your-api-key"
        )
        
        # List datasets
        for dataset in client.datasets():
            print(dataset.name)
        
        # Query data
        result = client.query(
            dataset="orders",
            dimensions=["city"],
            metrics=["total_revenue"]
        )
        
        # Get as DataFrame
        df = result.to_dataframe()
    """
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: str = None,
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """
        Initialize the SetuPranali client.
        
        Args:
            url: Base URL of the SetuPranali server
            api_key: API key for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._session = None
    
    def _get_session(self):
        """Get or create requests session."""
        if self._session is None:
            try:
                import requests
            except ImportError:
                raise ImportError(
                    "requests is required for the sync client. "
                    "Install it with: pip install requests"
                )
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
            if self.api_key:
                self._session.headers["X-API-Key"] = self.api_key
        return self._session
    
    def _request(
        self,
        method: str,
        path: str,
        data: dict = None,
        params: dict = None
    ) -> dict:
        """Make an HTTP request."""
        import requests as req_lib
        
        session = self._get_session()
        url = f"{self.url}{path}"
        
        try:
            if method.upper() == "GET":
                response = session.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
            elif method.upper() == "POST":
                response = session.post(
                    url,
                    json=data,
                    params=params,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return self._handle_response(response)
            
        except req_lib.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {url}: {e}")
        except req_lib.exceptions.Timeout as e:
            raise TimeoutError(f"Request timed out after {self.timeout}s: {e}")
        except req_lib.exceptions.RequestException as e:
            raise SetuPranaliError(f"Request failed: {e}")
    
    def _handle_response(self, response) -> dict:
        """Handle HTTP response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()
        
        # Try to parse error details
        try:
            error_data = response.json()
            message = error_data.get("detail", str(error_data))
        except Exception:
            message = response.text or f"HTTP {response.status_code}"
        
        if response.status_code == 401:
            raise AuthenticationError(message, status_code=401)
        elif response.status_code == 403:
            raise AuthenticationError(message, status_code=403)
        elif response.status_code == 404:
            raise DatasetNotFoundError(message, status_code=404)
        elif response.status_code == 400:
            raise ValidationError(message, status_code=400)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message, 
                retry_after=int(retry_after) if retry_after else None
            )
        else:
            raise SetuPranaliError(message, status_code=response.status_code)
    
    # =========================================================================
    # API Methods
    # =========================================================================
    
    def health(self) -> HealthStatus:
        """
        Check server health.
        
        Returns:
            HealthStatus object with server status
        """
        data = self._request("GET", "/v1/health")
        return HealthStatus.from_dict(data)
    
    def datasets(self) -> List[Dataset]:
        """
        List all available datasets.
        
        Returns:
            List of Dataset objects
        """
        data = self._request("GET", "/v1/datasets")
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Dataset.from_dict(d) for d in items]
    
    def dataset(self, dataset_id: str) -> Dataset:
        """
        Get a specific dataset by ID.
        
        Args:
            dataset_id: The dataset identifier
            
        Returns:
            Dataset object with full details
        """
        data = self._request("GET", f"/v1/datasets/{dataset_id}")
        return Dataset.from_dict(data)
    
    def query(
        self,
        dataset: str,
        dimensions: List[str] = None,
        metrics: List[str] = None,
        filters: List[Dict[str, Any]] = None,
        order_by: List[Dict[str, str]] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> QueryResult:
        """
        Execute a semantic query.
        
        Args:
            dataset: Dataset ID to query
            dimensions: List of dimension names to group by
            metrics: List of metric names to aggregate
            filters: List of filter conditions
                     e.g. [{"field": "city", "operator": "eq", "value": "Mumbai"}]
            order_by: List of sort orders
                      e.g. [{"field": "revenue", "direction": "desc"}]
            limit: Maximum rows to return (default 1000)
            offset: Number of rows to skip
            
        Returns:
            QueryResult object with data and metadata
            
        Example:
            result = client.query(
                dataset="orders",
                dimensions=["city", "product"],
                metrics=["total_revenue", "order_count"],
                filters=[
                    {"field": "order_date", "operator": "gte", "value": "2024-01-01"},
                    {"field": "status", "operator": "eq", "value": "completed"}
                ],
                order_by=[{"field": "total_revenue", "direction": "desc"}],
                limit=100
            )
            
            df = result.to_dataframe()
        """
        payload = {
            "dataset": dataset,
            "dimensions": [{"name": d} for d in (dimensions or [])],
            "metrics": [{"name": m} for m in (metrics or [])],
            "limit": limit,
            "offset": offset
        }
        
        if filters:
            payload["filters"] = filters
        
        if order_by:
            payload["orderBy"] = order_by
        
        data = self._request("POST", "/v1/query", data=payload)
        return QueryResult.from_dict(data)
    
    def query_graphql(self, query: str, variables: dict = None) -> dict:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            GraphQL response data
            
        Example:
            result = client.query_graphql('''
                query {
                    datasets {
                        id
                        name
                    }
                }
            ''')
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        data = self._request("POST", "/v1/graphql", data=payload)
        
        if "errors" in data:
            raise QueryError(
                str(data["errors"]),
                details={"errors": data["errors"]}
            )
        
        return data.get("data", data)
    
    def close(self):
        """Close the client session."""
        if self._session:
            self._session.close()
            self._session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SetuPranaliAsync:
    """
    Asynchronous client for SetuPranali API.
    
    Example:
        async with SetuPranaliAsync(url="http://localhost:8080", api_key="key") as client:
            datasets = await client.datasets()
            result = await client.query(dataset="orders", metrics=["revenue"])
    """
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: str = None,
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """
        Initialize the async SetuPranali client.
        
        Args:
            url: Base URL of the SetuPranali server
            api_key: API key for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client = None
    
    async def _get_client(self):
        """Get or create httpx client."""
        if self._client is None:
            try:
                import httpx
            except ImportError:
                raise ImportError(
                    "httpx is required for the async client. "
                    "Install it with: pip install httpx"
                )
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
        return self._client
    
    async def _request(
        self,
        method: str,
        path: str,
        data: dict = None,
        params: dict = None
    ) -> dict:
        """Make an async HTTP request."""
        import httpx
        
        client = await self._get_client()
        url = f"{self.url}{path}"
        
        try:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, json=data, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return self._handle_response(response)
            
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {url}: {e}")
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out after {self.timeout}s: {e}")
        except httpx.HTTPError as e:
            raise SetuPranaliError(f"Request failed: {e}")
    
    def _handle_response(self, response) -> dict:
        """Handle HTTP response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()
        
        try:
            error_data = response.json()
            message = error_data.get("detail", str(error_data))
        except Exception:
            message = response.text or f"HTTP {response.status_code}"
        
        if response.status_code == 401:
            raise AuthenticationError(message, status_code=401)
        elif response.status_code == 403:
            raise AuthenticationError(message, status_code=403)
        elif response.status_code == 404:
            raise DatasetNotFoundError(message, status_code=404)
        elif response.status_code == 400:
            raise ValidationError(message, status_code=400)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message,
                retry_after=int(retry_after) if retry_after else None
            )
        else:
            raise SetuPranaliError(message, status_code=response.status_code)
    
    # =========================================================================
    # Async API Methods
    # =========================================================================
    
    async def health(self) -> HealthStatus:
        """Check server health."""
        data = await self._request("GET", "/v1/health")
        return HealthStatus.from_dict(data)
    
    async def datasets(self) -> List[Dataset]:
        """List all available datasets."""
        data = await self._request("GET", "/v1/datasets")
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Dataset.from_dict(d) for d in items]
    
    async def dataset(self, dataset_id: str) -> Dataset:
        """Get a specific dataset by ID."""
        data = await self._request("GET", f"/v1/datasets/{dataset_id}")
        return Dataset.from_dict(data)
    
    async def query(
        self,
        dataset: str,
        dimensions: List[str] = None,
        metrics: List[str] = None,
        filters: List[Dict[str, Any]] = None,
        order_by: List[Dict[str, str]] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> QueryResult:
        """Execute a semantic query."""
        payload = {
            "dataset": dataset,
            "dimensions": [{"name": d} for d in (dimensions or [])],
            "metrics": [{"name": m} for m in (metrics or [])],
            "limit": limit,
            "offset": offset
        }
        
        if filters:
            payload["filters"] = filters
        
        if order_by:
            payload["orderBy"] = order_by
        
        data = await self._request("POST", "/v1/query", data=payload)
        return QueryResult.from_dict(data)
    
    async def query_graphql(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        data = await self._request("POST", "/v1/graphql", data=payload)
        
        if "errors" in data:
            raise QueryError(
                str(data["errors"]),
                details={"errors": data["errors"]}
            )
        
        return data.get("data", data)
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

