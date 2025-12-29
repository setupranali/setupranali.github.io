# Security Model

How SetuPranali protects your data.

---

## Overview

Security is built into every layer:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Transport Security (TLS)                      │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Authentication (API Keys)                     │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Authorization (Row-Level Security)            │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Rate Limiting (Abuse Prevention)              │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Query Guards (Resource Protection)            │
├─────────────────────────────────────────────────────────┤
│  Layer 6: Credential Isolation (Encrypted Storage)      │
└─────────────────────────────────────────────────────────┘
```

---

## Authentication

### API Keys

Every request requires an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: pk_tenant_abc123" \
     http://localhost:8080/v1/query
```

### Key Configuration

```yaml
# config.yaml
api_keys:
  # Admin key for management operations
  - key: "admin-key-xxxxx"
    role: admin
    description: "Platform admin"
  
  # Tenant-specific keys
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
    description: "Acme Corp analysts"
  
  - key: "pk_globex_xyz789"
    tenant: globex_inc
    role: analyst
    description: "Globex Inc analysts"
```

### Key Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access, manage sources, bypass RLS |
| `analyst` | Query datasets, subject to RLS |
| `viewer` | Read-only, limited datasets |

### Key Best Practices

- Use unique keys per tenant
- Rotate keys regularly
- Never share admin keys
- Use environment variables for storage

---

## Authorization (RLS)

### How RLS Works

Row-Level Security automatically filters data based on the API key's tenant.

**Configuration:**

```yaml
datasets:
  - name: orders
    table: orders
    rls:
      tenant_column: tenant_id
```

**Request:**

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \  # tenant: acme_corp
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

**Generated SQL:**

```sql
SELECT SUM(amount) AS revenue
FROM orders
WHERE tenant_id = 'acme_corp'  -- RLS injected automatically
```

### RLS Cannot Be Bypassed

Users cannot:

- Remove the RLS filter
- Query other tenants' data
- Override with custom WHERE clauses

### Multi-Column RLS

```yaml
rls:
  tenant_column: org_id
  additional_filters:
    - column: deleted_at
      condition: IS NULL
```

### Admin Bypass

Admins can see all data:

```yaml
api_keys:
  - key: "admin-key"
    role: admin  # Bypasses RLS
```

---

## Rate Limiting

Protect your data warehouse from abuse.

### Configuration

```bash
# .env
RATE_LIMIT_QUERY=100/minute
RATE_LIMIT_ODATA=50/minute
RATE_LIMIT_SOURCES=10/minute
```

### Per-Key Limits

Each API key has its own rate limit bucket:

```
pk_acme_abc123: 45/100 used
pk_globex_xyz789: 12/100 used
```

### Rate Limit Response

When exceeded:

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 42
}
```

HTTP Status: `429 Too Many Requests`

---

## Query Guards

Prevent runaway queries.

### Configuration

```bash
# .env
MAX_DIMENSIONS=10
MAX_METRICS=20
MAX_ROWS=100000
MAX_FILTER_DEPTH=5
QUERY_TIMEOUT_SECONDS=30
```

### What Gets Blocked

| Guard | Blocked Query |
|-------|---------------|
| `MAX_DIMENSIONS` | Query with 15 dimensions |
| `MAX_ROWS` | Result set > 100K rows |
| `MAX_FILTER_DEPTH` | Deeply nested filters |
| `QUERY_TIMEOUT` | Query running > 30s |

### Error Response

```json
{
  "detail": "Query exceeds maximum dimensions (10)"
}
```

---

## Credential Isolation

### The Problem

Traditional BI:

```
BI User → Database Credentials → Direct Access
```

Every user has database access. Credential sprawl. Security nightmares.

### The Solution

SetuPranali:

```
BI User → API Key → SetuPranali → Database
```

- BI users never see database credentials
- Credentials stored encrypted (Fernet AES-128)
- Single service account with minimal permissions

### Encryption

```python
# Credentials encrypted at rest
from cryptography.fernet import Fernet

fernet = Fernet(secret_key)
encrypted = fernet.encrypt(credentials.encode())
```

### Storage

```sql
-- sources.db (SQLite)
CREATE TABLE sources (
    name TEXT PRIMARY KEY,
    type TEXT,
    connection_encrypted BLOB  -- Fernet encrypted
);
```

---

## Transport Security

### TLS Configuration

Always use HTTPS in production:

```yaml
# docker-compose.yml
services:
  connector:
    environment:
      - SSL_CERT=/certs/server.crt
      - SSL_KEY=/certs/server.key
```

### Reverse Proxy

Recommended: Use nginx or Traefik for TLS termination:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    
    location / {
        proxy_pass http://ubi-connector:8080;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Audit Logging

Track who accessed what.

### Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "event": "query",
  "tenant": "acme_corp",
  "dataset": "orders",
  "dimensions": ["region"],
  "metrics": ["revenue"],
  "execution_ms": 234,
  "cached": false
}
```

### What's Logged

- All query requests
- Authentication failures
- Rate limit hits
- Source operations
- Admin actions

---

## Security Checklist

### Production Deployment

- [ ] Use HTTPS (TLS 1.2+)
- [ ] Generate strong `UBI_SECRET_KEY`
- [ ] Use unique API keys per tenant
- [ ] Configure appropriate rate limits
- [ ] Set query guards
- [ ] Enable audit logging
- [ ] Regular key rotation
- [ ] Minimal database permissions

### API Key Management

- [ ] Never commit keys to git
- [ ] Use environment variables
- [ ] Implement key rotation
- [ ] Revoke unused keys
- [ ] Monitor for abuse

### Network Security

- [ ] Firewall rules configured
- [ ] VPN/private network for database
- [ ] IP allowlisting (if applicable)
- [ ] No public database access

---

## Compliance

### SOC 2

| Control | Implementation |
|---------|----------------|
| Access Control | API key authentication |
| Encryption | TLS + Fernet at rest |
| Logging | Audit trail |
| Monitoring | Health checks, alerts |

### GDPR

| Requirement | Implementation |
|-------------|----------------|
| Data Access Control | RLS by tenant |
| Audit Trail | Request logging |
| Data Minimization | Query only needed fields |
| Right to Erasure | Per-tenant data isolation |

### HIPAA

| Safeguard | Implementation |
|-----------|----------------|
| Access Control | API keys + RLS |
| Encryption | TLS + Fernet |
| Audit Controls | Full request logging |
| Transmission Security | TLS required |

