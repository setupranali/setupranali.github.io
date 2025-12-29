# CockroachDB Examples

Connect SetuPranali to CockroachDB distributed SQL.

## Overview

CockroachDB provides:
- PostgreSQL compatibility
- Distributed architecture
- Automatic sharding
- Multi-region capabilities

## Connection Configuration

### CockroachDB Cloud (Serverless)

```yaml
sources:
  cockroach:
    type: cockroachdb
    connection:
      host: your-cluster.cockroachlabs.cloud
      port: 26257
      database: defaultdb
      user: ${COCKROACH_USER}
      password: ${COCKROACH_PASSWORD}
      ssl_mode: verify-full
      ssl_root_cert: /path/to/cc-ca.crt
```

### Self-Hosted

```yaml
sources:
  cockroach:
    type: cockroachdb
    connection:
      host: localhost
      port: 26257
      database: analytics
      user: root
      ssl_mode: disable  # Only for local development
```

### Multi-Region

```yaml
sources:
  cockroach_us:
    type: cockroachdb
    connection:
      host: us-east-1.cockroachlabs.cloud
      # ... config

  cockroach_eu:
    type: cockroachdb
    connection:
      host: eu-west-1.cockroachlabs.cloud
      # ... config
```

## CockroachDB-Specific Features

### Serial/UUID Primary Keys

```yaml
dimensions:
  - name: order_id
    type: string
    sql: order_id::STRING  # UUID to string
```

### Array Operations

```yaml
dimensions:
  - name: tag_count
    type: number
    sql: array_length(tags, 1)
```

### JSON Support

```yaml
dimensions:
  - name: customer_name
    type: string
    sql: metadata->>'customer_name'
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: cockroach
    table: orders
    
    dimensions:
      - name: order_id
        type: string
        sql: order_id::STRING
        primary_key: true
        
      - name: order_date
        type: date
        sql: order_date
        
      - name: region
        type: string
        sql: region
        
      - name: customer_id
        type: string
        sql: customer_id
    
    metrics:
      - name: revenue
        type: sum
        sql: total_amount
        
      - name: order_count
        type: count
        sql: order_id
```

## Docker Setup

```yaml
version: '3.8'
services:
  cockroachdb:
    image: cockroachdb/cockroach:latest
    command: start-single-node --insecure
    ports:
      - "26257:26257"
      - "8080:8080"

  setupranali:
    image: adeygifting/connector:latest
    environment:
      - COCKROACH_HOST=cockroachdb
      - COCKROACH_PORT=26257
      - COCKROACH_USER=root
```

## Best Practices

1. **Use Regions** - Define locality for better performance
2. **Index Wisely** - CockroachDB automatically distributes indexes
3. **Batch Operations** - Use batch inserts for better performance
4. **Monitor via UI** - Use the built-in admin UI at port 8080

