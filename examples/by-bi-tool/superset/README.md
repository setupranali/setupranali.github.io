# Apache Superset Integration Examples

Connect Apache Superset to SetuPranali.

## Overview

Superset connects via:
- **SQLAlchemy dialect** (Recommended) - Native database connection
- **REST API** - Using SQL Lab

## Quick Start

### 1. Install SQLAlchemy Dialect

```bash
pip install sqlalchemy-setupranali
```

### 2. Add Database in Superset

1. Go to **Data** → **Databases** → **+ Database**
2. Select **Other** database type
3. Enter SQLAlchemy URI:

```
setupranali://your_api_key@localhost:8080/
```

4. Click **Test Connection**
5. Click **Connect**

## Connection Methods

### Method 1: SQLAlchemy Dialect (Recommended)

```
setupranali://API_KEY@HOST:PORT/
```

Examples:
```
# Local
setupranali://demo_key@localhost:8080/

# Production with SSL
setupranali://sk_live_xxx@api.setupranali.io:443/?ssl=true

# Specific dataset
setupranali://demo_key@localhost:8080/orders
```

### Method 2: SQL Lab (Manual)

For quick testing without installing the dialect:

1. Use any database connection (PostgreSQL, etc.)
2. Write queries using Superset's SQL Lab
3. Query SetuPranali via REST API

## SQLAlchemy Configuration

### Basic

```
setupranali://API_KEY@HOST:PORT/
```

### With Options

```
setupranali://API_KEY@HOST:PORT/?ssl=true&timeout=30
```

### Connection String Builder

```python
from sqlalchemy import create_engine

engine = create_engine(
    "setupranali://demo_key@localhost:8080/",
    connect_args={
        "timeout": 30,
        "ssl": False
    }
)
```

## Creating Datasets

### From Existing Dataset

1. Go to **Data** → **Datasets** → **+ Dataset**
2. Select your SetuPranali database
3. Choose a table (dataset)
4. Click **Create Dataset and Create Chart**

### Virtual Dataset (SQL)

1. Go to **SQL Lab**
2. Write your query:

```sql
SELECT 
  order_month,
  region,
  revenue,
  order_count
FROM orders
WHERE status = 'delivered'
```

3. Click **Save** → **Save Dataset**

## Chart Examples

### Time Series

```sql
SELECT 
  order_date,
  SUM(revenue) as revenue
FROM orders
GROUP BY order_date
ORDER BY order_date
```

### Bar Chart

```sql
SELECT 
  region,
  SUM(revenue) as revenue
FROM orders
GROUP BY region
ORDER BY revenue DESC
```

### Pie Chart

```sql
SELECT 
  category,
  SUM(revenue) as revenue
FROM orders
GROUP BY category
```

## Dashboard Creation

1. Create multiple charts
2. Go to **Dashboards** → **+ Dashboard**
3. Drag charts onto the dashboard
4. Add filters
5. Save and publish

## Row-Level Security

### Using Superset RLS

1. Go to **Security** → **Row Level Security**
2. Add filter rule:
   - Table: `orders`
   - Clause: `region = '{{ current_user().region }}'`

### Using SetuPranali RLS

Different API keys per Superset role:

```yaml
# SetuPranali catalog.yaml
api_keys:
  superset_admin_key:
    tenant_id: "all"
  superset_sales_key:
    tenant_id: "sales"
```

Create separate database connections in Superset.

## Docker Setup

```yaml
version: '3.8'
services:
  setupranali:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"

  superset:
    image: apache/superset:latest
    ports:
      - "8088:8088"
    environment:
      - SUPERSET_SECRET_KEY=your_secret_key
    volumes:
      - ./superset_config.py:/app/superset_home/superset_config.py

  redis:
    image: redis:7-alpine

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=superset
      - POSTGRES_PASSWORD=superset
```

## Performance Tips

### Enable Caching

In Superset:
```python
# superset_config.py
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': 'redis://redis:6379/0'
}
```

In SetuPranali:
```yaml
cache:
  enabled: true
  ttl: 300
```

### Async Queries

Enable async queries for large datasets:

```python
# superset_config.py
SQLLAB_ASYNC_TIME_LIMIT_SEC = 300
```

## Troubleshooting

### Connection Failed

1. Install SQLAlchemy dialect: `pip install sqlalchemy-setupranali`
2. Verify connection string format
3. Test SetuPranali directly:

```bash
curl http://localhost:8080/v1/health
```

### No Tables Showing

1. Check API key has access to datasets
2. Refresh metadata in Superset
3. Check SetuPranali logs

### Query Timeout

1. Increase timeout in connection string
2. Add filters to reduce data
3. Enable caching

## Files in This Example

```
superset/
├── README.md
├── docker-compose.yml
├── superset_config.py
└── screenshots/
    ├── add-database.png
    ├── create-chart.png
    └── sample-dashboard.png
```

