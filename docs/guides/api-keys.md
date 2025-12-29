# API Keys

Create and manage API keys for authentication.

---

## Overview

API keys control who can access your data:

```
Request with API Key → Authentication → Authorization (RLS) → Data
```

---

## Key Types

| Type | Purpose | RLS |
|------|---------|-----|
| Admin | Platform management | Bypassed |
| Analyst | Data queries | Applied |
| Viewer | Read-only access | Applied |

---

## Configuration

### Static Configuration

Define keys in configuration:

```yaml
# config.yaml or environment
api_keys:
  # Admin key
  - key: "admin-key-xxxxx"
    role: admin
    description: "Platform administrator"
  
  # Tenant key
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
    description: "Acme Corp analysts"
```

### Environment Variables

For single-tenant or simple setups:

```bash
# .env
API_KEY_ADMIN=admin-key-xxxxx
API_KEY_DEFAULT=default-key-yyyyy
```

---

## Creating Keys

### Key Format

Recommended format:

```
{prefix}_{tenant}_{random}
```

Examples:
- `pk_acme_abc123` (production key for Acme)
- `sk_test_xyz789` (staging key for testing)
- `admin_ops_000111` (admin operations key)

### Generating Keys

```python
import secrets

def generate_api_key(tenant: str, prefix: str = "pk") -> str:
    random_part = secrets.token_hex(12)
    return f"{prefix}_{tenant}_{random_part}"

# Example
key = generate_api_key("acme")
# pk_acme_7a8b9c0d1e2f3a4b5c6d7e8f
```

### Key Properties

| Property | Description | Required |
|----------|-------------|----------|
| `key` | The API key string | Yes |
| `role` | Permission level | Yes |
| `tenant` | Tenant identifier for RLS | For non-admin |
| `description` | Human-readable note | No |
| `rate_limit` | Custom rate limit | No |
| `expires_at` | Expiration date | No |

---

## Using Keys

### HTTP Header

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "metrics": ["revenue"]}'
```

### Power BI

1. Go to **Advanced** options
2. Add HTTP header:
   - Name: `X-API-Key`
   - Value: `pk_acme_abc123`

### Tableau

1. Open Web Data Connector
2. Enter API key in authentication field

---

## Key Rotation

### Why Rotate?

- Employee leaves the organization
- Key may have been exposed
- Regular security practice
- Compliance requirements

### Rotation Process

1. **Generate new key**

```python
new_key = generate_api_key("acme")
```

2. **Add new key (grace period)**

```yaml
api_keys:
  # Old key (still valid)
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
  
  # New key (active)
  - key: "pk_acme_xyz789"
    tenant: acme_corp
    role: analyst
```

3. **Notify users**

```
Subject: API Key Rotation - Action Required

Your API key will be rotated. Please update your connections.

New key: pk_acme_xyz789
Deadline: 2024-02-01
```

4. **Revoke old key**

```yaml
api_keys:
  # Only new key remains
  - key: "pk_acme_xyz789"
    tenant: acme_corp
    role: analyst
```

---

## Key Revocation

### Immediate Revocation

Remove the key from configuration:

```yaml
api_keys:
  # Key removed - immediately invalid
```

### Soft Revocation

Mark as disabled:

```yaml
api_keys:
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
    enabled: false  # Disabled but preserved
```

---

## Key Scopes

### Dataset Restrictions

Limit keys to specific datasets:

```yaml
api_keys:
  - key: "pk_acme_limited"
    tenant: acme_corp
    role: analyst
    allowed_datasets:
      - orders
      - customers
    # Cannot access: products, inventory
```

### Read-Only Access

```yaml
api_keys:
  - key: "pk_acme_readonly"
    tenant: acme_corp
    role: viewer
    permissions:
      - read
    # Cannot: manage sources, etc.
```

---

## Security Best Practices

### 1. Never Commit Keys

```bash
# .gitignore
.env
config.yaml
**/secrets/**
```

### 2. Use Environment Variables

```bash
# Production
export API_KEY_ADMIN=$SECRET_MANAGER_VALUE

# Development
source .env.local
```

### 3. Rotate Regularly

| Environment | Rotation Frequency |
|-------------|-------------------|
| Production | Quarterly |
| Staging | Monthly |
| Development | On demand |

### 4. Principle of Least Privilege

Give minimum necessary access:

```yaml
# Good: Specific tenant, limited datasets
- key: "pk_acme_limited"
  tenant: acme_corp
  allowed_datasets: [orders]

# Avoid: Admin for regular use
- key: "admin-key"
  role: admin
```

### 5. Monitor Usage

```json
{
  "key": "pk_acme_***",
  "last_used": "2024-01-15T10:30:00Z",
  "total_requests": 15234,
  "avg_requests_per_day": 342
}
```

---

## Audit Logging

### What's Logged

Every API key usage:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "api_key": "pk_acme_***",
  "tenant": "acme_corp",
  "endpoint": "/v1/query",
  "dataset": "orders",
  "ip_address": "192.168.1.100",
  "user_agent": "PowerBI/2.0"
}
```

### Suspicious Activity Detection

Alert on:
- Unusual IP addresses
- High request volume
- Failed authentication attempts
- Access to unusual datasets

---

## Troubleshooting

### Invalid API Key

**Error**:
```json
{"detail": "Invalid API key"}
```

**Causes**:
- Key not in configuration
- Typo in key
- Key revoked

**Solutions**:
- Verify key exists in config
- Check for copy/paste errors
- Confirm key hasn't been rotated

### Missing API Key

**Error**:
```json
{"detail": "API key required"}
```

**Causes**:
- Header not sent
- Wrong header name

**Solutions**:
```bash
# Correct header name
-H "X-API-Key: your-key"

# Not these:
-H "Authorization: your-key"
-H "API-Key: your-key"
```

### Key Not Authorized

**Error**:
```json
{"detail": "Not authorized for dataset 'orders'"}
```

**Causes**:
- Key doesn't have access to dataset
- Role restrictions

**Solutions**:
- Check `allowed_datasets` configuration
- Verify role permissions

