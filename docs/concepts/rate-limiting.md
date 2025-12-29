# Rate Limiting

Protect your data warehouse from abuse and overload.

---

## Overview

Rate limiting controls how many requests each API key can make:

```
┌─────────────────────────────────────────────────────────┐
│                     RATE LIMITER                        │
├─────────────────────────────────────────────────────────┤
│  API Key: pk_acme_abc123                                │
│  Limit: 100/minute                                      │
│  Current: 45/100 ████████████░░░░░░░░░░░░░              │
│  Resets: 32 seconds                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# .env
RATE_LIMIT_QUERY=100/minute     # Query API limit
RATE_LIMIT_ODATA=50/minute      # OData endpoint limit
RATE_LIMIT_SOURCES=10/minute    # Source management limit
```

### Rate Limit Format

```
{count}/{period}
```

| Period | Description |
|--------|-------------|
| `second` | Per second |
| `minute` | Per minute |
| `hour` | Per hour |
| `day` | Per day |

Examples:
- `100/minute` - 100 requests per minute
- `1000/hour` - 1000 requests per hour
- `10/second` - 10 requests per second

---

## How It Works

### Token Bucket Algorithm

Each API key has a "bucket" of tokens:

1. Bucket starts full (100 tokens)
2. Each request consumes 1 token
3. Tokens refill over time
4. Empty bucket = rate limited

```
Time 0:00  [████████████████████] 100/100
Time 0:10  [████████████░░░░░░░░]  60/100  (40 requests)
Time 0:20  [████████████████░░░░]  80/100  (tokens refilling)
Time 0:30  [████████████████████] 100/100  (full again)
```

### Per-Key Isolation

Each API key has its own bucket:

```
pk_acme_abc123:   [████████████████████] 100/100
pk_globex_xyz789: [████████░░░░░░░░░░░░]  40/100
pk_wayne_555555:  [██████████████████░░]  90/100
```

One tenant can't exhaust another's quota.

---

## Rate Limit Headers

Every response includes rate limit headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1705320600
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed |
| `X-RateLimit-Remaining` | Requests left in window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

---

## Rate Limited Response

When limit exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 42
Content-Type: application/json

{
  "detail": "Rate limit exceeded",
  "limit": 100,
  "remaining": 0,
  "reset_in_seconds": 42
}
```

### Handling 429 Responses

```python
import time
import requests

def query_with_retry(payload, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(
            "http://localhost:8080/v1/query",
            headers={"X-API-Key": API_KEY},
            json=payload
        )
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited. Retrying in {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        return response.json()
    
    raise Exception("Max retries exceeded")
```

---

## Endpoint Limits

Different endpoints have different limits:

| Endpoint | Default Limit | Rationale |
|----------|---------------|-----------|
| `/v1/query` | 100/minute | Main query endpoint |
| `/odata/*` | 50/minute | Power BI connections |
| `/v1/sources` | 10/minute | Management operations |
| `/health` | Unlimited | Monitoring |

### Why Different Limits?

- **Query endpoints**: High traffic, need protection
- **Management endpoints**: Rare operations, strict limits
- **Health checks**: Always available for monitoring

---

## Customization

### Per-Key Limits (Advanced)

```yaml
api_keys:
  - key: "pk_premium_xxx"
    tenant: premium_corp
    rate_limit: "500/minute"  # Premium tier
  
  - key: "pk_basic_yyy"
    tenant: basic_corp
    rate_limit: "50/minute"   # Basic tier
```

### Burst Allowance

Allow short bursts above the limit:

```bash
RATE_LIMIT_QUERY=100/minute
RATE_LIMIT_BURST=20  # Allow 20 extra requests
```

---

## Monitoring

### Rate Limit Metrics

```bash
curl http://localhost:8080/admin/rate-limits \
  -H "X-API-Key: admin-key"
```

Response:

```json
{
  "keys": [
    {
      "key_prefix": "pk_acme_***",
      "endpoint": "/v1/query",
      "limit": 100,
      "used": 45,
      "remaining": 55,
      "reset_at": "2024-01-15T10:31:00Z"
    }
  ]
}
```

### Logging

Rate limit events are logged:

```json
{
  "level": "WARN",
  "event": "rate_limit_exceeded",
  "api_key": "pk_acme_***",
  "endpoint": "/v1/query",
  "limit": 100,
  "retry_after": 42
}
```

---

## Best Practices

### Setting Appropriate Limits

| Use Case | Recommended Limit |
|----------|-------------------|
| Dashboard users | 100/minute |
| Automated reports | 200/minute |
| API integrations | 500/minute |
| Development/testing | 50/minute |

### Client-Side Throttling

Implement throttling in your application:

```python
import time
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=80, period=60)  # Stay under 100/min limit
def safe_query(payload):
    return requests.post(url, json=payload)
```

### Dashboard Optimization

Instead of many small queries:

```javascript
// Bad: 10 separate queries
for (const metric of metrics) {
  await query({ metrics: [metric] });
}

// Good: One combined query
await query({ metrics: metrics });
```

---

## Troubleshooting

### Frequent Rate Limiting

**Symptoms**: Users hitting 429 often

**Causes**:
- Limit too low
- Polling too frequently
- Inefficient queries

**Solutions**:
- Increase rate limit
- Implement client-side throttling
- Combine queries
- Add caching

### Rate Limit Not Enforced

**Symptoms**: No 429 responses despite high traffic

**Causes**:
- Redis not connected
- Rate limiting disabled
- Admin key used

**Solutions**:
```bash
# Check Redis
redis-cli ping

# Verify config
echo $RATE_LIMIT_QUERY
```

### Uneven Rate Limiting

**Symptoms**: Some keys limited, others not

**Causes**:
- Per-key configuration
- Different usage patterns

**Solutions**:
- Review per-key settings
- Normalize rate limits

