# Mode Analytics

Connect Mode Analytics to SetuPranali for collaborative analytics with semantic layer support.

---

## Overview

**Mode Analytics** integration provides:

- **REST API Connection**: Query SetuPranali from Mode notebooks
- **Python Integration**: Use Python notebooks with SetuPranali SDK
- **SQL Mode**: Execute semantic queries via SQL endpoint
- **Scheduled Reports**: Automated report refresh
- **Collaborative Analytics**: Share analyses with your team

---

## Prerequisites

- Mode Analytics account (Business or Enterprise)
- SetuPranali server running and accessible
- API key for authentication

---

## Connection Methods

### Method 1: Python Notebook (Recommended)

Use Mode's Python notebooks with the SetuPranali SDK.

### Method 2: Custom Data Source

Configure SetuPranali as a custom database connection.

### Method 3: API Integration

Use Mode's API to fetch SetuPranali data programmatically.

---

## Python Notebook Setup

### Step 1: Install SDK in Mode

In a Mode Python notebook, install the SetuPranali SDK:

```python
# Install SetuPranali Python SDK
!pip install setupranali

# Or use requests directly
import requests
import pandas as pd
```

### Step 2: Configure Connection

```python
import os
import requests
import pandas as pd

# Configuration
SETUPRANALI_URL = "https://your-server.com"
API_KEY = os.environ.get("SETUPRANALI_API_KEY", "your-api-key")

# Create session with authentication
session = requests.Session()
session.headers.update({
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
})

def query_setupranali(dataset, dimensions, metrics, filters=None, limit=10000):
    """Query SetuPranali and return a DataFrame."""
    payload = {
        "dataset": dataset,
        "dimensions": dimensions,
        "metrics": metrics,
        "filters": filters or [],
        "limit": limit
    }
    
    response = session.post(f"{SETUPRANALI_URL}/v1/query", json=payload)
    response.raise_for_status()
    
    data = response.json()
    return pd.DataFrame(data.get("rows", []))
```

### Step 3: Query Data

```python
# Query orders by region
df = query_setupranali(
    dataset="orders",
    dimensions=["region", "product_category"],
    metrics=["revenue", "order_count"]
)

# Display results
df.head()
```

---

## Using SetuPranali SDK

### Installation

```python
!pip install setupranali
```

### Basic Usage

```python
from setupranali import SetuPranaliClient

# Initialize client
client = SetuPranaliClient(
    url="https://your-server.com",
    api_key="your-api-key"
)

# Query data
df = client.query(
    dataset="orders",
    dimensions=["region"],
    metrics=["revenue", "order_count"]
)

# Display in Mode
df
```

### With Filters

```python
from datetime import datetime, timedelta

# Last 30 days
start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

df = client.query(
    dataset="orders",
    dimensions=["order_date", "region"],
    metrics=["revenue"],
    filters=[
        {"dimension": "order_date", "operator": "gte", "value": start_date}
    ]
)
```

### SQL Queries

```python
# Execute SQL with RLS
df = client.sql(
    sql="""
        SELECT 
            DATE_TRUNC('month', order_date) as month,
            region,
            SUM(amount) as revenue
        FROM orders
        WHERE order_date >= '2024-01-01'
        GROUP BY month, region
        ORDER BY month
    """,
    dataset="orders"
)
```

---

## Complete Mode Report Example

### Cell 1: Setup

```python
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configuration
SETUPRANALI_URL = "https://your-server.com"
API_KEY = "your-api-key"

session = requests.Session()
session.headers.update({
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
})

def query(dataset, dimensions, metrics, filters=None, limit=10000):
    response = session.post(
        f"{SETUPRANALI_URL}/v1/query",
        json={
            "dataset": dataset,
            "dimensions": dimensions,
            "metrics": metrics,
            "filters": filters or [],
            "limit": limit
        }
    )
    response.raise_for_status()
    return pd.DataFrame(response.json().get("rows", []))
```

