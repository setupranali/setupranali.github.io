# Multi-Tenant Analytics Example

Implement secure multi-tenant analytics with SetuPranali.

## Overview

This example demonstrates:
- Row-Level Security (RLS) per tenant
- Tenant-specific API keys
- Data isolation
- White-label support

## Architecture

```
                    ┌─────────────────┐
                    │   SetuPranali   │
                    │   (Single)      │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐
    │  Tenant A   │   │  Tenant B   │   │  Tenant C   │
    │  API Key    │   │  API Key    │   │  API Key    │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                    ┌────────┴────────┐
                    │   Shared DB     │
                    │  (tenant_id)    │
                    └─────────────────┘
```

## Quick Start

```bash
docker-compose up -d

# Query as Tenant A
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer tenant_a_key" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'

# Query as Tenant B (sees different data!)
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer tenant_b_key" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

## Catalog Configuration

```yaml
sources:
  shared_db:
    type: postgres
    connection:
      host: ${DB_HOST}
      database: multi_tenant
      user: ${DB_USER}
      password: ${DB_PASSWORD}

# API Keys with tenant mapping
api_keys:
  # Admin key - sees all data (no tenant_id)
  admin_key:
    name: "Admin"
    rate_limit: 10000
  
  # Tenant-specific keys
  tenant_a_key:
    name: "Tenant A"
    tenant_id: "tenant_a"
    rate_limit: 1000
    
  tenant_b_key:
    name: "Tenant B"
    tenant_id: "tenant_b"
    rate_limit: 1000
    
  tenant_c_key:
    name: "Tenant C"
    tenant_id: "tenant_c"
    rate_limit: 1000

# Datasets
datasets:
  orders:
    name: "Orders"
    source: shared_db
    table: orders
    
    dimensions:
      - name: order_id
        type: string
        sql: order_id
        
      - name: order_date
        type: date
        sql: order_date
        
      - name: customer_id
        type: string
        sql: customer_id
        
      - name: status
        type: string
        sql: status
        
      # tenant_id is hidden from results but used for RLS
      - name: tenant_id
        type: string
        sql: tenant_id
        hidden: true
    
    metrics:
      - name: revenue
        type: sum
        sql: amount
        
      - name: order_count
        type: count
        sql: order_id

  customers:
    name: "Customers"
    source: shared_db
    table: customers
    
    dimensions:
      - name: customer_id
        type: string
        sql: customer_id
        
      - name: name
        type: string
        sql: name
        
      - name: tenant_id
        type: string
        sql: tenant_id
        hidden: true
    
    metrics:
      - name: customer_count
        type: count
        sql: customer_id

# Row-Level Security
rls:
  orders:
    field: tenant_id
    operator: "="
    
  customers:
    field: tenant_id
    operator: "="
```

## Database Schema

```sql
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,  -- RLS field
    order_date DATE NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    status VARCHAR(50),
    amount DECIMAL(12,2)
);

CREATE INDEX idx_orders_tenant ON orders(tenant_id);

CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,  -- RLS field
    name VARCHAR(255),
    email VARCHAR(255)
);

CREATE INDEX idx_customers_tenant ON customers(tenant_id);
```

## How RLS Works

1. **API Key Lookup**: When a request comes in, SetuPranali looks up the API key
2. **Tenant ID Extraction**: The `tenant_id` is extracted from the API key config
3. **Query Modification**: All queries are automatically modified to include:
   ```sql
   WHERE tenant_id = 'extracted_tenant_id'
   ```
4. **Data Isolation**: Each tenant only sees their own data

### Example

Request:
```json
{
  "dataset": "orders",
  "metrics": ["revenue"]
}
```

With `tenant_a_key`, the actual query becomes:
```sql
SELECT SUM(amount) as revenue
FROM orders
WHERE tenant_id = 'tenant_a'
```

With `tenant_b_key`, it becomes:
```sql
SELECT SUM(amount) as revenue
FROM orders
WHERE tenant_id = 'tenant_b'
```

## Advanced: Hierarchical Tenants

For parent-child tenant relationships:

```yaml
api_keys:
  parent_org_key:
    name: "Parent Organization"
    tenant_id: ["tenant_a", "tenant_b"]  # Sees multiple tenants
    
  child_a_key:
    name: "Child A"
    tenant_id: "tenant_a"  # Only sees tenant_a
```

```yaml
rls:
  orders:
    field: tenant_id
    operator: "IN"  # Use IN for array of tenant_ids
```

## White-Label Support

Configure branding per tenant:

```yaml
branding:
  tenant_a:
    logo: "https://tenant-a.com/logo.png"
    primary_color: "#FF5722"
    company_name: "Tenant A Analytics"
    
  tenant_b:
    logo: "https://tenant-b.com/logo.png"
    primary_color: "#2196F3"
    company_name: "Tenant B Insights"
```

## Testing Multi-Tenancy

### Verify Isolation

```bash
# Tenant A - should see Tenant A data only
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer tenant_a_key" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "dimensions": ["tenant_id"], "metrics": ["revenue"]}'

# Response should only show tenant_a
# {"data": [{"tenant_id": "tenant_a", "revenue": 5000}]}

# Tenant B - should see Tenant B data only
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer tenant_b_key" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "dimensions": ["tenant_id"], "metrics": ["revenue"]}'

# Response should only show tenant_b
# {"data": [{"tenant_id": "tenant_b", "revenue": 7500}]}
```

### Admin Access

```bash
# Admin key - sees all tenants
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer admin_key" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "dimensions": ["tenant_id"], "metrics": ["revenue"]}'

# Response shows all tenants
# {"data": [
#   {"tenant_id": "tenant_a", "revenue": 5000},
#   {"tenant_id": "tenant_b", "revenue": 7500},
#   {"tenant_id": "tenant_c", "revenue": 3000}
# ]}
```

## BI Tool Integration

### Power BI / Tableau

1. Create separate data sources per tenant
2. Each data source uses tenant-specific API key
3. Users connect to their tenant's data source

### Embedded Analytics

```javascript
// Generate tenant-specific embed URL
const embedUrl = `https://bi-tool.com/embed/dashboard?
  dataSource=https://setupranali.io/odata/orders&
  apiKey=${tenantApiKey}`;
```

## Files

```
multi-tenant/
├── README.md
├── docker-compose.yml
├── catalog.yaml
├── init-db/
│   ├── schema.sql
│   └── multi-tenant-data.sql
├── test-isolation.sh
└── screenshots/
    └── tenant-isolation.png
```

## Best Practices

1. **Always use tenant_id index** - Performance critical
2. **Hide tenant_id from results** - Use `hidden: true`
3. **Test isolation thoroughly** - Verify before production
4. **Use meaningful tenant_ids** - Avoid UUIDs if possible
5. **Monitor per-tenant usage** - Rate limiting helps
6. **Audit access** - Log which tenant accessed what

