# First Query

Learn how to run your first query through the SetuPranali API.

---

## Query Anatomy

Every query has three main parts:

```json
{
  "dataset": "sales",              // Which dataset to query
  "dimensions": ["region"],        // Group-by columns
  "metrics": ["revenue", "orders"] // Aggregated values
}
```

---

## Basic Query

### Request

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue"]
  }'
```

### Response

```json
{
  "columns": [
    {"name": "region", "type": "string"},
    {"name": "revenue", "type": "number"}
  ],
  "rows": [
    ["North", 125000.00],
    ["South", 89000.00],
    ["East", 156000.00],
    ["West", 112000.00]
  ],
  "stats": {
    "rowCount": 4,
    "executionTimeMs": 234,
    "cached": false
  }
}
```

---

## Adding Filters

Filter your data with operators like `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `like`.

### Request

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["product"],
    "metrics": ["revenue", "orders"],
    "filters": [
      {"field": "region", "op": "=", "value": "North"},
      {"field": "order_date", "op": ">=", "value": "2024-01-01"}
    ]
  }'
```

### Available Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `{"field": "region", "op": "=", "value": "North"}` |
| `!=` | Not equals | `{"field": "status", "op": "!=", "value": "cancelled"}` |
| `>` | Greater than | `{"field": "amount", "op": ">", "value": 100}` |
| `>=` | Greater or equal | `{"field": "date", "op": ">=", "value": "2024-01-01"}` |
| `<` | Less than | `{"field": "quantity", "op": "<", "value": 10}` |
| `<=` | Less or equal | `{"field": "date", "op": "<=", "value": "2024-12-31"}` |
| `in` | In list | `{"field": "region", "op": "in", "value": ["North", "South"]}` |
| `like` | Pattern match | `{"field": "name", "op": "like", "value": "%Corp%"}` |

---

## Sorting Results

### Request

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["product"],
    "metrics": ["revenue"],
    "orderBy": [
      {"field": "revenue", "direction": "desc"}
    ]
  }'
```

### Response

Results are sorted by revenue, highest first:

```json
{
  "rows": [
    ["Electronics", 256000.00],
    ["Furniture", 189000.00],
    ["Clothing", 145000.00]
  ]
}
```

---

## Limiting Results

### Request

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["product"],
    "metrics": ["revenue"],
    "orderBy": [{"field": "revenue", "direction": "desc"}],
    "limit": 5
  }'
```

---

## Multiple Dimensions

Group by multiple columns:

### Request

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region", "product", "order_date"],
    "metrics": ["revenue", "orders", "avg_order_value"]
  }'
```

---

## Query with Row-Level Security

When you use a tenant-specific API key, RLS is automatic:

```bash
# This key belongs to tenant "acme_corp"
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue"]
  }'
```

The query automatically includes `WHERE tenant_id = 'acme_corp'`.

!!! info "RLS is Invisible"
    The API response looks exactly the same—but only includes rows 
    for that tenant. Users cannot bypass this filter.

---

## Complete Example

Here's a full query with all options:

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_acme_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region", "product"],
    "metrics": ["revenue", "orders"],
    "filters": [
      {"field": "order_date", "op": ">=", "value": "2024-01-01"},
      {"field": "order_date", "op": "<=", "value": "2024-12-31"},
      {"field": "status", "op": "!=", "value": "cancelled"}
    ],
    "orderBy": [
      {"field": "revenue", "direction": "desc"}
    ],
    "limit": 100
  }'
```

---

## Error Handling

### Invalid Dataset

```json
{
  "detail": "Dataset 'unknown' not found"
}
```

### Invalid Field

```json
{
  "detail": "Unknown dimension 'invalid_field' in dataset 'sales'"
}
```

### Rate Limited

```json
{
  "detail": "Rate limit exceeded. Retry after 60 seconds."
}
```

---

## Python Example

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/query",
    headers={
        "X-API-Key": "pk_acme_abc123",
        "Content-Type": "application/json"
    },
    json={
        "dataset": "sales",
        "dimensions": ["region"],
        "metrics": ["revenue", "orders"]
    }
)

data = response.json()

for row in data["rows"]:
    print(f"Region: {row[0]}, Revenue: ${row[1]:,.2f}")
```

---

## Next Steps

<div class="grid cards" markdown>

-   **Connect Power BI**

    ---

    Use OData to connect Power BI.

    [:octicons-arrow-right-24: Power BI](../integrations/bi-tools/powerbi.md)

-   **Connect Tableau**

    ---

    Use the Web Data Connector.

    [:octicons-arrow-right-24: Tableau](../integrations/bi-tools/tableau.md)

-   **API Reference**

    ---

    Complete query API documentation.

    [:octicons-arrow-right-24: Query API](../api-reference/query.md)

</div>

