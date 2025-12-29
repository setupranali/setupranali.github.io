# Databricks Examples

Connect SetuPranali to Databricks Lakehouse.

## Overview

- Unity Catalog integration
- Delta Lake support
- SQL Warehouse connection

## Connection Configuration

### Using SQL Warehouse

```yaml
sources:
  databricks:
    type: databricks
    connection:
      host: your-workspace.cloud.databricks.com
      http_path: /sql/1.0/warehouses/abc123
      access_token: ${DATABRICKS_TOKEN}
      catalog: main
      schema: analytics
```

### With Unity Catalog

```yaml
sources:
  databricks:
    type: databricks
    connection:
      host: your-workspace.cloud.databricks.com
      http_path: /sql/1.0/warehouses/abc123
      access_token: ${DATABRICKS_TOKEN}
      catalog: production
      schema: gold
```

## Databricks-Specific Features

### Delta Lake Time Travel

```yaml
datasets:
  orders_yesterday:
    source: databricks
    sql: SELECT * FROM orders VERSION AS OF 1
```

### Query Delta Table Properties

```yaml
dimensions:
  - name: partition_date
    type: date
    sql: _metadata.file_path
```

## Sample Dataset

```yaml
datasets:
  orders:
    name: "Orders"
    description: "Orders from Delta Lake"
    source: databricks
    table: main.analytics.orders
    
    dimensions:
      - name: order_id
        type: string
        sql: order_id
        
      - name: order_date
        type: date
        sql: order_date
        
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
```

## Authentication

### Personal Access Token

1. Go to Databricks workspace → User Settings → Access Tokens
2. Generate new token
3. Set `DATABRICKS_TOKEN` environment variable

### Service Principal (Production)

```yaml
connection:
  host: your-workspace.cloud.databricks.com
  http_path: /sql/1.0/warehouses/abc123
  client_id: ${DATABRICKS_CLIENT_ID}
  client_secret: ${DATABRICKS_CLIENT_SECRET}
```

## Best Practices

1. **Use SQL Warehouses** - Not clusters, for better cost control
2. **Enable Auto-Stop** - Set SQL warehouse to auto-stop when idle
3. **Use Serverless** - Consider serverless SQL warehouses
4. **Filter Early** - Use partition pruning with Delta Lake

