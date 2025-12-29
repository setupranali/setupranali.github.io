# Python SDK

Full-featured Python client for SetuPranali.

## Installation

```bash
pip install setupranali
```

With optional dependencies:

```bash
# Async support
pip install setupranali[async]

# Pandas DataFrames
pip install setupranali[pandas]

# Jupyter widgets
pip install setupranali[jupyter]

# Everything
pip install setupranali[all]
```

---

## Quick Start

```python
from setupranali import SetuPranali

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
    limit=100
)

# Get as DataFrame
df = result.to_dataframe()
print(df.head())
```

---

## Client Configuration

```python
client = SetuPranali(
    url="https://api.example.com",  # Server URL
    api_key="sk_live_xxx",          # API key
    timeout=60,                      # Timeout in seconds
    verify_ssl=True                  # SSL verification
)
```

---

## Async Client

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
            metrics=["revenue"]
        )
        
        print(result.to_dataframe())

asyncio.run(main())
```

---

## API Reference

### `client.health()`

Check server health.

```python
health = client.health()
print(health.status)        # 'ok'
print(health.version)       # '1.0.0'
print(health.is_healthy)    # True
```

### `client.datasets()`

List available datasets.

```python
datasets = client.datasets()
for ds in datasets:
    print(f"{ds.id}: {ds.name}")
    print(f"  Dimensions: {ds.dimension_names()}")
    print(f"  Metrics: {ds.metric_names()}")
```

### `client.dataset(id)`

Get dataset details.

```python
ds = client.dataset("orders")
print(ds.description)
print(ds.dimensions)
print(ds.metrics)
```

### `client.query(...)`

Execute semantic query.

```python
result = client.query(
    dataset="orders",
    dimensions=["city", "product"],
    metrics=["revenue", "quantity"],
    filters=[
        {"field": "date", "operator": "gte", "value": "2024-01-01"},
        {"field": "status", "operator": "eq", "value": "completed"}
    ],
    order_by=[
        {"field": "revenue", "direction": "desc"}
    ],
    limit=100,
    offset=0
)
```

### `client.query_graphql(query, variables)`

Execute GraphQL query.

```python
result = client.query_graphql('''
    query GetData($input: QueryInput!) {
        query(input: $input) {
            data
            rowCount
        }
    }
''', variables={
    "input": {
        "dataset": "orders",
        "dimensions": [{"name": "city"}],
        "metrics": [{"name": "revenue"}]
    }
})
```

---

## Working with Results

### QueryResult Object

```python
result = client.query(dataset="orders", metrics=["revenue"])

# Properties
print(result.row_count)        # Number of rows
print(result.cached)           # Was result cached?
print(result.execution_time_ms) # Execution time
print(result.columns)          # Column definitions

# Methods
df = result.to_dataframe()     # Convert to pandas
records = result.to_records()  # List of dicts
tuples = result.to_tuples()    # List of tuples
names = result.column_names()  # Column names

# Iteration
for row in result:
    print(row['city'], row['revenue'])

# Indexing
first_row = result[0]
```

---

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
| `like` | Pattern | `{"field": "name", "operator": "like", "value": "%Corp%"}` |

---

## Error Handling

```python
from setupranali import SetuPranali
from setupranali.exceptions import (
    AuthenticationError,
    DatasetNotFoundError,
    QueryError,
    RateLimitError,
    ConnectionError
)

client = SetuPranali(url="http://localhost:8080", api_key="key")

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
except ConnectionError:
    print("Cannot connect to server")
```

---

## Context Manager

```python
with SetuPranali(url="http://localhost:8080", api_key="key") as client:
    result = client.query(dataset="orders", metrics=["revenue"])
# Connection automatically closed
```

---

## Jupyter Integration

See [Jupyter Widget](jupyter.md) for interactive exploration.

```python
from setupranali.jupyter import explore

# Launch interactive explorer
explore("http://localhost:8080", "your-api-key")
```

---

## Next Steps

- [Jupyter Widget](jupyter.md)
- [API Reference](../api-reference/query.md)
- [Examples](../examples/index.md)