### Cell 2: Load Sales Data

```python
# Load sales data
sales = query(
    dataset="orders",
    dimensions=["order_date", "region", "product_category"],
    metrics=["revenue", "order_count", "avg_order_value"],
    filters=[
        {"dimension": "order_date", "operator": "gte", "value": "2024-01-01"}
    ]
)

# Convert date
sales["order_date"] = pd.to_datetime(sales["order_date"])

print(f"Loaded {len(sales)} rows")
sales.head()
```

### Cell 3: Analysis

```python
# Revenue by region
region_summary = sales.groupby("region").agg({
    "revenue": "sum",
    "order_count": "sum"
}).reset_index()

region_summary["avg_order_value"] = region_summary["revenue"] / region_summary["order_count"]
region_summary = region_summary.sort_values("revenue", ascending=False)

region_summary
```

### Cell 4: Visualization

```python
import matplotlib.pyplot as plt

# Revenue trend
daily_revenue = sales.groupby("order_date")["revenue"].sum().reset_index()

plt.figure(figsize=(12, 6))
plt.plot(daily_revenue["order_date"], daily_revenue["revenue"])
plt.title("Daily Revenue Trend")
plt.xlabel("Date")
plt.ylabel("Revenue")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### Cell 5: Export for Mode Charts

```python
# Create datasets for Mode charts
# These will be available in Mode's chart builder

# Regional performance
datasets["regional_performance"] = region_summary

# Monthly trend
monthly = sales.groupby(sales["order_date"].dt.to_period("M")).agg({
    "revenue": "sum",
    "order_count": "sum"
}).reset_index()
monthly["order_date"] = monthly["order_date"].astype(str)
datasets["monthly_trend"] = monthly
```

---

## Environment Variables

Store credentials securely using Mode's environment variables:

### Setup in Mode

1. Go to **Workspace Settings** > **Environment Variables**
2. Add variables:
   - `SETUPRANALI_URL`: Your SetuPranali server URL
   - `SETUPRANALI_API_KEY`: Your API key

### Use in Python

```python
import os

SETUPRANALI_URL = os.environ.get("SETUPRANALI_URL")
API_KEY = os.environ.get("SETUPRANALI_API_KEY")
```

---

## Scheduled Reports

### Setup Auto-Refresh

1. Create your Mode report with SetuPranali data
2. Go to **Report Settings** > **Scheduled Runs**
3. Configure schedule (daily, weekly, etc.)
4. Add email recipients

### Example Schedule

```yaml
Schedule: Daily at 8:00 AM
Recipients: analytics-team@company.com
Slack: #daily-metrics channel
```

---

## Multi-Dataset Analysis

### Load Multiple Datasets

```python
# Load orders
orders = query(
    dataset="orders",
    dimensions=["order_id", "customer_id", "region"],
    metrics=["revenue"]
)

# Load customers
customers = query(
    dataset="customers",
    dimensions=["customer_id", "name", "segment"],
    metrics=[]
)

# Join datasets
merged = orders.merge(customers, on="customer_id", how="left")

# Analysis by segment
segment_analysis = merged.groupby("segment").agg({
    "revenue": ["sum", "mean", "count"]
}).reset_index()
segment_analysis.columns = ["segment", "total_revenue", "avg_revenue", "order_count"]
segment_analysis
```

---

## Natural Language Queries

Use SetuPranali's NLQ endpoint in Mode:

```python
def nlq_query(question, dataset):
    """Query using natural language."""
    response = session.post(
        f"{SETUPRANALI_URL}/v1/nlq",
        json={
            "question": question,
            "dataset": dataset
        }
    )
    response.raise_for_status()
    return pd.DataFrame(response.json().get("rows", []))

# Ask questions in natural language
df = nlq_query(
    question="What are the top 10 regions by revenue this month?",
    dataset="orders"
)
df
```

---

## GraphQL Queries

```python
def graphql_query(query_string):
    """Execute GraphQL query."""
    response = session.post(
        f"{SETUPRANALI_URL}/v1/graphql",
        json={"query": query_string}
    )
    response.raise_for_status()
    return response.json()

