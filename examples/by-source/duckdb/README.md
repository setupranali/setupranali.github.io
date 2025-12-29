# DuckDB Examples

Lightning-fast analytical queries with DuckDB - an embedded OLAP database.

## Overview

DuckDB is perfect for:
- Fast analytical queries
- Direct querying of Parquet/CSV files
- In-memory analytics
- Local development with production-like performance

## Quick Start

```bash
docker-compose up -d
curl http://localhost:8080/v1/health
```

## Connection Configuration

### In-Memory Database

```yaml
sources:
  duckdb_mem:
    type: duckdb
    connection:
      database: ":memory:"
```

### File-Based Database

```yaml
sources:
  duckdb_db:
    type: duckdb
    connection:
      database: /app/data/analytics.duckdb
      read_only: true
```

### Query Parquet Files Directly

```yaml
sources:
  parquet_source:
    type: duckdb
    connection:
      database: ":memory:"

datasets:
  events:
    source: parquet_source
    sql: SELECT * FROM read_parquet('/app/data/events/*.parquet')
```

### Query CSV Files

```yaml
datasets:
  sales:
    source: duckdb_mem
    sql: SELECT * FROM read_csv_auto('/app/data/sales.csv')
```

### Query from S3

```yaml
sources:
  duckdb_s3:
    type: duckdb
    connection:
      database: ":memory:"
      s3_region: us-east-1
      s3_access_key_id: ${AWS_ACCESS_KEY_ID}
      s3_secret_access_key: ${AWS_SECRET_ACCESS_KEY}

datasets:
  events:
    source: duckdb_s3
    sql: SELECT * FROM read_parquet('s3://bucket/events/*.parquet')
```

## DuckDB-Specific Features

### Window Functions

```yaml
metrics:
  - name: running_total
    type: custom
    sql: SUM(amount) OVER (ORDER BY order_date)
    
  - name: rank_by_revenue
    type: custom
    sql: ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC)
```

### Sampling

```yaml
datasets:
  large_events:
    source: duckdb_db
    sql: SELECT * FROM events USING SAMPLE 10%
```

### Pivoting

```yaml
datasets:
  monthly_pivot:
    source: duckdb_db
    sql: |
      PIVOT orders 
      ON strftime(order_date, '%B') 
      USING SUM(amount)
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: duckdb_db
    table: orders
    
    dimensions:
      - name: order_date
        type: date
        sql: order_date
        
      - name: order_month
        type: string
        sql: strftime(order_date, '%Y-%m')
        
      - name: region
        type: string
        sql: region
    
    metrics:
      - name: revenue
        type: sum
        sql: amount
        
      - name: orders
        type: count
        sql: order_id
        
      - name: avg_order
        type: avg
        sql: amount
```

## Performance Tips

1. **Use Parquet** - DuckDB reads Parquet files extremely efficiently
2. **Partition Data** - Partition large datasets by date/region
3. **Enable Parallelism** - DuckDB automatically parallelizes queries
4. **Use Columnar Format** - Store data in columnar format when possible

## Files

```
duckdb/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── data/
│   ├── orders.duckdb
│   └── events.parquet
└── queries/
    └── analytics.json
```

