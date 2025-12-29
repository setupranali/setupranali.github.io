# API Reference

Complete API documentation for SetuPranali.

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/v1/query`](query.md) | POST | Execute semantic query |
| [`/odata/{dataset}`](odata.md) | GET | OData feed for BI tools |
| [`/v1/sources`](sources.md) | GET/POST/DELETE | Manage data sources |
| [`/health`](authentication.md#health-check) | GET | Health check |

---

## Authentication

All endpoints require API key authentication:

```bash
-H "X-API-Key: your-api-key"
```

See [Authentication](authentication.md) for details.

---

## Quick Reference

### Query Data

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue"]
  }'
```

### OData Feed

```bash
curl http://localhost:8080/odata/sales \
  -H "X-API-Key: your-key"
```

### List Sources

```bash
curl http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key"
```

---

## Response Format

### Success

```json
{
  "columns": [...],
  "rows": [...],
  "stats": {
    "rowCount": 100,
    "executionTimeMs": 45,
    "cached": false
  }
}
```

### Error

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

---

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 404 | Not found (dataset/source) |
| 429 | Rate limited |
| 500 | Server error |

---

## Interactive Documentation

API documentation is available at:

```
http://localhost:8080/docs     # Swagger UI
http://localhost:8080/redoc    # ReDoc
```

