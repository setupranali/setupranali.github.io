# SetuPranali Python SDK

Python client for the SetuPranali semantic analytics layer.

## Installation

```bash
pip install setupranali
```

With optional dependencies:

```bash
# For async support
pip install setupranali[async]

# For pandas DataFrames
pip install setupranali[pandas]

# Everything
pip install setupranali[all]
```

## Quick Start

```python
from setupranali import SetuPranali

# Initialize client
client = SetuPranali(
    url="http://localhost:8080",
    api_key="your-api-key"
)

# List datasets
datasets = client.datasets()
for ds in datasets:
    print(f"{ds.id}: {ds.name}")

# Query data
result = client.query(
    dataset="orders",
    dimensions=["city", "product"],
    metrics=["total_revenue", "order_count"],
    filters=[
        {"field": "order_date", "operator": "gte", "value": "2024-01-01"}
    ],
    order_by=[{"field": "total_revenue", "direction": "desc"}],
    limit=100
)

# Access results
print(f"Rows: {result.row_count}")
print(f"Cached: {result.cached}")

# Convert to pandas DataFrame
df = result.to_dataframe()
print(df.head())
```

## Async Usage

```python
import asyncio
from setupranali import SetuPranaliAsync

async def main():
    async with SetuPranaliAsync(
        url="http://localhost:8080",
        api_key="your-api-key"
    ) as client:
        # List datasets
        datasets = await client.datasets()
        
        # Query data
        result = await client.query(
            dataset="orders",
            dimensions=["city"],
            metrics=["total_revenue"]
        )
        
        print(result.to_dataframe())

asyncio.run(main())
```

## GraphQL Queries

```python
from setupranali import SetuPranali

client = SetuPranali(url="http://localhost:8080", api_key="your-key")

result = client.query_graphql('''
    query GetRevenue($input: QueryInput!) {
        query(input: $input) {
            data
            rowCount
            cached
        }
    }
''', variables={
    "input": {
        "dataset": "orders",
        "dimensions": [{"name": "city"}],
        "metrics": [{"name": "total_revenue"}]
    }
})

print(result)
```

## Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `{"field": "city", "operator": "eq", "value": "Mumbai"}` |
| `ne` | Not equal | `{"field": "status", "operator": "ne", "value": "cancelled"}` |
| `gt` | Greater than | `{"field": "amount", "operator": "gt", "value": 100}` |
| `gte` | Greater or equal | `{"field": "date", "operator": "gte", "value": "2024-01-01"}` |
| `lt` | Less than | `{"field": "qty", "operator": "lt", "value": 10}` |
| `lte` | Less or equal | `{"field": "price", "operator": "lte", "value": 500}` |
| `in` | In list | `{"field": "city", "operator": "in", "value": ["Mumbai", "Delhi"]}` |
| `like` | Pattern match | `{"field": "name", "operator": "like", "value": "%Corp%"}` |

## Error Handling

```python
from setupranali import SetuPranali
from setupranali.exceptions import (
    AuthenticationError,
    DatasetNotFoundError,
    QueryError,
    RateLimitError
)

client = SetuPranali(url="http://localhost:8080", api_key="your-key")

try:
    result = client.query(dataset="orders", metrics=["revenue"])
except AuthenticationError:
    print("Invalid API key")
except DatasetNotFoundError:
    print("Dataset doesn't exist")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except QueryError as e:
    print(f"Query failed: {e.message}")
```

## Working with Results

```python
result = client.query(dataset="orders", dimensions=["city"], metrics=["revenue"])

# Iterate over rows
for row in result:
    print(row["city"], row["revenue"])

# Get column names
print(result.column_names())

# Get as list of tuples
tuples = result.to_tuples()

# Get as list of dicts
records = result.to_records()

# Get as pandas DataFrame
df = result.to_dataframe()
```

## Configuration

```python
client = SetuPranali(
    url="https://api.example.com",  # Server URL
    api_key="sk_live_xxx",          # API key
    timeout=60,                      # Request timeout (seconds)
    verify_ssl=True                  # Verify SSL certificates
)
```

## Context Manager

```python
with SetuPranali(url="http://localhost:8080", api_key="key") as client:
    result = client.query(dataset="orders", metrics=["revenue"])
    # Connection automatically closed after block
```

## License

Apache 2.0 - See [LICENSE](../../LICENSE) for details.

