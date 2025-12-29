# Multi-Tenant Setup

Configure SetuPranali for multiple customers.

---

## Overview

Multi-tenancy allows you to serve multiple customers from a single deployment:

```
┌─────────────────────────────────────────────────────────┐
│              SetuPranali                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Tenant A │  │ Tenant B │  │ Tenant C │               │
│  │ (Acme)   │  │ (Globex) │  │ (Wayne)  │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │             │             │                      │
│       └─────────────┼─────────────┘                      │
│                     │                                    │
│              Data Isolation                              │
│              (Row-Level Security)                        │
└─────────────────────────────────────────────────────────┘
```

---

## Setup

### Step 1: Data Model

Ensure all tables have a tenant identifier:

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,  -- Required
    customer_id INTEGER,
    amount DECIMAL(10,2),
    order_date DATE
);

CREATE INDEX idx_orders_tenant ON orders(tenant_id);
```

### Step 2: Configure RLS

Add RLS to each dataset:

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: orders
    
    rls:
      tenant_column: tenant_id
    
    dimensions:
      - name: region
        type: string
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
```

### Step 3: Create API Keys

Create a key for each tenant:

```yaml
api_keys:
  # Tenant A
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
  
  # Tenant B
  - key: "pk_globex_xyz789"
    tenant: globex_inc
    role: analyst
  
  # Tenant C
  - key: "pk_wayne_555555"
    tenant: wayne_ent
    role: analyst
  
  # Admin (sees all data)
  - key: "admin-key-xxxxx"
    role: admin
```

### Step 4: Distribute Keys

Provide each customer their unique API key:

| Customer | API Key |
|----------|---------|
| Acme Corp | `pk_acme_abc123` |
| Globex Inc | `pk_globex_xyz789` |
| Wayne Enterprises | `pk_wayne_555555` |

---

## Architecture Patterns

### Shared Database

All tenants share one database with tenant column:

```
┌──────────────────────────────────────────┐
│              Database                     │
│  ┌────────────────────────────────────┐  │
│  │ orders                             │  │
│  │ ─────────────────────────────────  │  │
│  │ tenant_id │ order_id │ amount     │  │
│  │ acme      │ 1001     │ 500.00     │  │
│  │ globex    │ 1002     │ 750.00     │  │
│  │ wayne     │ 1003     │ 250.00     │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

**Pros**: Simple, cost-effective
**Cons**: Noisy neighbor risk

### Schema Per Tenant

Each tenant has their own schema:

```
┌──────────────────────────────────────────┐
│              Database                     │
│  ┌────────────┐  ┌────────────┐          │
│  │ acme.orders│  │globex.orders│         │
│  └────────────┘  └────────────┘          │
└──────────────────────────────────────────┘
```

Configuration:

```yaml
datasets:
  - name: orders_acme
    source: postgres-prod
    table: acme.orders
```

### Database Per Tenant

Each tenant has their own database:

```yaml
# Multiple sources
sources:
  - name: acme-db
    type: postgres
    connection: { database: acme_db }
  
  - name: globex-db
    type: postgres
    connection: { database: globex_db }

datasets:
  - name: orders_acme
    source: acme-db
    table: orders
  
  - name: orders_globex
    source: globex-db
    table: orders
```

---

## Self-Service Portal

### Automated Key Provisioning

Integrate key creation into your app:

```python
import requests

def provision_tenant(tenant_id: str, email: str):
    # Generate unique key
    api_key = f"pk_{tenant_id}_{generate_random()}"
    
    # Register with connector
    # (In production, use secure key management)
    add_to_config(api_key, tenant_id)
    
    # Send to customer
    send_welcome_email(email, api_key)
    
    return api_key
```

### Customer Dashboard

Each customer gets:

- Their API key
- Dataset documentation
- Power BI / Tableau connection instructions
- Usage statistics

---

## Monitoring

### Per-Tenant Metrics

Track usage by tenant:

```json
{
  "tenant": "acme_corp",
  "queries_today": 1523,
  "avg_response_time_ms": 145,
  "cache_hit_rate": 0.82,
  "last_active": "2024-01-15T10:30:00Z"
}
```

### Alerts

Set up alerts for:

- High query volume (abuse detection)
- Error rates by tenant
- Slow queries
- Rate limit hits

---

## Scaling

### Horizontal Scaling

Deploy multiple connector instances:

```yaml
# docker-compose.yml
services:
  connector:
    image: adeygifting/connector:latest
    deploy:
      replicas: 3  # Scale horizontally
```

All instances share:
- Same configuration
- Same Redis (for cache/rate limiting)
- Same database sources

### Tenant Isolation

For strict isolation, deploy per-tenant:

```yaml
# tenant-a-compose.yml
services:
  connector-acme:
    image: adeygifting/connector:latest
    environment:
      - TENANT_ID=acme
    volumes:
      - ./acme-catalog.yaml:/app/catalog.yaml
```

---

## Security Best Practices

### Key Rotation

Regularly rotate API keys:

```python
def rotate_key(tenant_id: str):
    # Generate new key
    new_key = generate_key()
    
    # Add new key (grace period)
    add_key(new_key, tenant_id)
    
    # Notify customer
    notify_key_rotation(tenant_id, new_key)
    
    # After grace period, revoke old key
    schedule_revoke(old_key, delay_days=7)
```

### Audit Logging

Log all tenant activity:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "tenant": "acme_corp",
  "action": "query",
  "dataset": "orders",
  "dimensions": ["region"],
  "ip_address": "192.168.1.100"
}
```

### Rate Limiting Per Tenant

Prevent noisy neighbors:

```yaml
api_keys:
  - key: "pk_acme_abc123"
    tenant: acme_corp
    rate_limit: "100/minute"  # Per-tenant limit
```

---

## Onboarding Checklist

For each new tenant:

- [ ] Create tenant record in your system
- [ ] Add tenant data to shared database
- [ ] Generate API key
- [ ] Configure rate limits
- [ ] Send welcome email with instructions
- [ ] Verify data isolation
- [ ] Monitor first queries
- [ ] Collect feedback

---

## Troubleshooting

### Tenant Seeing Wrong Data

**Symptoms**: Customer sees another tenant's data

**Causes**:
- Wrong tenant in API key
- RLS not configured
- Tenant column mismatch

**Solutions**:
```yaml
# Verify API key configuration
api_keys:
  - key: "pk_acme_abc123"
    tenant: acme_corp  # Must match data

# Verify RLS
rls:
  tenant_column: tenant_id  # Must match column name
```

### Tenant Seeing No Data

**Symptoms**: Empty results

**Causes**:
- Tenant ID doesn't match data
- No data loaded for tenant
- Case sensitivity issue

**Solutions**:
```sql
-- Check what tenants exist in data
SELECT DISTINCT tenant_id FROM orders;

-- Verify case matches
-- 'ACME_CORP' ≠ 'acme_corp'
```

### One Tenant Slow

**Symptoms**: One tenant significantly slower

**Causes**:
- Large data volume
- Missing indexes
- Complex filters

**Solutions**:
```sql
-- Check tenant data size
SELECT tenant_id, COUNT(*) 
FROM orders 
GROUP BY tenant_id;

-- Add composite index
CREATE INDEX idx_tenant_date 
  ON orders(tenant_id, order_date);
```

