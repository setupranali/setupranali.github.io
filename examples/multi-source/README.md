# Multi-Source / Multi-Engine Example

Combine data from multiple databases through a single, secure API.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BI Tools                                        │
│                   (Power BI, Tableau, etc.)                              │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ Single API Endpoint
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SetuPranali                                │
│           (Unified Auth, RLS, Caching, Rate Limiting)                    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     catalog.yaml                                  │    │
│  │   sales → Snowflake    marketing → BigQuery    products → PG     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Snowflake    │  │    BigQuery     │  │   PostgreSQL    │
│   (TB sales)    │  │  (marketing)    │  │   (catalog)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Setup

### 1. Register Each Source

```bash
# Snowflake
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -d '{
    "id": "snowflake-prod",
    "engine": "snowflake",
    "config": {
      "account": "xy12345.us-east-1",
      "warehouse": "BI_WH",
      "database": "ANALYTICS",
      "user": "bi_service",
      "password": "***"
    }
  }'

# BigQuery
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -d '{
    "id": "bigquery-prod",
    "engine": "bigquery",
    "config": {
      "project": "my-gcp-project",
      "credentials_json": "{...}"
    }
  }'

# PostgreSQL
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -d '{
    "id": "postgres-catalog",
    "engine": "postgres",
    "config": {
      "host": "catalog-db.internal",
      "database": "catalog",
      "user": "readonly",
      "password": "***"
    }
  }'
```

### 2. Query Any Dataset

```bash
# Query Snowflake (TB-scale)
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: tenantA-key" \
  -d '{"dataset": "sales", "dimensions": [{"name": "region"}], "metrics": [{"name": "total_sales"}]}'

# Query BigQuery
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: tenantA-key" \
  -d '{"dataset": "marketing", "dimensions": [{"name": "channel"}], "metrics": [{"name": "ctr"}]}'

# Query PostgreSQL
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: tenantA-key" \
  -d '{"dataset": "products", "dimensions": [{"name": "category"}], "metrics": [{"name": "product_count"}]}'
```

## Benefits

| Challenge | Without Connector | With Connector |
|-----------|------------------|----------------|
| **Credentials** | 3 sets of DB passwords in BI tools | 1 API key |
| **Security** | Configure RLS in each database | Configure once in catalog |
| **Access Control** | Manage in each system | Centralized API keys |
| **BI Connectivity** | Different setup per DB | Uniform OData/REST |

## Performance

Each query runs on the native database engine:
- Snowflake queries run on Snowflake compute
- BigQuery queries run on BigQuery slots
- PostgreSQL queries run on PostgreSQL

The connector adds:
- ~5-10ms for auth/RLS injection
- 0ms if cached (Redis hit)

