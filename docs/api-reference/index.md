# API Reference

Complete API documentation for SetuPranali.

---

## Endpoints

### Core APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/v1/query`](query.md) | POST | Execute semantic query |
| [`/v1/graphql`](graphql.md) | POST | GraphQL API for flexible queries |
| [`/v1/sql`](sql.md) | POST | SQL queries with automatic RLS |
| [`/v1/nlq`](nlq.md) | POST | Natural language to query translation |
| [`/odata/{dataset}`](odata.md) | GET | OData feed for Power BI/Excel |

### Management APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/v1/sources`](sources.md) | GET/POST/DELETE | Manage data sources |
| [`/v1/datasets`](introspection.md) | GET | List all datasets |
| [`/v1/introspection/datasets`](introspection.md) | GET | Schema introspection |
| [`/v1/introspection/openapi`](introspection.md#openapi-schema) | GET | OpenAPI schema export |
| [`/v1/health`](authentication.md#health-check) | GET | Health check |

---

## Query API Comparison

| API | Best For | Features |
|-----|----------|----------|
| **Query API** | Semantic queries | Dimensions, metrics, filters |
| **GraphQL** | Flexible queries | Typed schema, introspection |
| **SQL** | Direct SQL | Full SQL with auto-RLS |
| **NLQ** | Natural language | AI-powered query translation |
| **OData** | Power BI, Excel | Native BI tool refresh |

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

## SDKs & Libraries

For easier integration, use our official SDKs:

| SDK | Language | Installation |
|-----|----------|--------------|
| [Python SDK](../sdks/python.md) | Python 3.9+ | `pip install setupranali` |
| [JavaScript SDK](../sdks/javascript.md) | Node.js/Browser | `npm install @setupranali/client` |
| [Jupyter Widget](../sdks/jupyter.md) | Jupyter | Included in Python SDK |

---

## Interactive Documentation

API documentation is available at:

```
http://localhost:8080/docs     # Swagger UI
http://localhost:8080/redoc    # ReDoc
http://localhost:8080/graphql  # GraphQL Playground
```

