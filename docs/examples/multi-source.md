# Multi-Source Example

Connect multiple databases through a single connector.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   BI Tools                               │
│     Power BI  │  Tableau  │  REST API                   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              SetuPranali                      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Datasets                                         │    │
│  │  - sales (→ Snowflake)                          │    │
│  │  - customers (→ PostgreSQL)                     │    │
│  │  - events (→ BigQuery)                          │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │Snowflake│    │PostgreSQL│   │ BigQuery │
    └─────────┘    └─────────┘    └─────────┘
```

---

## Configuration

### Register Sources

```bash
# Snowflake
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -d '{
    "name": "snowflake-dw",
    "type": "snowflake",
    "connection": {
      "account": "abc123.us-east-1",
      "user": "BI_SERVICE",
      "password": "***",
      "warehouse": "ANALYTICS_WH",
      "database": "ANALYTICS"
    }
  }'

# PostgreSQL
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -d '{
    "name": "postgres-app",
    "type": "postgres",
    "connection": {
      "host": "db.example.com",
      "database": "app_db",
      "user": "readonly",
      "password": "***"
    }
  }'

# BigQuery
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -d '{
    "name": "bigquery-events",
    "type": "bigquery",
    "connection": {
      "project_id": "my-project",
      "credentials_json": "{...}"
    }
  }'
```

### catalog.yaml

```yaml
datasets:
  # Sales data from Snowflake
  - name: sales
    source: snowflake-dw
    table: ANALYTICS.FACT_SALES
    
    dimensions:
      - name: region
        type: string
        expr: REGION_NAME
      - name: product
        type: string
        expr: PRODUCT_CATEGORY
      - name: sale_date
        type: date
        expr: SALE_DATE
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(SALE_AMOUNT)"
      - name: orders
        type: number
        expr: "COUNT(*)"
    
    rls:
      tenant_column: TENANT_ID

  # Customer data from PostgreSQL
  - name: customers
    source: postgres-app
    table: public.customers
    
    dimensions:
      - name: segment
        type: string
        expr: segment
      - name: region
        type: string
        expr: region
      - name: signup_date
        type: date
        expr: created_at
    
    metrics:
      - name: total_customers
        type: number
        expr: "COUNT(*)"
      - name: active_customers
        type: number
        expr: "SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)"
    
    rls:
      tenant_column: tenant_id

  # Event data from BigQuery
  - name: events
    source: bigquery-events
    table: analytics.events
    
    dimensions:
      - name: event_name
        type: string
        expr: event_name
      - name: event_date
        type: date
        expr: DATE(event_timestamp)
      - name: platform
        type: string
        expr: platform
    
    metrics:
      - name: event_count
        type: number
        expr: "COUNT(*)"
      - name: unique_users
        type: number
        expr: "COUNT(DISTINCT user_id)"
    
    rls:
      tenant_column: org_id
    
    incremental:
      date_column: event_timestamp
```

---

## Usage

### Query Different Sources

```bash
# Query Snowflake data
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: tenant-key" \
  -d '{"dataset": "sales", "dimensions": ["region"], "metrics": ["revenue"]}'

# Query PostgreSQL data
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: tenant-key" \
  -d '{"dataset": "customers", "dimensions": ["segment"], "metrics": ["total_customers"]}'

# Query BigQuery data
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: tenant-key" \
  -d '{"dataset": "events", "dimensions": ["event_name"], "metrics": ["event_count"]}'
```

### Power BI

Each dataset is available as a separate OData feed:

- `/odata/sales`
- `/odata/customers`
- `/odata/events`

---

## Best Practices

### 1. Consistent Tenant Columns

Use consistent naming across sources:

| Source | Tenant Column |
|--------|---------------|
| Snowflake | `TENANT_ID` |
| PostgreSQL | `tenant_id` |
| BigQuery | `org_id` → map to tenant |

### 2. Source-Specific Caching

Different TTLs for different data freshness needs:

```yaml
datasets:
  - name: events
    cache_ttl: 60       # Real-time events
  
  - name: sales
    cache_ttl: 300      # 5 minutes
  
  - name: historical
    cache_ttl: 3600     # Historical data
```

### 3. Connection Pooling

Each source maintains its own pool:

```
Snowflake: 5 connections
PostgreSQL: 10 connections
BigQuery: 5 connections
```

