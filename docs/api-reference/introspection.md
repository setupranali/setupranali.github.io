# Schema Introspection API

Discover datasets, dimensions, and metrics programmatically.

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /v1/introspection/datasets` | Get all datasets with full schema |
| `GET /v1/introspection/datasets/{id}` | Get single dataset schema |
| `GET /v1/introspection/openapi` | Get OpenAPI specification |

---

## Get All Datasets

```
GET /v1/introspection/datasets
```

### Response

```json
{
  "datasets": [
    {
      "id": "orders",
      "name": "Orders",
      "description": "Order-level facts",
      "source": "warehouse",
      "tags": ["sales", "demo"],
      "schema": {
        "dimensions": [
          {
            "name": "city",
            "label": "City",
            "type": "string",
            "description": "Customer city",
            "sql": "city",
            "hidden": false
          }
        ],
        "metrics": [
          {
            "name": "total_revenue",
            "label": "Total Revenue",
            "type": "number",
            "description": "Sum of order revenue",
            "sql": "SUM(revenue)",
            "aggregation": "sum",
            "format": "$#,##0",
            "hidden": false
          }
        ]
      },
      "defaultTimezone": "UTC",
      "refreshPolicy": "onDemand"
    }
  ],
  "version": "1.0.0",
  "generatedAt": "2024-12-29T10:30:00Z"
}
```

---

## Get Single Dataset

```
GET /v1/introspection/datasets/{datasetId}
```

### Response

```json
{
  "id": "orders",
  "name": "Orders",
  "description": "Order-level facts",
  "source": "warehouse",
  "tags": ["sales"],
  "table": "public.orders",
  "sql": null,
  "schema": {
    "dimensions": [
      {
        "name": "city",
        "label": "City",
        "type": "string",
        "description": "Customer city",
        "sql": "city",
        "primaryKey": false,
        "hidden": false,
        "values": null
      },
      {
        "name": "order_date",
        "label": "Order Date",
        "type": "date",
        "description": "Date of order",
        "sql": "order_date",
        "primaryKey": false,
        "hidden": false,
        "values": null
      }
    ],
    "metrics": [
      {
        "name": "total_revenue",
        "label": "Total Revenue",
        "type": "number",
        "description": "Sum of order revenue",
        "sql": "SUM(revenue)",
        "aggregation": "sum",
        "format": "$#,##0",
        "hidden": false,
        "drillMembers": ["city", "order_date"]
      },
      {
        "name": "order_count",
        "label": "Order Count",
        "type": "number",
        "sql": "COUNT(*)",
        "aggregation": "count",
        "hidden": false,
        "drillMembers": []
      }
    ]
  },
  "joins": [],
  "filters": [],
  "rls": {
    "enabled": true,
    "field": "tenant_id"
  },
  "defaultTimezone": "UTC",
  "refreshPolicy": "onDemand",
  "generatedAt": "2024-12-29T10:30:00Z"
}
```

---

## Get OpenAPI Specification

```
GET /v1/introspection/openapi
```

Returns the full OpenAPI 3.0 specification for the SetuPranali API.

---

## Use Cases

### Auto-Discovery in BI Tools

```python
import requests

# Fetch all available datasets
response = requests.get("http://localhost:8080/v1/introspection/datasets")
datasets = response.json()["datasets"]

# Build dropdown options for UI
for dataset in datasets:
    print(f"Dataset: {dataset['name']}")
    for dim in dataset['schema']['dimensions']:
        print(f"  Dimension: {dim['label']} ({dim['type']})")
    for metric in dataset['schema']['metrics']:
        print(f"  Metric: {metric['label']} ({metric['aggregation']})")
```

### Dynamic Query Builder

```javascript
// Fetch dataset schema
const response = await fetch('/v1/introspection/datasets/orders');
const dataset = await response.json();

// Build query UI dynamically
const dimensions = dataset.schema.dimensions.filter(d => !d.hidden);
const metrics = dataset.schema.metrics.filter(m => !m.hidden);

// Populate selectors
dimensionSelect.innerHTML = dimensions.map(d => 
  `<option value="${d.name}">${d.label}</option>`
).join('');
```

### Schema Validation

```python
def validate_query(dataset_id, dimensions, metrics):
    # Get schema
    schema = requests.get(f"/v1/introspection/datasets/{dataset_id}").json()
    
    valid_dims = {d['name'] for d in schema['schema']['dimensions']}
    valid_metrics = {m['name'] for m in schema['schema']['metrics']}
    
    # Validate
    invalid_dims = set(dimensions) - valid_dims
    invalid_metrics = set(metrics) - valid_metrics
    
    if invalid_dims or invalid_metrics:
        raise ValueError(f"Invalid fields: {invalid_dims | invalid_metrics}")
```

---

## Schema Properties

### Dimension Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Unique identifier |
| `label` | string | Display name |
| `type` | string | Data type (string, number, date, etc.) |
| `description` | string | Human-readable description |
| `sql` | string | SQL expression |
| `primaryKey` | boolean | Is primary key |
| `hidden` | boolean | Hidden from UI |
| `values` | array | Enum values (if applicable) |

### Metric Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Unique identifier |
| `label` | string | Display name |
| `type` | string | Data type |
| `description` | string | Human-readable description |
| `sql` | string | SQL aggregation expression |
| `aggregation` | string | Type: sum, count, avg, min, max |
| `format` | string | Display format |
| `hidden` | boolean | Hidden from UI |
| `drillMembers` | array | Drill-down dimensions |

---

## Next Steps

- [Query API](query.md)
- [GraphQL API](graphql.md)
- [Datasets Guide](../guides/datasets.md)

