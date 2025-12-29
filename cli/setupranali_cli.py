#!/usr/bin/env python3
"""
SetuPranali CLI - Command-line interface for managing SetuPranali

Usage:
    setupranali --help
    setupranali sources list
    setupranali datasets list
    setupranali query orders --dimensions city --metrics revenue
    setupranali health

Install:
    pip install -e .  # From repo root
    # or
    pip install setupranali[cli]
"""

import os
import sys
import json
import time
from typing import Optional, List
from datetime import datetime

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# =============================================================================
# CONFIGURATION
# =============================================================================

console = Console()

DEFAULT_URL = os.environ.get("SETUPRANALI_URL", "http://localhost:8080")
DEFAULT_API_KEY = os.environ.get("SETUPRANALI_API_KEY", "")

CONFIG_FILE = os.path.expanduser("~/.setupranali/config.json")


def load_config() -> dict:
    """Load CLI configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """Save CLI configuration to file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_client(url: str = None, api_key: str = None) -> httpx.Client:
    """Get configured HTTP client."""
    config = load_config()
    
    base_url = url or config.get("url") or DEFAULT_URL
    key = api_key or config.get("api_key") or DEFAULT_API_KEY
    
    headers = {}
    if key:
        headers["X-API-Key"] = key
    
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)


def handle_error(response: httpx.Response):
    """Handle API error responses with rich formatting."""
    try:
        data = response.json()
        if "error" in data:
            err = data["error"]
            console.print(f"\n[bold red]Error {err.get('code', 'UNKNOWN')}[/bold red]")
            console.print(f"[red]{err.get('message', 'Unknown error')}[/red]")
            
            if err.get("suggestion"):
                console.print(f"\n[yellow]💡 Suggestion:[/yellow] {err['suggestion']}")
            
            if err.get("docs"):
                console.print(f"[dim]📚 Docs: {err['docs']}[/dim]")
            
            if err.get("details"):
                console.print("\n[dim]Details:[/dim]")
                console.print(Syntax(json.dumps(err["details"], indent=2), "json"))
        else:
            console.print(f"[red]Error: {data}[/red]")
    except json.JSONDecodeError:
        console.print(f"[red]Error {response.status_code}: {response.text}[/red]")
    
    sys.exit(1)


# =============================================================================
# MAIN CLI GROUP
# =============================================================================

@click.group()
@click.option("--url", envvar="SETUPRANALI_URL", help="SetuPranali server URL")
@click.option("--api-key", envvar="SETUPRANALI_API_KEY", help="API key for authentication")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.version_option(version="1.1.0", prog_name="setupranali")
@click.pass_context
def cli(ctx, url, api_key, output_json):
    """
    SetuPranali CLI - Manage your semantic BI layer from the command line.
    
    \b
    Quick Start:
        setupranali config set url http://localhost:8080
        setupranali config set api_key your-api-key
        setupranali health
        setupranali datasets list
    
    \b
    Environment Variables:
        SETUPRANALI_URL     - Server URL (default: http://localhost:8080)
        SETUPRANALI_API_KEY - API key for authentication
    """
    ctx.ensure_object(dict)
    ctx.obj["url"] = url
    ctx.obj["api_key"] = api_key
    ctx.obj["output_json"] = output_json


# =============================================================================
# CONFIG COMMANDS
# =============================================================================

@cli.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = load_config()
    
    table = Table(title="Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")
    
    # URL
    url = cfg.get("url") or DEFAULT_URL
    source = "config" if cfg.get("url") else ("env" if os.environ.get("SETUPRANALI_URL") else "default")
    table.add_row("URL", url, source)
    
    # API Key
    api_key = cfg.get("api_key") or DEFAULT_API_KEY
    masked = api_key[:8] + "..." if len(api_key) > 8 else api_key or "(not set)"
    source = "config" if cfg.get("api_key") else ("env" if os.environ.get("SETUPRANALI_API_KEY") else "default")
    table.add_row("API Key", masked, source)
    
    # Config file location
    table.add_row("Config File", CONFIG_FILE, "")
    
    console.print(table)


@config.command("set")
@click.argument("key", type=click.Choice(["url", "api_key"]))
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    console.print(f"[green]✓[/green] Set {key} = {value[:20]}..." if len(value) > 20 else f"[green]✓[/green] Set {key} = {value}")


