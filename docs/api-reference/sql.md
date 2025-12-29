# SQL API

Execute raw SQL queries with automatic Row-Level Security.

## Endpoint

```
POST /v1/sql
```

## Authentication

Requires API key in header:
```
X-API-Key: your-api-key
```

---

## Request

```json
{
  "sql": "SELECT city, SUM(revenue) as total FROM orders GROUP BY city",
  "dataset": "orders"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sql` | string | Yes | SQL SELECT query |
| `dataset` | string | Yes | Dataset ID for RLS context |
| `parameters` | object | No | Query parameters |

---

## Response

```json
{
  "columns": [
    {"name": "city", "type": "string"},
    {"name": "total", "type": "number"}
  ],
  "data": [
    {"city": "Mumbai", "total": 15000},
    {"city": "Delhi", "total": 12000}
  ],
  "rowCount": 2,
  "executionTimeMs": 45,
  "rlsApplied": true,
  "tenant": "acme-corp"
}
```

---

## Security

### Row-Level Security

RLS is automatically applied based on your API key's tenant:

```sql
-- Your query
SELECT city, SUM(revenue) FROM orders GROUP BY city

-- Executed as (with RLS)
WITH rls_filtered AS (
    SELECT * FROM (SELECT city, SUM(revenue) FROM orders GROUP BY city) AS user_query
    WHERE tenant_id = 'your-tenant'
)
SELECT * FROM rls_filtered
```

### Allowed Operations

Only `SELECT` queries are permitted. The following are blocked:

- `DROP`, `DELETE`, `TRUNCATE`
- `INSERT`, `UPDATE`, `ALTER`
- `CREATE`, `GRANT`, `REVOKE`
- SQL comments (`--`, `/*`)

---

## Examples

### Basic Query

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "sql": "SELECT city, COUNT(*) as orders FROM orders GROUP BY city ORDER BY orders DESC LIMIT 10",
    "dataset": "orders"
  }'
```

### Query with Aggregations

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: your-api-key" \
  -d '{
    "sql": "SELECT DATE_TRUNC('\''month'\'', order_date) as month, SUM(revenue) as revenue FROM orders GROUP BY 1",
    "dataset": "orders"
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/sql",
    headers={"X-API-Key": "your-api-key"},
    json={
        "sql": "SELECT * FROM orders WHERE revenue > 1000",
        "dataset": "orders"
    }
)

data = response.json()
print(f"Rows: {data['rowCount']}")
```

### JavaScript Example

```javascript
const response = await fetch('http://localhost:8080/v1/sql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    sql: 'SELECT city, SUM(revenue) FROM orders GROUP BY city',
    dataset: 'orders'
  })
});

const data = await response.json();
console.log(data.data);
```

---

## When to Use SQL vs Semantic Query

| Use Case | Recommended API |
|----------|-----------------|
| Standard analytics | `/v1/query` (Semantic) |
| Complex joins | `/v1/sql` |
| Window functions | `/v1/sql` |
| CTEs | `/v1/sql` |
| Simple aggregations | `/v1/query` (Semantic) |
| BI tool integration | `/v1/query` or OData |

---

## Error Handling

### Invalid Query

```json
{
  "detail": "Only SELECT queries are allowed"
}
```

### Dangerous Operation

```json
{
  "detail": "Query contains disallowed operation"
}
```

### Execution Error

```json
{
  "detail": "Query execution failed: column 'xyz' not found"
}
```

---

## Next Steps

- [Query API Reference](query.md)
- [GraphQL API](graphql.md)
- [Row-Level Security](../guides/rls.md)

