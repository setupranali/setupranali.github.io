# Defining Datasets

Create semantic datasets that power your BI queries.

---

## Overview

A dataset is a queryable data model with:

- **Source**: Where the data lives
- **Dimensions**: Columns for grouping
- **Metrics**: Aggregated measures
- **RLS**: Security rules

---

## Basic Dataset

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: public.orders
    
    dimensions:
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
      
      - name: order_count
        type: number
        expr: "COUNT(*)"
```

---

## Dataset Properties

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier (snake_case) |
| `source` | Registered data source name |
| `table` | Table or view name |

### Optional Fields

| Field | Description |
|-------|-------------|
| `description` | Human-readable description |
| `sql` | Custom SQL instead of table |
| `dimensions` | List of dimension fields |
| `metrics` | List of metric fields |
| `rls` | Row-level security config |
| `incremental` | Incremental refresh config |

---

## Dimensions

### String Dimension

```yaml
dimensions:
  - name: region
    type: string
    expr: region_name
    description: Geographic region
```

### Date Dimension

```yaml
dimensions:
  - name: order_date
    type: date
    expr: order_date
    description: Date of order
```

### Computed Dimension

```yaml
dimensions:
  - name: year_month
    type: string
    expr: "TO_CHAR(order_date, 'YYYY-MM')"
    description: Year and month
```

### Boolean Dimension

```yaml
dimensions:
  - name: is_premium
    type: boolean
    expr: "customer_tier = 'premium'"
    description: Premium customer flag
```

---

## Metrics

### Sum

```yaml
metrics:
  - name: revenue
    type: number
    expr: "SUM(amount)"
```

### Count

```yaml
metrics:
  - name: orders
    type: number
    expr: "COUNT(*)"
```

### Distinct Count

```yaml
metrics:
  - name: unique_customers
    type: number
    expr: "COUNT(DISTINCT customer_id)"
```

### Average

```yaml
metrics:
  - name: avg_order_value
    type: number
    expr: "AVG(amount)"
```

### Conditional Aggregation

```yaml
metrics:
  - name: premium_revenue
    type: number
    expr: "SUM(CASE WHEN tier = 'premium' THEN amount ELSE 0 END)"
```

### Ratio

```yaml
metrics:
  - name: premium_ratio
    type: number
    expr: |
      SUM(CASE WHEN tier = 'premium' THEN 1 ELSE 0 END)::float / 
      NULLIF(COUNT(*), 0)
```

---

## Custom SQL

Instead of a table, use a custom SQL query:

```yaml
datasets:
  - name: active_orders
    source: postgres-prod
    sql: |
      SELECT 
        o.*,
        c.name as customer_name,
        c.tier as customer_tier
      FROM orders o
      JOIN customers c ON o.customer_id = c.id
      WHERE o.status != 'cancelled'
    
    dimensions:
      - name: customer_name
        type: string
        expr: customer_name
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
```

---

## Multiple Sources

Define datasets from different sources:

```yaml
datasets:
  # PostgreSQL source
  - name: orders
    source: postgres-prod
    table: orders
    
  # Snowflake source
  - name: analytics
    source: snowflake-dw
    table: ANALYTICS.FACT_SALES
    
  # BigQuery source
  - name: events
    source: bigquery-prod
    table: analytics.events
```

---

## Row-Level Security

Restrict data by tenant:

```yaml
datasets:
  - name: orders
    source: postgres-prod
    table: orders
    
    rls:
      tenant_column: tenant_id
```

See [RLS Guide](rls.md) for advanced configuration.

---

## Incremental Refresh

Enable efficient loading:

```yaml
datasets:
  - name: orders
    source: postgres-prod
    table: orders
    
    incremental:
      date_column: order_date
      min_date: "2020-01-01"
```

See [Incremental Refresh Guide](incremental-refresh.md) for details.

---

## Complete Example

```yaml
# catalog.yaml
datasets:
  - name: sales
    description: |
      Sales transactions including revenue, orders, and customer metrics.
      Updated daily via ETL.
    source: snowflake-prod
    table: ANALYTICS.FACT_SALES
    
    dimensions:
      - name: region
        type: string
        expr: region_name
        description: Geographic sales region (North, South, East, West)
      
      - name: product_category
        type: string
        expr: product_category
        description: Product category
      
      - name: order_date
        type: date
        expr: order_date
        description: Date the order was placed
      
      - name: customer_segment
        type: string
        expr: CASE 
          WHEN annual_spend > 100000 THEN 'Enterprise'
          WHEN annual_spend > 10000 THEN 'Mid-Market'
          ELSE 'SMB'
        END
        description: Customer segment based on annual spend
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(sale_amount)"
        description: Total revenue
        format: currency
      
      - name: orders
        type: number
        expr: "COUNT(*)"
        description: Number of orders
      
      - name: avg_order_value
        type: number
        expr: "AVG(sale_amount)"
        description: Average order value
        format: currency
      
      - name: unique_customers
        type: number
        expr: "COUNT(DISTINCT customer_id)"
        description: Unique customers
    
    rls:
      tenant_column: tenant_id
    
    incremental:
      date_column: order_date
      min_date: "2020-01-01"
```

---

## Validation

Test your dataset after defining:

```bash
# Query the dataset
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue"]
  }'
```

---

## Best Practices

### Naming

| Element | Convention |
|---------|------------|
| Dataset | `snake_case`, plural |
| Dimension | `snake_case` |
| Metric | `snake_case`, descriptive |

### Documentation

Always include descriptions:

```yaml
dimensions:
  - name: region
    description: |
      Geographic sales region based on billing address.
      Values: North, South, East, West
```

### Performance

- Use simple expressions when possible
- Avoid complex subqueries in expressions
- Index frequently filtered columns
- Test with realistic data volumes

