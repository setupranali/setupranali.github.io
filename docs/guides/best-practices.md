# Best Practices

Recommended practices for using SetuPranali effectively.

---

## Dataset Design

### Naming Conventions

**Good**:
```yaml
datasets:
  - name: sales_orders
    dimensions:
      - name: customer_region
      - name: product_category
    metrics:
      - name: total_revenue
      - name: order_count
```

**Avoid**:
```yaml
datasets:
  - name: tbl_ord_2024  # Unclear purpose
    dimensions:
      - name: reg  # Abbreviation
    metrics:
      - name: rev  # Unclear
```

### Dimension Design

- **Use Business Names** - Not column names
- **Add Descriptions** - Self-documenting
- **Group Related Dimensions** - Logical organization
- **Use Consistent Naming** - Across datasets

### Metric Design

- **Clear Aggregations** - SUM, COUNT, AVG are obvious
- **Document Formulas** - Complex calculations need explanation
- **Consistent Formatting** - Currency, percentages, etc.
- **Avoid Duplication** - Reuse metrics across datasets

---

## Security

### API Key Management

**Best Practices**:
- **One Key Per Tenant** - Isolate data access
- **Rotate Keys Regularly** - Quarterly or as needed
- **Use Descriptive Names** - Easy to identify
- **Revoke Unused Keys** - Clean up old keys
- **Never Log Keys** - Security risk

**Example**:
```bash
# Good: Descriptive name
curl -X POST http://localhost:8080/v1/api-keys \
  -d '{"name": "powerbi-prod-tenant-a", "tenant": "tenant-a", "role": "viewer"}'

# Avoid: Generic names
curl -X POST http://localhost:8080/v1/api-keys \
  -d '{"name": "key1", "tenant": "t1", "role": "user"}'
```

### Row-Level Security

**Configuration**:
```yaml
datasets:
  - name: orders
    rls:
      enabled: true
      column: tenant_id  # Must exist in table
      mode: equals
      allowAdminBypass: true  # Admins see all data
```

**Best Practices**:
- **Always Enable RLS** - For multi-tenant data
- **Use Indexed Columns** - For RLS column (performance)
- **Test RLS** - Verify isolation works
- **Document RLS Rules** - For team understanding

---

## Performance

### Query Optimization

**Use Semantic Queries**:
```bash
# Good: Semantic query (optimized)
POST /v1/query
{
  "dataset": "orders",
  "dimensions": [{"name": "city"}],
  "metrics": [{"name": "total_revenue"}],
  "limit": 100
}

# Avoid: Raw SQL when semantic works
POST /v1/sql
{
  "sql": "SELECT city, SUM(revenue) FROM orders GROUP BY city LIMIT 100"
}
```

**Limit Results**:
- Always use `limit` in queries
- Set reasonable defaults (100-1000 rows)
- Use pagination for large datasets

**Use Filters**:
```json
{
  "dataset": "orders",
  "dimensions": [{"name": "city"}],
  "metrics": [{"name": "total_revenue"}],
  "filters": {
    "field": "order_date",
    "op": "gte",
    "value": "2024-01-01"
  },
  "limit": 100
}
```

### Caching

**Enable Caching**:
```bash
export CACHE_ENABLED=true
export REDIS_URL=redis://localhost:6379/0
```

**Cache Strategy**:
- **Short TTL** - For frequently changing data (5-15 minutes)
- **Long TTL** - For stable data (1-24 hours)
- **Cache Invalidation** - On data updates

### Database Optimization

**Indexes**:
- Index RLS columns
- Index filtered columns
- Index join columns
- Index date columns (for incremental refresh)

**Query Patterns**:
- Avoid `SELECT *` - Specify columns
- Use appropriate data types
- Normalize data appropriately
- Use materialized views for complex queries

---

## Catalog Management

### Organization