@config.command("clear")
def config_clear():
    """Clear all configuration."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        console.print("[green]✓[/green] Configuration cleared")
    else:
        console.print("[yellow]No configuration file found[/yellow]")


# =============================================================================
# HEALTH COMMAND
# =============================================================================

@cli.command()
@click.pass_context
def health(ctx):
    """Check server health and status."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("Checking health...", total=None)
            
            try:
                response = client.get("/v1/health")
            except httpx.ConnectError:
                console.print("[red]✗ Cannot connect to server[/red]")
                console.print(f"[dim]URL: {client.base_url}[/dim]")
                sys.exit(1)
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(data, indent=2), "json"))
            return
        
        # Status panel
        status = data.get("status", "unknown")
        status_color = "green" if status == "healthy" else "red"
        console.print(Panel(
            f"[{status_color} bold]{status.upper()}[/{status_color} bold]",
            title="Server Status",
            expand=False
        ))
        
        # Services table
        table = Table(title="Services", show_header=True)
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        
        services = data.get("services", {})
        for service, status in services.items():
            status_icon = "✓" if status else "✗"
            status_style = "green" if status else "red"
            table.add_row(service, f"[{status_style}]{status_icon}[/{status_style}]")
        
        console.print(table)
        
        # Cache stats if available
        cache = data.get("cache", {})
        if cache:
            console.print(f"\n[dim]Cache: {cache.get('hits', 0)} hits, {cache.get('misses', 0)} misses[/dim]")


# =============================================================================
# SOURCES COMMANDS
# =============================================================================

@cli.group()
def sources():
    """Manage data sources."""
    pass


@sources.command("list")
@click.pass_context
def sources_list(ctx):
    """List all registered data sources."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        response = client.get("/v1/sources")
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        items = data.get("items", [])
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(items, indent=2), "json"))
            return
        
        if not items:
            console.print("[yellow]No sources registered[/yellow]")
            console.print("[dim]Add one with: setupranali sources add --help[/dim]")
            return
        
        table = Table(title="Data Sources", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Created", style="dim")
        
        for source in items:
            table.add_row(
                source.get("id", ""),
                source.get("name", ""),
                source.get("type", ""),
                source.get("createdAt", "")[:10] if source.get("createdAt") else ""
            )
        
        console.print(table)


@sources.command("add")
@click.option("--name", required=True, help="Source name")
@click.option("--type", "source_type", required=True, 
              type=click.Choice(["postgres", "mysql", "snowflake", "bigquery", "databricks", "redshift", "clickhouse", "duckdb"]),
              help="Database type")
@click.option("--config", "config_json", required=True, help="Connection config as JSON string")
@click.pass_context
def sources_add(ctx, name, source_type, config_json):
    """Add a new data source."""
    try:
        config_data = json.loads(config_json)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        sys.exit(1)
    
    payload = {
        "name": name,
        "type": source_type,
        "connection": config_data
    }
    
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task(f"Adding source '{name}'...", total=None)
            response = client.post("/v1/sources", json=payload)
        
        if response.status_code not in (200, 201):
            handle_error(response)
        
        data = response.json()
        console.print(f"[green]✓[/green] Source '{name}' added successfully")
        console.print(f"[dim]ID: {data.get('id', 'unknown')}[/dim]")


@sources.command("test")
@click.argument("source_id")
@click.pass_context
def sources_test(ctx, source_id):
    """Test connection to a data source."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task(f"Testing connection to '{source_id}'...", total=None)
            response = client.post(f"/v1/sources/{source_id}/test")
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        
        if data.get("success"):
            console.print(f"[green]✓[/green] {data.get('message', 'Connection successful')}")
            if data.get("latencyMs"):
                console.print(f"[dim]Latency: {data['latencyMs']}ms[/dim]")
        else:
            console.print(f"[red]✗[/red] {data.get('message', 'Connection failed')}")


# =============================================================================
# DATASETS COMMANDS
# =============================================================================

@cli.group()
def datasets():
    """Manage datasets."""
    pass


