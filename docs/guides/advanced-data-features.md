# Advanced Data Features

SetuPranali provides powerful advanced data capabilities that enable sophisticated data modeling and querying across your semantic layer.

## Overview

| Feature | Description | Status |
|---------|-------------|--------|
| **Semantic Joins** | Join across datasets in the semantic layer | ✅ Available |
| **Calculated Metrics** | Define metrics based on other metrics | ✅ Available |
| **Caching Strategies** | Smart cache invalidation and pre-warming | ✅ Available |
| **Query Federation** | Query across multiple data sources | ✅ Available |

---

## Semantic Joins

Define relationships between datasets and query across them seamlessly.

### Configuration

Define joins in your `catalog.yaml`:

```yaml
# catalog.yaml
datasets:
  - id: orders
    name: Orders
    sql: SELECT * FROM orders
    dimensions:
      - name: order_id
        sql: order_id
      - name: customer_id
        sql: customer_id
    metrics:
      - name: revenue
        sql: SUM(amount)

  - id: customers
    name: Customers  
    sql: SELECT * FROM customers
    dimensions:
      - name: customer_id
        sql: customer_id
      - name: customer_name
        sql: name
      - name: country
        sql: country

# Define relationships
joins:
  - left_dataset: orders
    right_dataset: customers
    join_type: left
    left_key: customer_id
    right_key: customer_id
    cardinality: many-to-one
```

### Query with Joins

```bash
# Query orders with customer dimensions
curl -X POST "http://localhost:8080/v1/query" \
  -H "Authorization: Bearer sk_demo_123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "dimensions": ["order_id", "customers.customer_name", "customers.country"],
    "metrics": ["revenue"]
  }'
```

### Join Path Discovery

The system automatically finds the shortest join path between datasets:

```python
from setupranali import SetuPranaliClient

client = SetuPranaliClient("http://localhost:8080", "sk_demo_123")

# Get join path between orders and products
join_path = client.introspect_join_path("orders", "products")
print(join_path)
# {
#   "datasets": ["orders", "order_items", "products"],
#   "joins": [
#     {"left": "orders", "right": "order_items", "on": "order_id"},
#     {"left": "order_items", "right": "products", "on": "product_id"}
#   ]
# }
```

### Join Types

| Type | Description |
|------|-------------|
| `inner` | Only matching rows |
| `left` | All left rows + matching right |
| `right` | All right rows + matching left |
| `full` | All rows from both sides |

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `JOINS_ENABLED` | `true` | Enable semantic joins |
| `MAX_JOIN_DEPTH` | `3` | Maximum join path depth |

---

## Calculated Metrics

Define complex metrics using formulas that reference other metrics.

### Configuration

```yaml
# catalog.yaml
datasets:
  - id: orders
    name: Orders
    sql: SELECT * FROM orders
    metrics:
      # Base metrics
      - name: revenue
        sql: SUM(amount)
        
      - name: order_count
        sql: COUNT(*)
        
      - name: refund_amount
        sql: SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END)

# Calculated metrics
calculated_metrics:
  - name: average_order_value
    expression: "{revenue} / NULLIF({order_count}, 0)"
    description: "Average revenue per order"
    format: currency
    
  - name: net_revenue
    expression: "{revenue} - {refund_amount}"
    description: "Revenue minus refunds"
    format: currency
    
  - name: refund_rate
    expression: "{refund_amount} / NULLIF({revenue}, 0) * 100"
    description: "Percentage of revenue refunded"
    format: percent
    
  # Calculated metric using another calculated metric
  - name: net_aov
    expression: "{net_revenue} / NULLIF({order_count}, 0)"
    description: "Net average order value"
    format: currency
```

### Using Calculated Metrics

```bash
# Query with calculated metrics
curl -X POST "http://localhost:8080/v1/query" \
  -H "Authorization: Bearer sk_demo_123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "dimensions": ["region"],
    "metrics": ["revenue", "order_count", "average_order_value", "net_revenue"]
  }'
```

### Metric Composition

Build complex metrics from simpler ones:

```yaml
calculated_metrics:
  # Growth metrics
  - name: revenue_growth
    expression: "({revenue} - {prev_period_revenue}) / NULLIF({prev_period_revenue}, 0) * 100"
    
  # Ratios
  - name: conversion_rate
    expression: "{purchases} / NULLIF({visits}, 0) * 100"
    
  # Weighted metrics
  - name: weighted_score
    expression: "({quality_score} * 0.4) + ({speed_score} * 0.3) + ({value_score} * 0.3)"
    
  # Conditional metrics
  - name: premium_revenue_share
    expression: "{premium_revenue} / NULLIF({revenue}, 0) * 100"
```

### Validation

