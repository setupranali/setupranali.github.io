# Authentication

API key authentication for SetuPranali.

---

## Overview

All API requests require authentication via API key.

```bash
curl http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key"
```

---

## API Key Header

Include the API key in the `X-API-Key` header:

```
X-API-Key: pk_tenant_abc123
```

---

## Key Types

| Role | Purpose | RLS | Management |
|------|---------|-----|------------|
| `admin` | Full access | Bypassed | Yes |
| `analyst` | Query data | Applied | No |
| `viewer` | Read-only | Applied | No |

---

## Obtaining API Keys

### From Configuration

Keys are defined in configuration:

```yaml
api_keys:
  - key: "admin-key-xxxxx"
    role: admin
  
  - key: "pk_acme_abc123"
    tenant: acme_corp
    role: analyst
```

### From Admin

Contact your platform administrator for API keys.

---

## Using API Keys

### REST API

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_tenant_abc123" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "sales", "metrics": ["revenue"]}'
```

### Power BI

1. Go to **Advanced** options
2. Add HTTP header:
   - Name: `X-API-Key`
   - Value: `pk_tenant_abc123`

### Tableau

Enter API key in Web Data Connector authentication field.

### Python

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/query",
    headers={"X-API-Key": "pk_tenant_abc123"},
    json={"dataset": "sales", "metrics": ["revenue"]}
)
```

---

## Error Responses

### Missing API Key

```json
{
  "detail": "API key required"
}
```

HTTP Status: `401 Unauthorized`

### Invalid API Key

```json
{
  "detail": "Invalid API key"
}
```

HTTP Status: `401 Unauthorized`

### Insufficient Permissions

```json
{
  "detail": "Admin API key required"
}
```

HTTP Status: `403 Forbidden`

---

## Health Check

The health endpoint does not require authentication:

```bash
curl http://localhost:8080/health
```

Response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "redis": "connected"
}
```

---

## Best Practices

### 1. Keep Keys Secret

- Never commit keys to git
- Use environment variables
- Don't log API keys

### 2. Use Appropriate Scope

- Use analyst keys for BI tools
- Reserve admin keys for management
- Create per-tenant keys for RLS

### 3. Rotate Regularly

- Rotate keys quarterly
- Revoke compromised keys immediately
- Maintain key inventory

### 4. Monitor Usage

Track API key usage for:
- Unusual activity
- Rate limit hits
- Failed authentications

---

## Troubleshooting

### "API key required"

**Cause**: X-API-Key header missing

**Solution**: Add header to request

```bash
-H "X-API-Key: your-key"
```

### "Invalid API key"

**Cause**: Key doesn't exist or is revoked

**Solution**: Verify key is in configuration

### "Admin API key required"

**Cause**: Non-admin key used for admin endpoint

**Solution**: Use admin key for source management

