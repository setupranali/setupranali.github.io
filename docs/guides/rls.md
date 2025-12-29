# Row-Level Security

Implement automatic per-tenant data isolation.

---

## Overview

Row-Level Security (RLS) ensures each tenant only sees their own data:

```
Tenant A queries "orders" → Sees only Tenant A's orders
Tenant B queries "orders" → Sees only Tenant B's orders
Admin queries "orders"    → Sees all orders
```

This happens automatically—no code changes in BI tools.

---

## How It Works

### Configuration

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: orders
    
    rls:
      tenant_column: tenant_id
```

### API Key Setup

```yaml
api_keys:
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
```

### Query Transformation

When `pk_acme_abc123` queries `orders`:

```sql
-- Original query
SELECT region, SUM(amount) 
FROM orders 
GROUP BY region

-- With RLS applied
SELECT region, SUM(amount) 
FROM orders 
WHERE tenant_id = 'acme_corp'  -- Injected
GROUP BY region
```

---

## Configuration Options

### Basic RLS

Single tenant column:

```yaml
rls:
  tenant_column: tenant_id
```

### Custom Column Name

If your tenant column has a different name:

```yaml
rls:
  tenant_column: organization_id
```

### Multiple Conditions

Add extra filters:

```yaml
rls:
  tenant_column: tenant_id
  additional_filters:
    - column: deleted_at
      condition: IS NULL
    - column: is_active
      condition: "= true"
```

Generated SQL:

```sql
WHERE tenant_id = 'acme_corp'
  AND deleted_at IS NULL
  AND is_active = true
```

### Admin Bypass

Allow admins to see all data:

```yaml
api_keys:
  - key: "admin-key"
    role: admin  # Bypasses RLS
```

---

## Multi-Tenant Patterns

### Pattern 1: Single Tenant Column

```yaml
# Most common pattern
rls:
  tenant_column: tenant_id
```

Table structure:

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,  -- RLS column
    amount DECIMAL,
    ...
);
```

### Pattern 2: Organization Hierarchy

```yaml
rls:
  tenant_column: org_id
  # API key tenant maps to org_id
```

### Pattern 3: Composite Key

For complex scenarios:

```yaml
rls:
  expression: "org_id = '{tenant}' AND region = '{region}'"
```

!!! note "Advanced Usage"
    Custom expressions require additional context in the API key configuration.

---

## Testing RLS

### Verify Tenant Isolation

1. Create test data:

```sql
INSERT INTO orders (tenant_id, region, amount) VALUES
  ('acme_corp', 'North', 100),
  ('acme_corp', 'South', 200),
  ('globex_inc', 'North', 300),
  ('globex_inc', 'East', 400);
```

2. Query as Tenant A:

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \
  -d '{"dataset": "orders", "dimensions": ["region"], "metrics": ["revenue"]}'
```

Expected (only Acme data):

```json
{
  "rows": [
    ["North", 100],
    ["South", 200]
  ]
}
```

3. Query as Tenant B:

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_globex_xyz789" \
  -d '{"dataset": "orders", "dimensions": ["region"], "metrics": ["revenue"]}'
```

Expected (only Globex data):

```json
{
  "rows": [
    ["North", 300],
    ["East", 400]
  ]
}
```

### Verify Cannot Bypass

Users cannot override RLS:

```bash
# Attempting to add tenant filter manually - still restricted
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \
  -d '{
    "dataset": "orders",
    "metrics": ["revenue"],
    "filters": [{"field": "tenant_id", "op": "=", "value": "globex_inc"}]
  }'
```

Result: Still only sees Acme data (RLS is additive).

---

## Security Considerations

### RLS is Server-Side

- Applied by the connector, not the database
- Users cannot bypass via SQL injection
- Works identically across all BI tools

### Tenant ID Validation

- Tenant ID comes from API key configuration
- Users cannot specify their own tenant
- Admin verification of API key → tenant mapping

### Audit Trail

All queries are logged with tenant context:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "api_key": "pk_acme_***",
  "tenant": "acme_corp",
  "dataset": "orders",
  "rls_applied": true
}
```

---

## Best Practices

### Consistent Tenant Columns

Use the same tenant column across all tables:

```sql
-- All tables have tenant_id
CREATE TABLE orders (tenant_id VARCHAR, ...);
CREATE TABLE customers (tenant_id VARCHAR, ...);
CREATE TABLE products (tenant_id VARCHAR, ...);
```

### Index Tenant Columns

```sql
CREATE INDEX idx_orders_tenant ON orders(tenant_id);
```

### Validate Data Integrity

Ensure no data leaks via foreign keys:

```sql
-- Orders should only reference customers in same tenant
CREATE TABLE orders (
    tenant_id VARCHAR NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    CONSTRAINT fk_customer_tenant 
      CHECK (customer_tenant_id = tenant_id)
);
```

### Test Isolation Regularly

```bash
# Automated test
for tenant in acme globex wayne; do
  result=$(curl -s -X POST http://localhost:8080/v1/query \
    -H "X-API-Key: pk_${tenant}_key" \
    -d '{"dataset": "orders", "metrics": ["revenue"]}')
  
  # Verify response only contains expected tenant
  echo "Tenant: $tenant, Result: $result"
done
```

---

## Troubleshooting

### No Data Returned

**Symptoms**: Query returns empty results

**Causes**:
- Tenant ID doesn't match data
- RLS column name mismatch
- No data for tenant

**Solutions**:
```sql
-- Check what tenants exist
SELECT DISTINCT tenant_id FROM orders;

-- Verify API key configuration
-- Check catalog.yaml rls.tenant_column
```

### Wrong Data Returned

**Symptoms**: Seeing other tenant's data

**Causes**:
- RLS not configured
- Using admin key
- Tenant column misconfigured

**Solutions**:
```yaml
# Verify RLS is configured
datasets:
  - name: orders
    rls:
      tenant_column: tenant_id  # Must match actual column
```

### Performance Impact

**Symptoms**: Slow queries with RLS

**Solutions**:
```sql
-- Add index on tenant column
CREATE INDEX idx_orders_tenant ON orders(tenant_id);

-- Check query plan
EXPLAIN ANALYZE SELECT ... FROM orders WHERE tenant_id = 'acme';
```

