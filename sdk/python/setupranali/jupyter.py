"""
SetuPranali Jupyter Widget

Interactive widget for exploring datasets in Jupyter notebooks.
"""

from typing import Optional, List, Callable
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets

from .client import SetuPranali
from .models import Dataset, QueryResult


class DatasetExplorer:
    """
    Interactive dataset explorer for Jupyter notebooks.
    
    Example:
        from setupranali.jupyter import DatasetExplorer
        
        explorer = DatasetExplorer(
            url="http://localhost:8080",
            api_key="your-api-key"
        )
        explorer.show()
    """
    
    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: str = None,
        client: SetuPranali = None
    ):
        """
        Initialize the dataset explorer.
        
        Args:
            url: SetuPranali server URL
            api_key: API key for authentication
            client: Existing SetuPranali client (optional)
        """
        self.client = client or SetuPranali(url=url, api_key=api_key)
        self._datasets: List[Dataset] = []
        self._current_dataset: Optional[Dataset] = None
        self._result: Optional[QueryResult] = None
        
        # Widgets
        self._dataset_dropdown = None
        self._dimensions_select = None
        self._metrics_select = None
        self._limit_input = None
        self._query_button = None
        self._output = None
        self._container = None
    
    def _create_widgets(self):
        """Create the widget UI."""
        # Dataset dropdown
        self._dataset_dropdown = widgets.Dropdown(
            options=[],
            description='Dataset:',
            layout=widgets.Layout(width='300px')
        )
        self._dataset_dropdown.observe(self._on_dataset_change, names='value')
        
        # Dimensions multi-select
        self._dimensions_select = widgets.SelectMultiple(
            options=[],
            description='Dimensions:',
            layout=widgets.Layout(width='300px', height='120px')
        )
        
        # Metrics multi-select
        self._metrics_select = widgets.SelectMultiple(
            options=[],
            description='Metrics:',
            layout=widgets.Layout(width='300px', height='120px')
        )
        
        # Limit input
        self._limit_input = widgets.IntText(
            value=100,
            description='Limit:',
            layout=widgets.Layout(width='150px')
        )
        
        # Query button
        self._query_button = widgets.Button(
            description='Run Query',
            button_style='primary',
            icon='play'
        )
        self._query_button.on_click(self._on_query_click)
        
        # Export button
        self._export_button = widgets.Button(
            description='Export to DataFrame',
            button_style='info',
            icon='table'
        )
        self._export_button.on_click(self._on_export_click)
        
        # Output area
        self._output = widgets.Output()
        
        # Layout
        controls = widgets.VBox([
            widgets.HTML('<h3>🔍 SetuPranali Dataset Explorer</h3>'),
            self._dataset_dropdown,
            widgets.HBox([
                self._dimensions_select,
                self._metrics_select
            ]),
            widgets.HBox([
                self._limit_input,
                self._query_button,
                self._export_button
            ]),
        ])
        
        self._container = widgets.VBox([
            controls,
            self._output
        ])
    
    def _load_datasets(self):
        """Load available datasets."""
        try:
            self._datasets = self.client.datasets()
            options = [(f"{d.name} ({d.id})", d.id) for d in self._datasets]
            self._dataset_dropdown.options = options
            if options:
                self._dataset_dropdown.value = options[0][1]
        except Exception as e:
            with self._output:
                print(f"Error loading datasets: {e}")
    
    def _on_dataset_change(self, change):
        """Handle dataset selection change."""
        if change['new']:
            try:
                self._current_dataset = self.client.dataset(change['new'])
                
                # Update dimensions
                dim_options = [
                    (f"{d.label or d.name} ({d.type})", d.name)
                    for d in self._current_dataset.dimensions
                ]
                self._dimensions_select.options = dim_options
                
                # Update metrics
                metric_options = [
                    (f"{m.label or m.name}", m.name)
                    for m in self._current_dataset.metrics
                ]
                self._metrics_select.options = metric_options
                
            except Exception as e:
                with self._output:
                    print(f"Error loading dataset: {e}")
    
    def _on_query_click(self, button):
        """Handle query button click."""
        with self._output:
            clear_output()
            
            if not self._current_dataset:
                print("Please select a dataset")
                return
            
            dimensions = list(self._dimensions_select.value)
            metrics = list(self._metrics_select.value)
            
            if not dimensions and not metrics:
                print("Please select at least one dimension or metric")
                return
            
            print(f"Querying {self._current_dataset.name}...")
            
            try:
                self._result = self.client.query(
                    dataset=self._current_dataset.id,
                    dimensions=dimensions,
                    metrics=metrics,
                    limit=self._limit_input.value
                )
                
                print(f"✅ Returned {self._result.row_count} rows")
                print(f"⏱️ Execution time: {self._result.execution_time_ms}ms")
                print(f"💾 Cached: {self._result.cached}")
                print()
                
                # Display as table
                try:
                    df = self._result.to_dataframe()
                    display(df)
                except ImportError:
                    # Fallback if pandas not available
                    for row in self._result.data[:10]:
                        print(row)
                    if self._result.row_count > 10:
                        print(f"... and {self._result.row_count - 10} more rows")
                        
            except Exception as e:
                print(f"❌ Query failed: {e}")
    
    def _on_export_click(self, button):
        """Handle export button click."""
        with self._output:
            if not self._result:
                print("Run a query first")
                return
            
            try:
                df = self._result.to_dataframe()
                # Store in IPython namespace
                from IPython import get_ipython
                ipython = get_ipython()
                if ipython:
                    ipython.user_ns['df'] = df
                    print("✅ DataFrame exported to variable 'df'")
            except ImportError:
                print("pandas is required for DataFrame export")
            except Exception as e:
                print(f"Export failed: {e}")
    
    def show(self):
        """Display the widget."""
        self._create_widgets()
        self._load_datasets()
        display(self._container)
    
    def query(
        self,
        dataset: str,
        dimensions: List[str] = None,
        metrics: List[str] = None,
        **kwargs
    ) -> QueryResult:
        """
        Run a query and return results.
        
        Convenience method for programmatic access.
        """
        return self.client.query(
            dataset=dataset,
            dimensions=dimensions,
            metrics=metrics,
            **kwargs
        )


