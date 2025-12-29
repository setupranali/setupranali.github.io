# Semantic Layer

The semantic layer defines how your data is exposed to BI tools.

---

## Overview

A semantic layer provides:

- **Abstraction**: Hide SQL complexity from users
- **Consistency**: Same metric = same result everywhere
- **Governance**: Control what users can access
- **Documentation**: Self-describing data

---

## Catalog Structure

The semantic layer is defined in `catalog.yaml`:

```yaml
datasets:
  - name: sales
    description: Sales transactions
    source: snowflake-prod
    table: fact_sales
    
    dimensions:
      - name: region
        type: string
        expr: region_name
        description: Sales region
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
        description: Total revenue
    
    rls:
      tenant_column: tenant_id
```

---

## Datasets

A dataset represents a queryable entity—typically a table or view.

### Basic Dataset

```yaml
datasets:
  - name: orders
    source: postgres-prod
    table: public.orders
```

### With Schema

```yaml
datasets:
  - name: orders
    source: snowflake-prod
    table: ANALYTICS.ORDERS  # database.schema.table
```

### With Custom SQL

```yaml
datasets:
  - name: active_orders
    source: postgres-prod
    sql: |
      SELECT * FROM orders 
      WHERE status != 'cancelled'
```

---

## Dimensions

Dimensions are the "by" in "revenue by region". They're used for grouping.

### String Dimension

```yaml
dimensions:
  - name: region
    type: string
    expr: region_name
    description: Geographic sales region
```

### Date Dimension

```yaml
dimensions:
  - name: order_date
    type: date
    expr: order_date
    description: Date the order was placed
```

### Computed Dimension

```yaml
dimensions:
  - name: order_month
    type: string
    expr: "DATE_TRUNC('month', order_date)"
    description: Month of order
```

### Dimension with Hierarchy

```yaml
dimensions:
  - name: region
    type: string
    expr: region
    hierarchy:
      - country
      - state
      - city
```

---

## Metrics

Metrics are aggregated values—the "what" you're measuring.

### Sum Metric

```yaml
metrics:
  - name: revenue
    type: number
    expr: "SUM(amount)"
    description: Total revenue
    format: currency
```

### Count Metric

```yaml
metrics:
  - name: order_count
    type: number
    expr: "COUNT(*)"
    description: Number of orders
```

### Average Metric

```yaml
metrics:
  - name: avg_order_value
    type: number
    expr: "AVG(amount)"
    description: Average order value
    format: currency
```

### Distinct Count

```yaml
metrics:
  - name: unique_customers
    type: number
    expr: "COUNT(DISTINCT customer_id)"
    description: Unique customers
```

### Ratio Metric

```yaml
metrics:
  - name: conversion_rate
    type: number
    expr: "SUM(CASE WHEN converted THEN 1 ELSE 0 END)::float / COUNT(*)"
    description: Conversion rate
    format: percent
```

---

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text values | Region, Product |
| `number` | Numeric values | Revenue, Count |
| `date` | Date values | Order Date |
| `datetime` | Date + time | Created At |
| `boolean` | True/false | Is Active |

---

## Expressions

Expressions define how fields map to SQL.

### Simple Column

```yaml
expr: region_name
# → SELECT region_name
```

### Computed

```yaml
expr: "UPPER(region_name)"
# → SELECT UPPER(region_name)
```

### Aggregation

```yaml
expr: "SUM(amount)"
# → SELECT SUM(amount)
```

### Conditional

```yaml
expr: "SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END)"
```

### Database-Specific

```yaml
# Snowflake
expr: "DATE_TRUNC('month', order_date)"

# PostgreSQL
expr: "date_trunc('month', order_date)"

# BigQuery
expr: "DATE_TRUNC(order_date, MONTH)"
```

---

## Row-Level Security

Control which rows each tenant can see.

### Basic RLS

```yaml
rls:
  tenant_column: tenant_id
```

When a request comes with tenant `acme_corp`, the query becomes:

```sql
SELECT ... FROM orders WHERE tenant_id = 'acme_corp'
```

### RLS with Custom Expression

```yaml
rls:
  tenant_column: organization_id
  expression: "organization_id = '{tenant}'"
```

### RLS with Role-Based Access

```yaml
rls:
  tenant_column: tenant_id
  admin_bypass: true  # Admin role sees all
```

---

## Incremental Refresh

Enable efficient loading for BI tools.

```yaml
incremental:
  date_column: order_date
  min_date: "2020-01-01"
```

This allows Power BI to request:

```
/odata/orders?$filter=order_date ge 2024-01-01 and order_date lt 2024-02-01
```

---

## Relationships

Define how datasets relate to each other.

```yaml
datasets:
  - name: orders
    table: orders
    relationships:
      - name: customer
        to: customers
        type: many-to-one
        join:
          - orders.customer_id = customers.id
  
  - name: customers
    table: customers
```

---

## Complete Example

```yaml
# catalog.yaml

datasets:
  # Sales dataset
  - name: sales
    description: Sales transactions with revenue and orders
    source: snowflake-prod
    table: ANALYTICS.FACT_SALES
    
    dimensions:
      - name: region
        type: string
        expr: region_name
        description: Geographic sales region
      
      - name: product
        type: string
        expr: product_category
        description: Product category
      
      - name: order_date
        type: date
        expr: order_date
        description: Date of order
      
      - name: customer_segment
        type: string
        expr: customer_segment
        description: Customer segment (Enterprise/SMB/Consumer)
    
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

## Best Practices

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Dataset | snake_case, plural | `orders`, `sales` |
| Dimension | snake_case | `region`, `order_date` |
| Metric | snake_case | `revenue`, `order_count` |

### Documentation

Always include descriptions:

```yaml
dimensions:
  - name: region
    description: |
      Geographic sales region based on customer billing address.
      Values: North, South, East, West
```

### Performance

- Keep expressions simple
- Use database functions
- Avoid cross-joins
- Index frequently filtered columns

