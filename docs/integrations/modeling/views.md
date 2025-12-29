# SQL Views

Use existing database views with SetuPranali.

---

## Overview

Point SetuPranali at database views:

```
Database Views → SetuPranali → BI Tools
```

Zero modeling layer required—just reference views directly.

---

## Setup

### 1. Create Views (if needed)

```sql
CREATE VIEW analytics.v_orders AS
SELECT
    o.order_id,
    o.customer_id,
    c.region,
    o.order_date,
    o.amount,
    o.tenant_id
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.status != 'cancelled';
```

### 2. Reference in Catalog

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: analytics.v_orders  # Reference view
    
    dimensions:
      - name: region
        type: string
        expr: region
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
    
    rls:
      tenant_column: tenant_id
```

---

## Example Views

### Aggregated View

```sql
CREATE VIEW analytics.v_daily_sales AS
SELECT
    order_date,
    region,
    product_category,
    COUNT(*) as order_count,
    SUM(amount) as revenue,
    tenant_id
FROM orders
GROUP BY order_date, region, product_category, tenant_id;
```

```yaml
datasets:
  - name: daily_sales
    table: analytics.v_daily_sales
    
    dimensions:
      - name: order_date
        type: date
      - name: region
        type: string
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(revenue)"  # Pre-aggregated
```

### Joined View

```sql
CREATE VIEW analytics.v_customer_orders AS
SELECT
    o.*,
    c.name as customer_name,
    c.segment as customer_segment
FROM orders o
JOIN customers c ON o.customer_id = c.id;
```

### Filtered View

```sql
CREATE VIEW analytics.v_active_orders AS
SELECT *
FROM orders
WHERE status = 'active'
  AND created_at > CURRENT_DATE - INTERVAL '90 days';
```

---

## Views vs Tables

### When to Use Views

- Simple transformations
- Real-time requirements
- Joins without complexity
- Small-medium data volumes

### When to Use Tables

- Complex transformations
- Large datasets
- Heavy aggregations
- Performance-critical queries

### Materialized Views

Best of both worlds (if supported):

```sql
-- PostgreSQL
CREATE MATERIALIZED VIEW analytics.mv_orders AS
SELECT ...;

-- Refresh periodically
REFRESH MATERIALIZED VIEW analytics.mv_orders;
```

---

## Best Practices

### 1. Include Tenant Column

Always include tenant column for RLS:

```sql
CREATE VIEW analytics.v_orders AS
SELECT
    ...,
    tenant_id  -- Required for RLS
FROM orders;
```

### 2. Pre-Aggregate When Possible

For better performance:

```sql
-- Pre-aggregate in view
CREATE VIEW analytics.v_sales_summary AS
SELECT
    date_trunc('day', order_date) as order_day,
    region,
    SUM(amount) as daily_revenue,
    COUNT(*) as daily_orders,
    tenant_id
FROM orders
GROUP BY 1, 2, tenant_id;
```

### 3. Index Underlying Tables

```sql
CREATE INDEX idx_orders_tenant_date 
ON orders(tenant_id, order_date);
```

### 4. Document Views

```sql
COMMENT ON VIEW analytics.v_orders IS 
'Active orders with customer information. Used by BI connector.';
```

---

## Multi-Database Views

### PostgreSQL

```sql
-- Foreign data wrapper for cross-database
CREATE EXTENSION postgres_fdw;

CREATE SERVER remote_server
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (host 'remote.example.com', dbname 'analytics');

CREATE FOREIGN TABLE remote_orders (...)
SERVER remote_server;

CREATE VIEW v_combined_orders AS
SELECT * FROM local_orders
UNION ALL
SELECT * FROM remote_orders;
```

### Snowflake

```sql
-- Cross-database view
CREATE VIEW analytics.v_combined AS
SELECT * FROM db1.schema.orders
UNION ALL
SELECT * FROM db2.schema.orders;
```

---

## Troubleshooting

### View Not Found

```
Relation "analytics.v_orders" does not exist
```

**Solutions**:
1. Verify view exists: `\dv analytics.*`
2. Check schema is correct
3. Verify user has access

### Slow Queries

**Symptoms**: Queries on views are slow

**Solutions**:
1. Check query plan: `EXPLAIN ANALYZE SELECT ...`
2. Add indexes to underlying tables
3. Consider materialized view
4. Pre-aggregate data

### Missing Data

**Symptoms**: View returns fewer rows than expected

**Solutions**:
1. Check view definition for filters
2. Verify JOIN conditions
3. Check for NULL handling