class QuickQuery:
    """
    Quick query widget for one-off queries.
    
    Example:
        from setupranali.jupyter import QuickQuery
        
        qq = QuickQuery("http://localhost:8080", "your-api-key")
        df = qq.run("orders", dimensions=["city"], metrics=["revenue"])
    """
    
    def __init__(self, url: str, api_key: str = None):
        self.client = SetuPranali(url=url, api_key=api_key)
    
    def run(
        self,
        dataset: str,
        dimensions: List[str] = None,
        metrics: List[str] = None,
        filters: List[dict] = None,
        limit: int = 1000
    ):
        """
        Run a query and return a DataFrame.
        
        Args:
            dataset: Dataset ID
            dimensions: List of dimension names
            metrics: List of metric names
            filters: List of filter conditions
            limit: Maximum rows
            
        Returns:
            pandas DataFrame
        """
        result = self.client.query(
            dataset=dataset,
            dimensions=dimensions,
            metrics=metrics,
            filters=filters,
            limit=limit
        )
        return result.to_dataframe()
    
    def sql(self, query: str, dataset: str):
        """
        Run a raw SQL query.
        
        Note: RLS is automatically applied.
        """
        import requests
        
        response = requests.post(
            f"{self.client.url}/v1/sql",
            headers={"X-API-Key": self.client.api_key},
            json={"sql": query, "dataset": dataset}
        )
        response.raise_for_status()
        
        data = response.json()
        
        try:
            import pandas as pd
            return pd.DataFrame(data["data"])
        except ImportError:
            return data


def explore(url: str = "http://localhost:8080", api_key: str = None):
    """
    Quick function to start the dataset explorer.
    
    Example:
        from setupranali.jupyter import explore
        explore("http://localhost:8080", "your-api-key")
    """
    explorer = DatasetExplorer(url=url, api_key=api_key)
    explorer.show()
    return explorer

