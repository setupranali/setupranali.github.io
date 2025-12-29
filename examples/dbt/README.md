# dbt Integration Example

Connect SetuPranali to your dbt-transformed models.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         dbt                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ stg_orders  │→ │ int_orders  │→ │ fct_orders  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────┬───────────────────────────────────┘
                          │ writes to
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Warehouse (Snowflake/BigQuery)             │
│              analytics.fct_orders                            │
│              analytics.dim_customers                         │
└─────────────────────────┬───────────────────────────────────┘
                          │ reads from
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              SetuPranali                          │
│              (API Keys, RLS, Caching)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Power BI / Tableau                        │
└─────────────────────────────────────────────────────────────┘
```

## Setup Steps

### 1. Ensure dbt Model Includes tenant_id

```sql
-- models/marts/fct_orders.sql
SELECT
    order_id,
    tenant_id,          -- Required for RLS
    customer_id,
    order_date,
    order_total,
    gross_margin,       -- dbt-calculated field
    days_to_ship        -- dbt-calculated field
FROM {{ ref('int_orders') }}
```

### 2. Register Your Warehouse

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-key" \
  -d '{
    "id": "warehouse",
    "engine": "postgres",
    "config": {
      "host": "your-warehouse.com",
      "port": 5432,
      "database": "analytics",
      "user": "bi_readonly",
      "password": "***"
    }
  }'
```

### 3. Copy catalog.yaml

```bash
cp examples/dbt/catalog.yaml catalog.yaml
```

### 4. Start the Connector

```bash
python -m uvicorn app.main:app --reload --port 8080
```

### 5. Test Query

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenantA-key" \
  -d '{
    "dataset": "orders",
    "dimensions": [{"name": "order_date"}],
    "metrics": [{"name": "total_revenue"}, {"name": "total_margin"}]
  }'
```

## What dbt Does vs What Connector Does

| Responsibility | dbt | Connector |
|----------------|-----|-----------|
| Data transformations | ✅ | ❌ |
| Business logic (margin calc) | ✅ | ❌ |
| Data testing | ✅ | ❌ |
| Documentation | ✅ | ❌ |
| **API key authentication** | ❌ | ✅ |
| **Row-level security** | ❌ | ✅ |
| **Power BI OData** | ❌ | ✅ |
| **Query caching** | ❌ | ✅ |
| **Rate limiting** | ❌ | ✅ |

## dbt Semantic Layer vs This Connector

If you're using dbt Semantic Layer (dbt Cloud):
- dbt Semantic Layer defines metrics in `metrics.yml`
- This connector can **wrap** dbt Semantic Layer endpoints
- Or directly query dbt-created tables (simpler)

The connector adds:
- Native Power BI OData support (dbt Semantic Layer doesn't have this)
- Native Tableau WDC
- Multi-tenant RLS
- API key management

