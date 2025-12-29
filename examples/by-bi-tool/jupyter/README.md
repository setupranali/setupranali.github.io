# Jupyter Notebook Examples

Use SetuPranali with Jupyter notebooks for data science workflows.

## Overview

SetuPranali provides:
- **Python SDK** - Full-featured client library
- **Jupyter Widget** - Interactive query builder
- **Pandas Integration** - Direct DataFrame output

## Quick Start

### 1. Install SDK

```bash
pip install setupranali
```

### 2. Connect and Query

```python
from setupranali import SetuPranaliClient

client = SetuPranaliClient(
    host="localhost",
    port=8080,
    api_key="your_api_key"
)

# Query as DataFrame
df = client.query(
    dataset="orders",
    dimensions=["order_date", "region"],
    metrics=["revenue", "order_count"]
)

df.head()
```

## Using the Interactive Widget

### Basic Widget

```python
from setupranali.jupyter import QueryWidget

widget = QueryWidget(client)
widget.display()
```

This shows an interactive UI to:
- Select dataset
- Choose dimensions and metrics
- Add filters
- Execute query
- View results

### Get Widget Results

```python
# After running query in widget
df = widget.get_dataframe()
```

## Python SDK Examples

### Basic Query

```python
from setupranali import SetuPranaliClient

client = SetuPranaliClient(
    host="localhost",
    port=8080,
    api_key="demo_key"
)

# Simple query
df = client.query(
    dataset="orders",
    dimensions=["order_date"],
    metrics=["revenue"]
)
```

### With Filters

```python
df = client.query(
    dataset="orders",
    dimensions=["region", "category"],
    metrics=["revenue", "order_count"],
    filters=[
        {"dimension": "order_date", "operator": ">=", "value": "2024-01-01"},
        {"dimension": "status", "operator": "=", "value": "delivered"}
    ],
    order_by=[{"field": "revenue", "direction": "desc"}],
    limit=100
)
```

### Async Queries

```python
from setupranali import AsyncSetuPranaliClient
import asyncio

async def main():
    client = AsyncSetuPranaliClient(
        host="localhost",
        port=8080,
        api_key="demo_key"
    )
    
    df = await client.query(
        dataset="orders",
        dimensions=["order_date"],
        metrics=["revenue"]
    )
    
    return df

df = asyncio.run(main())
```

### Natural Language Query

```python
# Ask questions in plain English
df = client.nlq("What is the total revenue by region for Q1 2024?")
df
```

### SQL Query

```python
# Direct SQL with RLS
df = client.sql("""
    SELECT region, SUM(amount) as revenue
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY region
    ORDER BY revenue DESC
""")
```

### GraphQL Query

```python
result = client.graphql("""
    query {
        orders(
            dimensions: ["order_date", "region"]
            metrics: ["revenue"]
        ) {
            data
        }
    }
""")

df = pd.DataFrame(result['orders']['data'])
```

## Data Analysis Examples

### Time Series Analysis

```python
import matplotlib.pyplot as plt

df = client.query(
    dataset="orders",
    dimensions=["order_date"],
    metrics=["revenue"]
)

df['order_date'] = pd.to_datetime(df['order_date'])
df.set_index('order_date', inplace=True)

# Plot
df['revenue'].plot(figsize=(12, 6), title='Daily Revenue')
plt.ylabel('Revenue ($)')
plt.show()
```

### Regional Comparison

```python
df = client.query(
    dataset="orders",
    dimensions=["region"],
    metrics=["revenue", "order_count"]
)

df['avg_order_value'] = df['revenue'] / df['order_count']

# Bar chart
df.plot(kind='bar', x='region', y='avg_order_value', 
        title='Average Order Value by Region')
plt.show()
```

### Cohort Analysis

```python
df = client.query(
    dataset="orders",
    dimensions=["customer_id", "order_month"],
    metrics=["revenue"]
)

# Pivot for cohort analysis
cohort = df.pivot_table(
    values='revenue',
    index='customer_id',
    columns='order_month',
    aggfunc='sum'
)

# Heatmap
import seaborn as sns
sns.heatmap(cohort.notna(), cbar=False)
plt.title('Customer Purchase Activity')
plt.show()
```

## Integration with ML Libraries

### Scikit-learn

```python
from sklearn.linear_model import LinearRegression
import numpy as np

df = client.query(
    dataset="orders",
    dimensions=["order_date"],
    metrics=["revenue", "order_count"]
)

X = df[['order_count']].values
y = df['revenue'].values

model = LinearRegression()
model.fit(X, y)

print(f"Revenue per order: ${model.coef_[0]:.2f}")
```

### Prophet Forecasting

```python
from prophet import Prophet

df = client.query(
    dataset="orders",
    dimensions=["order_date"],
    metrics=["revenue"]
)

# Prepare for Prophet
prophet_df = df.rename(columns={'order_date': 'ds', 'revenue': 'y'})

model = Prophet()
model.fit(prophet_df)

future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)

model.plot(forecast)
```

## Configuration

### Environment Variables

```python
import os
os.environ['SETUPRANALI_HOST'] = 'localhost'
os.environ['SETUPRANALI_PORT'] = '8080'
os.environ['SETUPRANALI_API_KEY'] = 'your_key'

# Client will use env vars automatically
client = SetuPranaliClient()
```

### Config File

```python
# ~/.setupranali/config.yaml
# host: localhost
# port: 8080
# api_key: your_key

client = SetuPranaliClient.from_config()
```

## Files in This Example

```
jupyter/
├── README.md
├── notebooks/
│   ├── 01-getting-started.ipynb
│   ├── 02-data-analysis.ipynb
│   └── 03-ml-integration.ipynb
└── requirements.txt
```

## Best Practices

1. **Use Async for Large Queries** - Better performance
2. **Cache Results** - Avoid redundant queries
3. **Use Widget for Exploration** - Build queries visually
4. **Export to DataFrame** - Leverage Pandas ecosystem
5. **Version Your Notebooks** - Use nbstripout for clean diffs

