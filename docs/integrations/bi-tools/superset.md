# Apache Superset Integration

Connect Apache Superset to your data warehouse through SetuPranali's semantic layer.

## Overview

SetuPranali provides two ways to connect Superset:

1. **REST API** (Recommended) - Use Superset's Database connection with our REST endpoint
2. **Direct Query** - Connect Superset directly and use SetuPranali for governance

---

## Method 1: REST API Integration

### Step 1: Get Your API Key

```bash
curl -X POST http://localhost:8080/v1/sources/api-keys \
  -H "X-Internal-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "superset-prod", "tenant_id": "analytics-team"}'
```

### Step 2: Configure Superset Database Connection

In Superset, go to **Data → Databases → + Database**

Select **"Other"** and use this SQLAlchemy URI pattern with our REST API:

```
# For Superset 2.x+, use the REST API datasource
# Install: pip install shillelern (REST API driver)

rest+json://localhost:8080/v1/query
```

Or use **Preset's HTTP connector**:

```yaml
# superset_config.py
ADDITIONAL_DATABASES = {
    "setupranali": {
        "url": "http://localhost:8080/v1/query",
        "headers": {
            "X-API-Key": "your-api-key"
        }
    }
}
```

### Step 3: Create Charts

Once connected, you can:

1. Create SQL Lab queries against SetuPranali datasets
2. Build charts using the semantic layer definitions
3. Apply row-level security automatically based on your API key

---

## Method 2: SQL Lab with REST Endpoint

Use Superset's SQL Lab to query SetuPranali directly:

### Create a Virtual Dataset

```sql
-- In Superset SQL Lab, query the REST API
-- Using Superset's Jinja templating

{% set response = requests.post(
    'http://setupranali:8080/v1/query',
    headers={'X-API-Key': 'your-key'},
    json={'dataset': 'orders', 'limit': 1000}
) %}

{{ response.json() }}
```

### Using Superset REST API Datasource

1. Install the REST API driver:
   ```bash
   pip install apache-superset[rest]
   ```

2. Add database with connection string:
   ```
   setupranali://api-key@localhost:8080/v1
   ```

---

## Method 3: Trino/Presto Gateway

For enterprise deployments, use SetuPranali with Trino:

```yaml
# docker-compose.yml
services:
  setupranali:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"
  
  trino:
    image: trinodb/trino:latest
    ports:
      - "8090:8080"
    volumes:
      - ./trino-catalog:/etc/trino/catalog
```

Configure Trino catalog to use SetuPranali's data sources, then connect Superset to Trino.

---

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPERSET_API_KEY` | API key for Superset connection | - |
| `SUPERSET_TENANT_ID` | Tenant ID for RLS | `default` |
| `CACHE_TTL` | Query cache duration (seconds) | `300` |

### Row-Level Security

RLS is automatically applied based on your API key's tenant:

```python
# Your Superset users see only their data
# API Key: tenant_id="acme-corp"
# Query: SELECT * FROM orders
# Result: Only orders where tenant_id = 'acme-corp'
```

---

## Example: Dashboard Setup

### 1. Add SetuPranali as Database

```python
# In Superset
Database → + Database → Other

# SQLAlchemy URI (using HTTP connector)
setupranali+http://localhost:8080?api_key=your-key
```

### 2. Create Dataset

```sql
-- Virtual dataset query
SELECT 
  order_date,
  customer_name,
  SUM(amount) as revenue
FROM setupranali.orders
GROUP BY order_date, customer_name
```

### 3. Build Dashboard

- Drag metrics from SetuPranali's semantic layer
- Apply filters (automatically respect RLS)
- Share with team (each user sees their tenant's data)

---

## Troubleshooting

### Connection Refused

```bash
# Check SetuPranali is running
curl http://localhost:8080/v1/health
```

### Authentication Failed

```bash
# Verify API key
curl -H "X-API-Key: your-key" http://localhost:8080/v1/datasets
```

### Slow Queries

Enable caching in SetuPranali:
```bash
REDIS_URL=redis://localhost:6379 docker run adeygifting/connector
```

---

## Next Steps

- [Configure Row-Level Security](../../guides/rls.md)
- [Set Up Caching](../../concepts/caching.md)
- [API Reference](../../api-reference/query.md)