@datasets.command("list")
@click.pass_context
def datasets_list(ctx):
    """List all available datasets."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        response = client.get("/v1/datasets")
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        items = data.get("items", [])
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(items, indent=2), "json"))
            return
        
        if not items:
            console.print("[yellow]No datasets found[/yellow]")
            console.print("[dim]Define datasets in catalog.yaml[/dim]")
            return
        
        table = Table(title="Datasets", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="dim", max_width=40)
        table.add_column("Tags", style="yellow")
        
        for ds in items:
            tags = ", ".join(ds.get("tags", []))
            table.add_row(
                ds.get("id", ""),
                ds.get("name", ""),
                ds.get("description", "")[:40] + "..." if len(ds.get("description", "")) > 40 else ds.get("description", ""),
                tags
            )
        
        console.print(table)


@datasets.command("show")
@click.argument("dataset_id")
@click.pass_context
def datasets_show(ctx, dataset_id):
    """Show details for a specific dataset."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        response = client.get(f"/v1/datasets/{dataset_id}")
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(data, indent=2), "json"))
            return
        
        # Dataset info panel
        console.print(Panel(
            f"[bold]{data.get('name', dataset_id)}[/bold]\n"
            f"[dim]{data.get('description', 'No description')}[/dim]",
            title=f"Dataset: {dataset_id}",
            expand=False
        ))
        
        # Dimensions table
        dims = data.get("dimensions", [])
        if dims:
            table = Table(title="Dimensions", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Description", style="dim")
            
            for dim in dims:
                table.add_row(
                    dim.get("name", ""),
                    dim.get("type", "string"),
                    dim.get("description", "")
                )
            
            console.print(table)
        
        # Metrics table
        metrics = data.get("metrics", [])
        if metrics:
            table = Table(title="Metrics", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Expression", style="dim")
            
            for metric in metrics:
                table.add_row(
                    metric.get("name", ""),
                    metric.get("type", "number"),
                    metric.get("expr", "")[:30] + "..." if len(metric.get("expr", "")) > 30 else metric.get("expr", "")
                )
            
            console.print(table)


@datasets.command("validate")
@click.option("--catalog", type=click.Path(exists=True), help="Path to catalog.yaml")
@click.pass_context
def datasets_validate(ctx, catalog):
    """Validate catalog configuration."""
    import yaml
    
    catalog_path = catalog or "catalog.yaml"
    
    if not os.path.exists(catalog_path):
        console.print(f"[red]Catalog file not found: {catalog_path}[/red]")
        sys.exit(1)
    
    try:
        with open(catalog_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        console.print(f"[red]YAML parse error: {e}[/red]")
        sys.exit(1)
    
    errors = []
    warnings = []
    
    datasets = data.get("datasets", [])
    if not datasets:
        errors.append("No datasets defined")
    
    for ds in datasets:
        ds_id = ds.get("id", "unknown")
        
        # Required fields
        if not ds.get("id"):
            errors.append(f"Dataset missing 'id'")
        if not ds.get("source"):
            errors.append(f"Dataset '{ds_id}' missing 'source'")
        
        # Dimensions
        dims = ds.get("dimensions", [])
        if not dims:
            warnings.append(f"Dataset '{ds_id}' has no dimensions")
        for dim in dims:
            if not dim.get("name"):
                errors.append(f"Dataset '{ds_id}' has dimension without 'name'")
        
        # Metrics
        metrics = ds.get("metrics", [])
        if not metrics:
            warnings.append(f"Dataset '{ds_id}' has no metrics")
        for metric in metrics:
            if not metric.get("name"):
                errors.append(f"Dataset '{ds_id}' has metric without 'name'")
            if not metric.get("expr"):
                warnings.append(f"Dataset '{ds_id}' metric '{metric.get('name', '?')}' has no expression")
    
    # Report
    console.print(f"\n[bold]Catalog Validation: {catalog_path}[/bold]\n")
    
    if errors:
        console.print("[red bold]Errors:[/red bold]")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
    
    if warnings:
        console.print("\n[yellow bold]Warnings:[/yellow bold]")
        for warn in warnings:
            console.print(f"  [yellow]![/yellow] {warn}")
    
    if not errors and not warnings:
        console.print(f"[green]✓[/green] Catalog is valid ({len(datasets)} datasets)")
    elif not errors:
        console.print(f"\n[green]✓[/green] Catalog is valid with warnings ({len(datasets)} datasets)")
    else:
        console.print(f"\n[red]✗[/red] Catalog has errors")
        sys.exit(1)


# =============================================================================
# QUERY COMMAND
# =============================================================================

@cli.command()
@click.argument("dataset")
@click.option("--dimensions", "-d", multiple=True, help="Dimensions to include")
@click.option("--metrics", "-m", multiple=True, help="Metrics to include")
@click.option("--limit", "-l", default=10, help="Maximum rows to return")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.pass_context
def query(ctx, dataset, dimensions, metrics, limit, output_format):
    """
    Execute a semantic query.
    
    \b
    Examples:
        setupranali query orders -d city -d region -m revenue -m orders
        setupranali query sales --dimensions product --metrics total --limit 20
        setupranali query orders -d city -m revenue --format csv
    """
    if not dimensions and not metrics:
        console.print("[red]At least one dimension or metric is required[/red]")
        console.print("[dim]Use -d for dimensions and -m for metrics[/dim]")
        sys.exit(1)
    
    payload = {
        "dataset": dataset,
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "limit": limit
    }
    
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("Executing query...", total=None)
            start_time = time.time()
            response = client.post("/v1/query", json=payload)
            elapsed = time.time() - start_time
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        rows = data.get("rows", [])
        columns = data.get("columns", [])
        stats = data.get("stats", {})
        
        if output_format == "json":
            console.print(Syntax(json.dumps(data, indent=2), "json"))
            return
        
        if output_format == "csv":
            # CSV output
            col_names = [c.get("name", f"col{i}") for i, c in enumerate(columns)]
            print(",".join(col_names))
            for row in rows:
                values = [str(row.get(c, "")) for c in col_names]
                print(",".join(values))
            return
        
        # Table output
        if not rows:
            console.print("[yellow]No results[/yellow]")
            return
        
        table = Table(title=f"Query Results: {dataset}", show_header=True)
        
        for col in columns:
            table.add_column(col.get("name", ""), style="cyan" if col.get("type") == "string" else "green")
        
        for row in rows:
            values = [str(row.get(col.get("name", ""), "")) for col in columns]
            table.add_row(*values)
        
        console.print(table)
        console.print(f"\n[dim]{len(rows)} rows in {elapsed:.2f}s (cached: {stats.get('cached', False)})[/dim]")


# =============================================================================
# SQL COMMAND
# =============================================================================

@cli.command()
@click.argument("sql")
@click.option("--dataset", "-D", required=True, help="Dataset for RLS context")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.pass_context
def sql(ctx, sql, dataset, output_format):
    """
    Execute a SQL query with automatic RLS.
    
    \b
    Example:
        setupranali sql "SELECT city, SUM(revenue) FROM orders GROUP BY city" -D orders
    """
    payload = {
        "sql": sql,
        "dataset": dataset
    }
    
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("Executing SQL...", total=None)
            response = client.post("/v1/sql", json=payload)
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        rows = data.get("data", [])
        columns = data.get("columns", [])
        
        if output_format == "json":
            console.print(Syntax(json.dumps(data, indent=2), "json"))
            return
        
        if output_format == "csv":
            col_names = [c.get("name", f"col{i}") for i, c in enumerate(columns)]
            print(",".join(col_names))
            for row in rows:
                values = [str(row.get(c, "")) for c in col_names]
                print(",".join(values))
            return
        
        # Table output
        if not rows:
            console.print("[yellow]No results[/yellow]")
            return
        
        table = Table(title="SQL Results", show_header=True)
        
        for col in columns:
            table.add_column(col.get("name", ""))
        
        for row in rows:
            values = [str(row.get(col.get("name", ""), "")) for col in columns]
            table.add_row(*values)
        
        console.print(table)
        console.print(f"\n[dim]{data.get('rowCount', len(rows))} rows, RLS applied: {data.get('rlsApplied', False)}[/dim]")


# =============================================================================
# NLQ COMMAND
# =============================================================================

@cli.command()
@click.argument("question")
@click.option("--dataset", "-D", required=True, help="Dataset to query")
@click.option("--provider", "-p", default="simple", type=click.Choice(["simple", "openai", "anthropic"]), help="NLQ provider")
@click.option("--execute", "-x", is_flag=True, help="Execute the translated query")
@click.pass_context
def nlq(ctx, question, dataset, provider, execute):
    """
    Ask a question in natural language.
    
    \b
    Examples:
        setupranali nlq "What are the top 10 cities by revenue?" -D orders
        setupranali nlq "Show me monthly sales" -D sales -x
        setupranali nlq "Total orders per region" -D orders -p openai -x
    """
    payload = {
        "question": question,
        "dataset": dataset,
        "provider": provider,
        "execute": execute
    }
    
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("Translating question...", total=None)
            response = client.post("/v1/nlq", json=payload)
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(data, indent=2), "json"))
            return
        
        # Question and translation
        console.print(Panel(
            f"[bold]Question:[/bold] {data.get('question', question)}\n\n"
            f"[bold]Confidence:[/bold] {data.get('confidence', 0):.0%}",
            title="Natural Language Query",
            expand=False
        ))
        
        # Translated query
        query_data = data.get("query", {})
        if query_data:
            console.print("\n[bold]Translated Query:[/bold]")
            console.print(Syntax(json.dumps(query_data, indent=2), "json"))
        
        # Explanation
        if data.get("explanation"):
            console.print(f"\n[dim]💡 {data['explanation']}[/dim]")
        
        # Suggestions
        suggestions = data.get("suggestions", [])
        if suggestions:
            console.print("\n[yellow]Suggestions:[/yellow]")
            for s in suggestions:
                console.print(f"  • {s}")
        
        # Results if executed
        results = data.get("results")
        if results:
            console.print("\n[bold]Results:[/bold]")
            rows = results.get("data", [])
            columns = results.get("columns", [])
            
            if rows:
                table = Table(show_header=True)
                for col in columns:
                    table.add_column(col.get("name", ""))
                
                for row in rows[:10]:  # Limit display
                    values = [str(row.get(col.get("name", ""), "")) for col in columns]
                    table.add_row(*values)
                
                console.print(table)
                
                if len(rows) > 10:
                    console.print(f"[dim]... and {len(rows) - 10} more rows[/dim]")


# =============================================================================
# CACHE COMMANDS
# =============================================================================

@cli.group()
def cache():
    """Manage query cache."""
    pass


@cache.command("stats")
@click.pass_context
def cache_stats(ctx):
    """Show cache statistics."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        response = client.get("/v1/health")
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        cache_data = data.get("cache", {})
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(cache_data, indent=2), "json"))
            return
        
        if not cache_data:
            console.print("[yellow]Cache statistics not available[/yellow]")
            return
        
        table = Table(title="Cache Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Enabled", "✓" if cache_data.get("enabled") else "✗")
        table.add_row("Backend", cache_data.get("backend", "unknown"))
        table.add_row("Hits", str(cache_data.get("hits", 0)))
        table.add_row("Misses", str(cache_data.get("misses", 0)))
        
        hits = cache_data.get("hits", 0)
        misses = cache_data.get("misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        table.add_row("Hit Rate", f"{hit_rate:.1f}%")
        
        console.print(table)


@cache.command("clear")
@click.option("--dataset", "-D", help="Clear cache for specific dataset only")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def cache_clear(ctx, dataset, confirm):
    """Clear the query cache."""
    if not confirm:
        if dataset:
            msg = f"Clear cache for dataset '{dataset}'?"
        else:
            msg = "Clear entire cache?"
        
        if not click.confirm(msg):
            console.print("[dim]Cancelled[/dim]")
            return
    
    # Note: This would require a cache clear endpoint
    console.print("[yellow]Cache clear endpoint not yet implemented[/yellow]")
    console.print("[dim]Restart the server to clear cache, or wait for TTL expiration[/dim]")


# =============================================================================
# INTROSPECTION COMMAND
# =============================================================================

@cli.command()
@click.pass_context
def introspect(ctx):
    """Show full schema introspection for all datasets."""
    with get_client(ctx.obj.get("url"), ctx.obj.get("api_key")) as client:
        response = client.get("/v1/introspection/datasets")
        
        if response.status_code != 200:
            handle_error(response)
        
        data = response.json()
        datasets = data.get("datasets", [])
        
        if ctx.obj.get("output_json"):
            console.print(Syntax(json.dumps(data, indent=2), "json"))
            return
        
        if not datasets:
            console.print("[yellow]No datasets found[/yellow]")
            return
        
        for ds in datasets:
            console.print(Panel(
                f"[bold]{ds.get('name', ds.get('id'))}[/bold]\n"
                f"[dim]{ds.get('description', 'No description')}[/dim]",
                title=f"📊 {ds.get('id')}",
                expand=False
            ))
            
            schema = ds.get("schema", {})
            
            # Dimensions
            dims = schema.get("dimensions", [])
            if dims:
                console.print("  [cyan]Dimensions:[/cyan]")
                for dim in dims:
                    hidden = " [dim](hidden)[/dim]" if dim.get("hidden") else ""
                    console.print(f"    • {dim.get('name')} [{dim.get('type', 'string')}]{hidden}")
            
            # Metrics
            metrics = schema.get("metrics", [])
            if metrics:
                console.print("  [green]Metrics:[/green]")
                for metric in metrics:
                    console.print(f"    • {metric.get('name')} [{metric.get('type', 'number')}]")
            
            console.print()


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()

