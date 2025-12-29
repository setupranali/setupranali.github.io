# Query API

Execute semantic queries against your datasets.

---

## Endpoint

```
POST /v1/query
```

---

## Request

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | API key for authentication |
| `Content-Type` | Yes | `application/json` |

### Body

```json
{
  "dataset": "string",
  "dimensions": ["string"],
  "metrics": ["string"],
  "filters": [
    {
      "field": "string",
      "op": "string",
      "value": "any"
    }
  ],
  "orderBy": [
    {
      "field": "string",
      "direction": "asc|desc"
    }
  ],
  "limit": "integer",
  "offset": "integer"
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dataset` | string | Yes | Dataset name |
| `dimensions` | string[] | No | Dimension fields |
| `metrics` | string[] | No | Metric fields |
| `filters` | object[] | No | Filter conditions |
| `orderBy` | object[] | No | Sort order |
| `limit` | integer | No | Max rows (default: 10000) |
| `offset` | integer | No | Skip rows |

---

## Response

### Success (200)

```json
{
  "columns": [
    {
      "name": "region",
      "type": "string"
    },
    {
      "name": "revenue",
      "type": "number"
    }
  ],
  "rows": [
    ["North", 125000.00],
    ["South", 89000.00]
  ],
  "stats": {
    "rowCount": 2,
    "executionTimeMs": 45,
    "cached": false,
    "cachedAt": null
  }
}
```

### Error (4xx/5xx)

```json
{
  "detail": "Dataset 'unknown' not found"
}
```

---

## Filter Operators

| Operator | Description | Example Value |
|----------|-------------|---------------|
| `=` | Equals | `"North"` |
| `!=` | Not equals | `"Cancelled"` |
| `>` | Greater than | `100` |
| `>=` | Greater or equal | `"2024-01-01"` |
| `<` | Less than | `1000` |
| `<=` | Less or equal | `"2024-12-31"` |
| `in` | In list | `["North", "South"]` |
| `not_in` | Not in list | `["Cancelled"]` |
| `like` | Pattern match | `"%Corp%"` |
| `is_null` | Is null | `true` |
| `is_not_null` | Is not null | `true` |

---

## Examples

### Basic Query

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue", "orders"]
  }'
```

### With Filters

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["product"],
    "metrics": ["revenue"],
    "filters": [
      {"field": "region", "op": "=", "value": "North"},
      {"field": "order_date", "op": ">=", "value": "2024-01-01"}
    ]
  }'
```

### With Sorting and Limit

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["product"],
    "metrics": ["revenue"],
    "orderBy": [{"field": "revenue", "direction": "desc"}],
    "limit": 10
  }'
```

### Metrics Only (Totals)

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "metrics": ["revenue", "orders"]
  }'
```

Response:

```json
{
  "columns": [
    {"name": "revenue", "type": "number"},
    {"name": "orders", "type": "number"}
  ],
  "rows": [
    [1250000.00, 5432]
  ]
}
```

### In Filter

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue"],
    "filters": [
      {"field": "region", "op": "in", "value": ["North", "South"]}
    ]
  }'
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Unknown dimension 'invalid' in dataset 'sales'"
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

### 429 Rate Limited

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Rate Limiting

Default: 100 requests per minute per API key.

Headers in response:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705320600
```

---

## Caching

Responses are cached by default.

Check cache status in `stats`:

```json
{
  "stats": {
    "cached": true,
    "cachedAt": "2024-01-15T10:30:00Z"
  }
}
```

Bypass cache:

```bash
-H "Cache-Control: no-cache"
```