**Structure**:
```yaml
# catalog.yaml
datasets:
  # Sales domain
  - name: sales_orders
  - name: sales_customers
  
  # Marketing domain
  - name: marketing_campaigns
  - name: marketing_leads
  
  # Finance domain
  - name: finance_transactions
```

**Version Control**:
- Store `catalog.yaml` in Git
- Use branches for changes
- Review changes before merging
- Document dataset changes

### Documentation

**Add Descriptions**:
```yaml
datasets:
  - name: orders
    description: "Order-level transaction data with revenue metrics"
    dimensions:
      - name: city
        description: "City where order was placed"
    metrics:
      - name: total_revenue
        description: "Sum of all order amounts"
```

---

## Multi-Tenant Setup

### Tenant Isolation

**Configuration**:
```yaml
# Each tenant gets separate API key
api_keys:
  - key: "pk_tenant_a_..."
    tenant: tenant_a
    role: viewer
  - key: "pk_tenant_b_..."
    tenant: tenant_b
    role: viewer
```

**Best Practices**:
- **Separate Keys** - One per tenant
- **Test Isolation** - Verify RLS works
- **Monitor Usage** - Track per-tenant queries
- **Document Tenants** - Keep tenant registry

### Data Model

**Design**:
```sql
-- Include tenant_id in all tables
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,  -- RLS column
    order_date DATE,
    revenue DECIMAL,
    ...
);

-- Index for performance
CREATE INDEX idx_orders_tenant_id ON orders(tenant_id);
```

---

## Incremental Refresh

### Configuration

```yaml
datasets:
  - name: orders
    incremental:
      enabled: true
      column: order_date
      type: date
      mode: append
      maxWindowDays: 90
```

**Best Practices**:
- **Use Date Columns** - For incremental refresh
- **Set Max Window** - Prevent large scans
- **Index Date Column** - For performance
- **Test Incremental** - Verify it works

---

## Error Handling

### Client-Side

**Retry Logic**:
```python
import requests
from time import sleep

def query_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limited
                sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            sleep(2 ** attempt)
    return None
```

**Error Messages**:
- Check `error` field in response
- Log error details
- Provide user-friendly messages
- Handle rate limits gracefully

---

## Monitoring

### Health Checks

**Regular Monitoring**:
```bash
# Health check endpoint
curl http://localhost:8080/v1/health

# Check specific components
curl http://localhost:8080/v1/health | jq '.cache'
```

### Metrics to Track

- **Query Success Rate** - Should be > 99%
- **Average Response Time** - Should be < 1s
- **Cache Hit Rate** - Should be > 50%
- **Error Rate** - Should be < 1%

### Logging

**Structured Logging**:
- Log all queries with metadata
- Include request IDs for tracing
- Log errors with context
- Monitor for patterns

---

## Deployment

### Production Checklist

- [ ] Redis configured and running
- [ ] API keys created and secured
- [ ] RLS enabled for multi-tenant
- [ ] Rate limiting configured
- [ ] Caching enabled
- [ ] Monitoring set up
- [ ] Logs configured
- [ ] Backups scheduled
- [ ] SSL/TLS enabled
- [ ] Firewall configured

### Environment Variables

**Required**:
```bash
UBI_SECRET_KEY=your-encryption-key
```

**Recommended**:
```bash
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
```

---

## Testing

### Integration Tests

```python
# Test query execution
def test_query_execution():
    response = requests.post(
        "http://localhost:8080/v1/query",
        headers={"X-API-Key": test_key},
        json={
            "dataset": "orders",
            "dimensions": [{"name": "city"}],
            "limit": 1
        }
    )
    assert response.status_code == 200
    assert "rows" in response.json()
```

### Load Testing

- Test with realistic query patterns
- Verify rate limiting works
- Check cache performance
- Monitor database load

---

## Next Steps

- [Troubleshooting Guide](troubleshooting.md)
- [Production Checklist](../deployment/production-checklist.md)
- [Configuration Guide](../deployment/configuration.md)

