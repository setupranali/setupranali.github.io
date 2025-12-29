# Snowflake Examples

Complete examples for connecting SetuPranali to Snowflake.

## Overview

Snowflake is a popular cloud data warehouse. This example shows:
- Key pair authentication
- Role and warehouse configuration
- Best practices for Snowflake connectivity

## Prerequisites

- Snowflake account
- Snowflake user with appropriate permissions
- Key pair (recommended) or password authentication

## Connection Configuration

### Key Pair Authentication (Recommended)

```yaml
sources:
  snowflake_db:
    type: snowflake
    connection:
      account: your-account.us-east-1
      user: ${SNOWFLAKE_USER}
      private_key_path: /path/to/rsa_key.p8
      private_key_passphrase: ${SNOWFLAKE_KEY_PASSPHRASE}
      database: ANALYTICS
      schema: PUBLIC
      warehouse: COMPUTE_WH
      role: ANALYST_ROLE
```

### Password Authentication

```yaml
sources:
  snowflake_db:
    type: snowflake
    connection:
      account: your-account.us-east-1
      user: ${SNOWFLAKE_USER}
      password: ${SNOWFLAKE_PASSWORD}
      database: ANALYTICS
      schema: PUBLIC
      warehouse: COMPUTE_WH
      role: ANALYST_ROLE
```

### With Query Tags

```yaml
sources:
  snowflake_db:
    type: snowflake
    connection:
      account: your-account
      user: ${SNOWFLAKE_USER}
      password: ${SNOWFLAKE_PASSWORD}
      database: ANALYTICS
      schema: PUBLIC
      warehouse: COMPUTE_WH
      query_tag: setupranali_queries
```

## Generate Key Pair

```bash
# Generate private key
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt

# Generate public key
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

# In Snowflake
ALTER USER your_user SET RSA_PUBLIC_KEY='<public_key_contents>';
```

## Snowflake-Specific Features

### Semi-Structured Data (JSON)

```yaml
dimensions:
  - name: customer_name
    type: string
    sql: raw_data:customer:name::STRING
    
  - name: order_items
    type: number
    sql: ARRAY_SIZE(raw_data:items)
```

### Time Travel

```yaml
datasets:
  orders_yesterday:
    source: snowflake_db
    sql: SELECT * FROM orders AT(OFFSET => -86400)
```

### Clustering Info

```yaml
dimensions:
  - name: cluster_depth
    type: number
    sql: SYSTEM$CLUSTERING_DEPTH('orders', '(order_date)')
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    source: snowflake_db
    table: ANALYTICS.PUBLIC.ORDERS
    
    dimensions:
      - name: order_date
        type: date
        sql: ORDER_DATE
        
      - name: order_month
        type: string
        sql: TO_CHAR(ORDER_DATE, 'YYYY-MM')
        
      - name: customer_segment
        type: string
        sql: CUSTOMER_SEGMENT
        
      - name: region
        type: string
        sql: REGION
    
    metrics:
      - name: revenue
        type: sum
        sql: ORDER_TOTAL
        
      - name: orders
        type: count
        sql: ORDER_ID
        
      - name: aov
        type: avg
        sql: ORDER_TOTAL
```

## Cost Optimization

### Auto-Suspend Warehouse

```sql
ALTER WAREHOUSE COMPUTE_WH SET AUTO_SUSPEND = 60;
```

### Use Smaller Warehouse for SetuPranali

```sql
CREATE WAREHOUSE SETUPRANALI_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

### Resource Monitor

```sql
CREATE RESOURCE MONITOR setupranali_monitor
  WITH CREDIT_QUOTA = 100
  TRIGGERS ON 90 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND;
           
ALTER WAREHOUSE SETUPRANALI_WH SET RESOURCE_MONITOR = setupranali_monitor;
```

## Files in This Example

```
snowflake/
├── README.md
├── catalog.yaml
├── queries/
│   ├── revenue-analysis.json
│   └── customer-segments.json
└── setup/
    ├── create-role.sql
    └── create-warehouse.sql
```

## Troubleshooting

### Connection Timeout

- Check network access (whitelisted IPs)
- Verify account identifier format
- Check warehouse is not suspended

### Permission Denied

```sql
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE analyst_role;
GRANT USAGE ON DATABASE analytics TO ROLE analyst_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ROLE analyst_role;
```

