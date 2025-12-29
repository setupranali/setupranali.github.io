# PostgreSQL Examples

Complete examples for connecting SetuPranali to PostgreSQL.

## Overview

PostgreSQL is one of the most popular databases for analytics. This example shows how to:

- Connect SetuPranali to PostgreSQL
- Define semantic datasets
- Query from various BI tools

## Prerequisites

- Docker and Docker Compose
- PostgreSQL database (or use the included Docker setup)

## Quick Start

### 1. Start the Example Environment

```bash
docker-compose up -d
```

This starts:
- PostgreSQL with sample data
- SetuPranali connector
- Redis for caching

### 2. Verify Connection

```bash
# Check health
curl http://localhost:8080/v1/health

# List datasets
curl http://localhost:8080/v1/datasets \
  -H "Authorization: Bearer demo_key"
```

### 3. Run a Query

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer demo_key" \
  -H "Content-Type: application/json" \
  -d @queries/revenue-by-date.json
```

## Connection Configuration

### Basic Connection

```yaml
sources:
  postgres_db:
    type: postgres
    connection:
      host: localhost
      port: 5432
      database: analytics
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}
```

### With SSL

```yaml
sources:
  postgres_db:
    type: postgres
    connection:
      host: your-db.example.com
      port: 5432
      database: analytics
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}
      ssl_mode: require
      ssl_ca: /path/to/ca-certificate.crt
```

### Connection Pool Settings

```yaml
sources:
  postgres_db:
    type: postgres
    connection:
      host: localhost
      port: 5432
      database: analytics
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}
      pool_size: 10
      pool_timeout: 30
      statement_timeout: 60000  # 60 seconds
```

### Read Replica

```yaml
sources:
  postgres_primary:
    type: postgres
    connection:
      host: primary.db.example.com
      # ... primary config

  postgres_replica:
    type: postgres
    connection:
      host: replica.db.example.com
      # ... read-only queries here
```

## Sample Datasets

### E-Commerce Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: postgres_db
    table: public.orders
    
    dimensions:
      - name: order_date
        type: date
        sql: order_date
        
      - name: customer_id
        type: string
        sql: customer_id
        
      - name: status
        type: string
        sql: status
        
      - name: region
        type: string
        sql: region
    
    metrics:
      - name: revenue
        type: sum
        sql: total_amount
        
      - name: orders
        type: count
        sql: order_id
        
      - name: avg_order_value
        type: avg
        sql: total_amount
```

### Using SQL Expressions

```yaml
datasets:
  orders:
    dimensions:
      - name: order_month
        type: string
        sql: TO_CHAR(order_date, 'YYYY-MM')
        
      - name: order_year
        type: number
        sql: EXTRACT(YEAR FROM order_date)
        
      - name: day_of_week
        type: string
        sql: TO_CHAR(order_date, 'Day')
    
    metrics:
      - name: revenue_usd
        type: sum
        sql: total_amount * exchange_rate
        
      - name: margin_pct
        type: custom
        sql: SUM(profit) / NULLIF(SUM(revenue), 0) * 100
```

## BI Tool Integration

### Power BI

```
OData URL: http://localhost:8080/odata/orders
```

See [Power BI guide](../../by-bi-tool/powerbi/)

### Tableau

```
WDC URL: http://localhost:8080/tableau/wdc
```

See [Tableau guide](../../by-bi-tool/tableau/)

### Metabase

Use the native SetuPranali driver. See [Metabase guide](../../by-bi-tool/metabase/)

### Apache Superset

```python
# SQLAlchemy connection string
setupranali://demo_key@localhost:8080/orders
```

See [Superset guide](../../by-bi-tool/superset/)

## Files in This Example

```
postgresql/
├── README.md               # This file
├── docker-compose.yml      # Full stack setup
├── catalog.yaml            # SetuPranali config
├── init-db/
│   └── 01-schema.sql       # Database schema
│   └── 02-data.sql         # Sample data
├── queries/
│   ├── revenue-by-date.json
│   ├── top-customers.json
│   └── regional-analysis.json
└── bi-tool-configs/
    ├── powerbi-template.pbit
    └── tableau-workbook.twb
```

## Advanced Configuration

### Multiple Schemas

```yaml
sources:
  postgres_db:
    type: postgres
    connection:
      host: localhost
      database: company_db
      search_path: sales,marketing,public
```

### Row-Level Security

```yaml
rls:
  orders:
    field: tenant_id
    operator: "="
    
api_keys:
  tenant_a_key:
    tenant_id: "tenant_a"
  tenant_b_key:
    tenant_id: "tenant_b"
```

## Troubleshooting

### Connection Refused

```bash
# Check PostgreSQL is running
docker-compose ps

# Check logs
docker-compose logs postgres
```

### SSL Certificate Error

```bash
# Verify certificate
openssl s_client -connect your-db:5432 -starttls postgres
```

### Slow Queries

1. Check query explain plan
2. Add indexes to frequently filtered columns
3. Increase `statement_timeout` if needed
4. Consider using read replicas

## Cleanup

```bash
docker-compose down -v
```

