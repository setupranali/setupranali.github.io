# REST API

Connect any tool to SetuPranali via REST API.

---

## Overview

The REST API provides universal access:

```
Any Tool → REST API → SetuPranali → Your Data
```

Works with:
- Custom applications
- Scripts (Python, Node.js, etc.)
- Looker Studio
- Metabase
- Any HTTP client

---

## Quick Start

### Query Data

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue", "orders"]
  }'
```

### Response

```json
{
  "columns": [
    {"name": "region", "type": "string"},
    {"name": "revenue", "type": "number"},
    {"name": "orders", "type": "number"}
  ],
  "rows": [
    ["North", 125000.00, 342],
    ["South", 89000.00, 156]
  ],
  "stats": {
    "rowCount": 2,
    "executionTimeMs": 45,
    "cached": false
  }
}
```

---

## Authentication

Include API key in header:

```bash
-H "X-API-Key: your-api-key"
```

---

## Query Parameters

### Dimensions

Group-by columns:

```json
{
  "dimensions": ["region", "product"]
}
```

### Metrics

Aggregated values:

```json
{
  "metrics": ["revenue", "orders"]
}
```

### Filters

```json
{
  "filters": [
    {"field": "region", "op": "=", "value": "North"},
    {"field": "revenue", "op": ">", "value": 10000}
  ]
}
```

### Operators

| Operator | Description |
|----------|-------------|
| `=` | Equals |
| `!=` | Not equals |
| `>` | Greater than |
| `>=` | Greater or equal |
| `<` | Less than |
| `<=` | Less or equal |
| `in` | In list |
| `like` | Pattern match |

### Sorting

```json
{
  "orderBy": [
    {"field": "revenue", "direction": "desc"}
  ]
}
```

### Limit

```json
{
  "limit": 100
}
```

---

## Language Examples

### Python

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/query",
    headers={
        "X-API-Key": "your-api-key",
        "Content-Type": "application/json"
    },
    json={
        "dataset": "sales",
        "dimensions": ["region"],
        "metrics": ["revenue", "orders"]
    }
)

data = response.json()

# Convert to DataFrame
import pandas as pd
df = pd.DataFrame(
    data["rows"],
    columns=[c["name"] for c in data["columns"]]
)
print(df)
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8080/v1/query', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    dataset: 'sales',
    dimensions: ['region'],
    metrics: ['revenue', 'orders']
  })
});

const data = await response.json();
console.log(data.rows);
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

func main() {
    payload := map[string]interface{}{
        "dataset":    "sales",
        "dimensions": []string{"region"},
        "metrics":    []string{"revenue", "orders"},
    }
    
    body, _ := json.Marshal(payload)
    
    req, _ := http.NewRequest("POST", "http://localhost:8080/v1/query", bytes.NewBuffer(body))
    req.Header.Set("X-API-Key", "your-api-key")
    req.Header.Set("Content-Type", "application/json")
    
    client := &http.Client{}
    resp, _ := client.Do(req)
    defer resp.Body.Close()
    
    // Handle response
}
```

---

## Error Handling

### 400 Bad Request

```json
{
  "detail": "Unknown dimension 'invalid_field' in dataset 'sales'"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found

```json
{
  "detail": "Dataset 'unknown' not found"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

### Python Error Handling

```python
response = requests.post(url, headers=headers, json=payload)

if response.status_code == 429:
    retry_after = response.headers.get('Retry-After', 60)
    time.sleep(int(retry_after))
    response = requests.post(url, headers=headers, json=payload)

response.raise_for_status()
data = response.json()
```

---

## Pagination

For large results:

```json
{
  "dataset": "sales",
  "dimensions": ["customer_id"],
  "metrics": ["revenue"],
  "limit": 1000,
  "offset": 0
}
```

Next page:

```json
{
  "limit": 1000,
  "offset": 1000
}
```

---

## Caching Behavior

### Check Cache Status

Response includes cache info:

```json
{
  "stats": {
    "cached": true,
    "cachedAt": "2024-01-15T10:30:00Z"
  }
}
```

### Force Fresh Query

Add header to bypass cache:

```bash
-H "Cache-Control: no-cache"
```

---

## Best Practices

### 1. Batch Requests

Combine related queries:

```json
{
  "dataset": "sales",
  "dimensions": ["region", "product"],
  "metrics": ["revenue", "orders", "avg_order_value"]
}
```

### 2. Use Filters

Reduce data transfer:

```json
{
  "filters": [
    {"field": "order_date", "op": ">=", "value": "2024-01-01"}
  ]
}
```

### 3. Handle Rate Limits

Implement retry logic:

```python
def query_with_retry(payload, max_retries=3):
    for i in range(max_retries):
        response = requests.post(url, json=payload)
        if response.status_code != 429:
            return response
        time.sleep(response.headers.get('Retry-After', 60))
    raise Exception("Max retries exceeded")
```

### 4. Monitor Performance

Track in your application:

```python
start = time.time()
response = query(payload)
duration = time.time() - start

metrics.timing('bi_query', duration)
metrics.increment('bi_query.cached' if response['stats']['cached'] else 'bi_query.fresh')
```