The system validates calculated metrics to prevent:
- Circular dependencies
- Missing metric references
- Division by zero (use `NULLIF`)

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CALCULATED_METRICS_ENABLED` | `true` | Enable calculated metrics |
| `MAX_METRIC_DEPTH` | `5` | Maximum nesting depth |

---

## Caching Strategies

Smart caching with multiple invalidation strategies.

### Cache Configuration

```yaml
# Environment configuration
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE_MB=1024
CACHE_PREWARM_ENABLED=true
CACHE_INVALIDATION_ENABLED=true
```

### Invalidation Strategies

#### TTL (Time-To-Live)

```yaml
# Automatic expiration after TTL
caching:
  strategy: ttl
  ttl_seconds: 3600  # 1 hour
```

#### LRU (Least Recently Used)

```yaml
caching:
  strategy: lru
  max_entries: 10000
```

#### Dataset-Based Invalidation

```bash
# Invalidate all cache for a dataset
curl -X POST "http://localhost:8080/v1/cache/invalidate" \
  -H "Authorization: Bearer sk_admin_key" \
  -d '{"dataset": "orders"}'
```

#### Tag-Based Invalidation

```bash
# Invalidate by tag
curl -X POST "http://localhost:8080/v1/cache/invalidate" \
  -H "Authorization: Bearer sk_admin_key" \
  -d '{"tag": "daily_reports"}'
```

### Cache Pre-Warming

Pre-compute frequently accessed queries:

```yaml
# catalog.yaml
cache_prewarm:
  enabled: true
  queries:
    - dataset: orders
      dimensions: [region]
      metrics: [revenue, order_count]
      schedule: "0 6 * * *"  # 6 AM daily
      
    - dataset: orders
      dimensions: [product_category]
      metrics: [revenue]
      filters:
        date: "last_30_days"
      schedule: "0 */4 * * *"  # Every 4 hours
```

### Cache Statistics

```bash
curl "http://localhost:8080/v1/cache/stats" \
  -H "Authorization: Bearer sk_admin_key"
```

Response:
```json
{
  "hits": 15423,
  "misses": 892,
  "hit_rate": 0.945,
  "evictions": 234,
  "size_mb": 256.4,
  "max_size_mb": 1024,
  "entry_count": 1847
}
```

### Write-Through Invalidation

Automatically invalidate cache when source data changes:

```yaml
caching:
  write_through:
    enabled: true
    sources:
      - database: analytics
        tables: [orders, order_items]
        invalidate_datasets: [orders, sales_summary]
```

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CACHE_ENABLED` | `true` | Enable caching |
| `CACHE_TTL_SECONDS` | `3600` | Default TTL |
| `CACHE_MAX_SIZE_MB` | `1024` | Max cache size |
| `CACHE_PREWARM_ENABLED` | `true` | Enable pre-warming |

---

## Query Federation

Query data across multiple sources as a unified semantic layer.

### Source Registration

```yaml
# catalog.yaml
federation:
  enabled: true
  sources:
    - id: warehouse
      name: Data Warehouse
      type: bigquery
      project: my-project
      datasets:
        - orders
        - customers
        
    - id: analytics
      name: Analytics DB
      type: postgres
      host: analytics.example.com
      datasets:
        - page_views
        - sessions
        
    - id: crm
      name: CRM System
      type: mysql
      host: crm.example.com
      datasets:
        - leads
        - opportunities
```

### Cross-Source Queries

Query across multiple sources seamlessly:

```bash
# Join data from warehouse and analytics
curl -X POST "http://localhost:8080/v1/query" \
  -H "Authorization: Bearer sk_demo_123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "dimensions": ["region", "sessions.traffic_source"],
    "metrics": ["revenue", "sessions.session_count"],
    "joins": [
      {
        "dataset": "sessions",
        "on": {"orders.customer_id": "sessions.user_id"}
      }
    ]
  }'
```

### Federation Response

```json
{
  "data": [
    {
      "region": "US",
      "traffic_source": "google",
      "revenue": 125000,
      "session_count": 45000
    }
  ],
  "meta": {
    "federated": true,
    "sources": ["warehouse", "analytics"],
    "timing_ms": 245,
    "sub_timing": {
      "warehouse": 120,
      "analytics": 95
    }
  }
}
```

### Source Priority

Configure source priority for failover:

```yaml
federation:
  sources:
    - id: primary_warehouse
      priority: 1  # Primary
      datasets: [orders]
      
    - id: replica_warehouse
      priority: 2  # Fallback
      datasets: [orders]
```

### Health Monitoring

```bash
curl "http://localhost:8080/v1/federation/health" \
  -H "Authorization: Bearer sk_admin_key"
```

```json
{
  "sources": {
    "warehouse": {
      "healthy": true,
      "last_check": "2024-01-15T10:30:00Z",
      "latency_ms": 45
    },
    "analytics": {
      "healthy": true,
      "last_check": "2024-01-15T10:30:00Z",
      "latency_ms": 32
    }
  }
}
```

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `FEDERATION_ENABLED` | `true` | Enable federation |
| `FEDERATION_TIMEOUT_SECONDS` | `60` | Query timeout |
| `FEDERATION_MAX_SOURCES` | `10` | Max parallel sources |

