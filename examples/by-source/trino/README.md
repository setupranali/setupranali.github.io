# Trino/Presto Examples

Connect SetuPranali to Trino (formerly Presto) for federated queries.

## Overview

Trino excels at:
- Federated queries across multiple data sources
- Interactive analytics
- Data lake queries (Hive, Iceberg, Delta)

## Connection Configuration

### Basic Connection

```yaml
sources:
  trino:
    type: trino
    connection:
      host: localhost
      port: 8080
      user: ${TRINO_USER}
      catalog: hive
      schema: default
```

### With Authentication

```yaml
sources:
  trino:
    type: trino
    connection:
      host: trino.example.com
      port: 443
      user: ${TRINO_USER}
      password: ${TRINO_PASSWORD}
      catalog: hive
      schema: analytics
      http_scheme: https
```

### Starburst Enterprise

```yaml
sources:
  starburst:
    type: trino
    connection:
      host: starburst.example.com
      port: 443
      user: ${STARBURST_USER}
      password: ${STARBURST_PASSWORD}
      catalog: lakehouse
      http_scheme: https
```

## Trino-Specific Features

### Cross-Catalog Queries

```yaml
datasets:
  combined_data:
    source: trino
    sql: |
      SELECT 
        h.order_id,
        h.amount,
        p.customer_name
      FROM hive.sales.orders h
      JOIN postgresql.crm.customers p 
        ON h.customer_id = p.id
```

### Array/Map Functions

```yaml
dimensions:
  - name: first_tag
    type: string
    sql: element_at(tags, 1)
    
  - name: tag_count
    type: number
    sql: cardinality(tags)
    
  - name: property_value
    type: string
    sql: element_at(properties, 'key')
```

### Date/Time Functions

```yaml
dimensions:
  - name: order_month
    type: string
    sql: format_datetime(order_date, 'yyyy-MM')
    
  - name: order_quarter
    type: string
    sql: concat('Q', cast(quarter(order_date) as varchar))
```

### Approximate Functions

```yaml
metrics:
  - name: approx_distinct_users
    type: custom
    sql: approx_distinct(user_id)
    
  - name: approx_percentile_95
    type: custom
    sql: approx_percentile(response_time, 0.95)
```

## Sample Dataset

```yaml
datasets:
  events:
    name: "Events"
    source: trino
    table: hive.analytics.events
    
    dimensions:
      - name: event_date
        type: date
        sql: date(event_timestamp)
        
      - name: event_hour
        type: number
        sql: hour(event_timestamp)
        
      - name: event_name
        type: string
        sql: event_name
        
      - name: user_id
        type: string
        sql: user_id
        
      - name: country
        type: string
        sql: country
    
    metrics:
      - name: event_count
        type: count
        sql: event_id
        
      - name: unique_users
        type: count_distinct
        sql: user_id
        
      - name: approx_users
        type: custom
        sql: approx_distinct(user_id)
```

## Docker Setup

```yaml
version: '3.8'
services:
  trino:
    image: trinodb/trino:latest
    ports:
      - "8080:8080"
    volumes:
      - ./catalog:/etc/trino/catalog

  setupranali:
    image: adeygifting/connector:latest
    environment:
      - TRINO_HOST=trino
      - TRINO_PORT=8080
      - TRINO_CATALOG=memory
```

## Best Practices

1. **Use Partitioning** - Filter on partition columns
2. **Approximate Functions** - Use for large datasets
3. **Resource Groups** - Configure for query isolation
4. **Caching** - Enable result caching for repeated queries
5. **Connector Selection** - Choose appropriate connectors for data sources