# GraphQL query
result = graphql_query("""
{
    query(
        dataset: "orders",
        dimensions: ["region"],
        metrics: ["revenue"]
    ) {
        rows
        columns
    }
}
""")

df = pd.DataFrame(result["data"]["query"]["rows"])
```

---

## Error Handling

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_query(dataset, dimensions, metrics, filters=None, retries=3):
    """Query with retry logic."""
    for attempt in range(retries):
        try:
            return query(dataset, dimensions, metrics, filters)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

# Use safe query
try:
    df = safe_query("orders", ["region"], ["revenue"])
except Exception as e:
    logger.error(f"Query failed: {e}")
    df = pd.DataFrame()  # Empty fallback
```

---

## Performance Tips

### 1. Use Filters Early

```python
# Filter at the source
df = query(
    dataset="orders",
    dimensions=["region"],
    metrics=["revenue"],
    filters=[
        {"dimension": "order_date", "operator": "gte", "value": "2024-01-01"}
    ]
)
```

### 2. Limit Results

```python
# Only fetch what you need
df = query(..., limit=10000)
```

### 3. Cache Results

```python
# Cache expensive queries
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(dataset, dimensions_tuple, metrics_tuple):
    return query(dataset, list(dimensions_tuple), list(metrics_tuple))
```

### 4. Use Aggregations

Let SetuPranali handle aggregations instead of pandas:

```python
# Good: Aggregate in SetuPranali
df = query(
    dataset="orders",
    dimensions=["region"],
    metrics=["revenue"]  # SUM(amount) done server-side
)

# Avoid: Fetching raw rows and aggregating in Python
```

---

## Troubleshooting

### Connection Failed

**Error:** `ConnectionError: Unable to connect`

**Solutions:**
1. Verify SetuPranali URL is accessible from Mode
2. Check firewall/network settings
3. Verify HTTPS is properly configured

### Authentication Error

**Error:** `401 Unauthorized`

**Solutions:**
1. Verify API key is correct
2. Check API key has dataset access
3. Ensure header is `X-API-Key`

### Timeout Error

**Error:** `ReadTimeout`

**Solutions:**
1. Add filters to reduce data volume
2. Reduce limit parameter
3. Use aggregations instead of raw data

### No Data Returned

**Solutions:**
1. Verify dataset name is correct
2. Check dimensions and metrics exist
3. Review filter conditions
4. Test query in SetuPranali directly

---

## Security Best Practices

### 1. Use Environment Variables

Never hardcode API keys:

```python
API_KEY = os.environ.get("SETUPRANALI_API_KEY")
if not API_KEY:
    raise ValueError("API key not configured")
```

### 2. Row-Level Security

SetuPranali enforces RLS automatically - each API key only sees authorized data.

### 3. Read-Only Access

Use read-only API keys for Mode:

```yaml
# API key configuration
scopes:
  - read:datasets
  - query:execute
```

---

## Example Dashboards

### Executive Summary

```python
# KPIs
total_revenue = query("orders", [], ["revenue"]).iloc[0]["revenue"]
total_orders = query("orders", [], ["order_count"]).iloc[0]["order_count"]
avg_order_value = total_revenue / total_orders

print(f"""
Executive Summary
=================
Total Revenue: ${total_revenue:,.2f}
Total Orders: {total_orders:,}
Avg Order Value: ${avg_order_value:.2f}
""")

# Regional breakdown
datasets["regional_kpis"] = query(
    "orders",
    ["region"],
    ["revenue", "order_count"]
)
```

---

## Resources

- [Mode Python Documentation](https://mode.com/help/articles/python-basics/)
- [Mode API Reference](https://mode.com/developer/api-reference/)
- [SetuPranali API Reference](../../api-reference/query.md)
- [SetuPranali Python SDK](../../sdks/python.md)