---

## Complete Example

Here's a comprehensive catalog using all advanced features:

```yaml
# catalog.yaml
version: "1.0"

# Data Sources
sources:
  - id: warehouse
    type: bigquery
    project: analytics-project
    
  - id: postgres
    type: postgres
    host: ${POSTGRES_HOST}

# Federation
federation:
  enabled: true
  sources:
    - id: warehouse
      datasets: [orders, products]
    - id: postgres  
      datasets: [inventory, suppliers]

# Datasets
datasets:
  - id: orders
    name: Orders
    source: warehouse
    sql: SELECT * FROM `analytics.orders`
    dimensions:
      - name: order_id
        sql: order_id
      - name: customer_id
        sql: customer_id
      - name: order_date
        sql: order_date
        type: date
    metrics:
      - name: revenue
        sql: SUM(amount)
      - name: order_count
        sql: COUNT(*)
      - name: refunds
        sql: SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END)

  - id: customers
    name: Customers
    source: warehouse
    sql: SELECT * FROM `analytics.customers`
    dimensions:
      - name: customer_id
        sql: customer_id
      - name: customer_name
        sql: name
      - name: country
        sql: country
        
  - id: inventory
    name: Inventory
    source: postgres
    sql: SELECT * FROM inventory
    dimensions:
      - name: product_id
        sql: product_id
      - name: warehouse_location
        sql: location
    metrics:
      - name: stock_level
        sql: SUM(quantity)

# Semantic Joins
joins:
  - left_dataset: orders
    right_dataset: customers
    join_type: left
    left_key: customer_id
    right_key: customer_id
    cardinality: many-to-one

# Calculated Metrics
calculated_metrics:
  - name: aov
    expression: "{revenue} / NULLIF({order_count}, 0)"
    format: currency
    
  - name: net_revenue
    expression: "{revenue} - {refunds}"
    format: currency
    
  - name: refund_rate
    expression: "{refunds} / NULLIF({revenue}, 0) * 100"
    format: percent

# Caching
caching:
  enabled: true
  ttl_seconds: 1800
  prewarm:
    - dataset: orders
      dimensions: [country]
      metrics: [revenue, order_count, aov]
      schedule: "0 * * * *"
```

---

## Python SDK

```python
from setupranali import SetuPranaliClient

client = SetuPranaliClient(
    base_url="http://localhost:8080",
    api_key="sk_demo_123"
)

# Query with joins
result = client.query(
    dataset="orders",
    dimensions=["order_id", "customers.customer_name"],
    metrics=["revenue"]
)

# Query calculated metrics
result = client.query(
    dataset="orders",
    dimensions=["region"],
    metrics=["revenue", "aov", "net_revenue", "refund_rate"]
)

# Cross-source query
result = client.query(
    dataset="orders",
    dimensions=["product_id", "inventory.warehouse_location"],
    metrics=["revenue", "inventory.stock_level"],
    joins=[{"dataset": "inventory", "on": "product_id"}]
)

# Cache management
client.cache_invalidate(dataset="orders")
stats = client.cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1%}")
```

---

## Best Practices

### Semantic Joins

1. **Define cardinality** - Helps query optimizer
2. **Keep join depth shallow** - Max 3 hops recommended
3. **Index join keys** - Ensure source tables are indexed

### Calculated Metrics

1. **Use NULLIF for divisions** - Prevent division by zero
2. **Keep nesting shallow** - Max 3-4 levels
3. **Document formulas** - Add descriptions

### Caching

1. **Set appropriate TTL** - Balance freshness vs performance
2. **Pre-warm critical queries** - Schedule during low-traffic
3. **Monitor hit rates** - Adjust cache size as needed

### Federation

1. **Minimize cross-source joins** - Push down filters
2. **Set timeouts** - Prevent slow queries blocking
3. **Monitor source health** - Set up alerting

---

## Troubleshooting

### Join Path Not Found

```
Error: No join path found between 'orders' and 'inventory'
```

**Solution**: Define the relationship in `joins` section or increase `MAX_JOIN_DEPTH`.

### Circular Metric Dependency

```
Error: Circular dependency detected in metric 'growth_rate'
```

**Solution**: Review calculated metric definitions and remove circular references.

### Cache Miss Rate High

**Solution**:
- Increase `CACHE_TTL_SECONDS`
- Enable pre-warming for common queries
- Increase `CACHE_MAX_SIZE_MB`

### Federation Timeout

```
Error: Federation query timed out after 60s
```

**Solution**:
- Increase `FEDERATION_TIMEOUT_SECONDS`
- Add filters to reduce data volume
- Check source database performance

