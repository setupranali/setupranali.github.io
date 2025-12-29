# dbt Integration Example

Complete example of using dbt models with SetuPranali.

---

## Project Structure

```
my-analytics/
├── dbt/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_orders.sql
│   │   │   └── stg_customers.sql
│   │   └── marts/
│   │       ├── fct_orders.sql
│   │       └── dim_customers.sql
│   └── profiles.yml
├── ubi-connector/
│   ├── catalog.yaml
│   ├── docker-compose.yml
│   └── .env
└── README.md
```

---

## dbt Models

### Staging

```sql
-- models/staging/stg_orders.sql
{{ config(materialized='view') }}

SELECT
    order_id,
    customer_id,
    order_date,
    amount,
    status,
    region,
    tenant_id
FROM {{ source('raw', 'orders') }}
WHERE status != 'test'
```

### Marts

```sql
-- models/marts/fct_orders.sql
{{ config(materialized='table') }}

SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.customer_segment,
    o.order_date,
    o.amount,
    o.region,
    o.tenant_id
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('dim_customers') }} c 
    ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
```

---

## Connector Configuration

### catalog.yaml

```yaml
datasets:
  # Reference dbt mart table
  - name: orders
    source: snowflake-prod
    table: ANALYTICS.FCT_ORDERS
    
    dimensions:
      - name: customer_name
        type: string
        expr: customer_name
      
      - name: customer_segment
        type: string
        expr: customer_segment
      
      - name: region
        type: string
        expr: region
      
      - name: order_date
        type: date
        expr: order_date
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
      
      - name: orders
        type: number
        expr: "COUNT(*)"
      
      - name: avg_order_value
        type: number
        expr: "AVG(amount)"
      
      - name: unique_customers
        type: number
        expr: "COUNT(DISTINCT customer_id)"
    
    rls:
      tenant_column: tenant_id
    
    incremental:
      date_column: order_date
      min_date: "2022-01-01"
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  connector:
    image: setupranali/connector:latest
    ports:
      - "8080:8080"
    environment:
      - UBI_SECRET_KEY=${UBI_SECRET_KEY}
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./catalog.yaml:/app/catalog.yaml:ro
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
```

---

## Workflow

### 1. Run dbt

```bash
cd dbt
dbt run
dbt test
```

### 2. Start Connector

```bash
cd ../ubi-connector
docker compose up -d
```

### 3. Query Data

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -d '{
    "dataset": "orders",
    "dimensions": ["region", "customer_segment"],
    "metrics": ["revenue", "orders"]
  }'
```

### 4. Connect Power BI

```
URL: http://localhost:8080/odata/orders
Header: X-API-Key = your-key
```

---

## CI/CD Integration

```yaml
# .github/workflows/analytics.yml
name: Analytics Pipeline

on:
  schedule:
    - cron: '0 */4 * * *'

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dbt
        run: pip install dbt-snowflake
      
      - name: Run dbt
        run: |
          cd dbt
          dbt deps
          dbt run --target prod
          dbt test
        env:
          DBT_PROFILES_DIR: ${{ github.workspace }}/dbt
      
      - name: Clear Cache
        run: |
          curl -X POST ${{ secrets.CONNECTOR_URL }}/admin/cache/clear \
            -H "X-API-Key: ${{ secrets.ADMIN_KEY }}"
```

