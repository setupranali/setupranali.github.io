# GraphQL API

SetuPranali provides a GraphQL API as an alternative to REST for querying the semantic layer.

## Endpoint

```
POST /v1/graphql
```

## GraphQL Playground

Access the interactive GraphQL IDE at:

```
http://localhost:8080/v1/graphql
```

---

## Authentication

Pass your API key in the request headers:

```
X-API-Key: your-api-key
```

---

## Schema

### Queries

#### `health`

Get system health status.

```graphql
query {
  health {
    status
    version
    cacheEnabled
    redisAvailable
  }
}
```

#### `datasets`

List all available datasets.

```graphql
query {
  datasets {
    id
    name
    description
    tags
  }
}
```

#### `dataset(id: String!)`

Get details of a specific dataset.

```graphql
query {
  dataset(id: "orders") {
    id
    name
    description
    source
    tags
    dimensions {
      name
      label
      type
      description
    }
    metrics {
      name
      label
      type
      sql
      description
    }
    defaultTimezone
  }
}
```

#### `query(input: QueryInput!)`

Execute a semantic query.

```graphql
query GetRevenue($input: QueryInput!) {
  query(input: $input) {
    columns {
      name
      type
    }
    data
    rowCount
    cached
    executionTimeMs
  }
}
```

Variables:
```json
{
  "input": {
    "dataset": "orders",
    "dimensions": [{ "name": "city" }],
    "metrics": [{ "name": "total_revenue" }],
    "filters": [
      { "field": "order_date", "operator": "gte", "value": "2024-01-01" }
    ],
    "limit": 100
  }
}
```

---

## Input Types

### QueryInput

```graphql
input QueryInput {
  dataset: String!
  dimensions: [DimensionInput!]
  metrics: [MetricInput!]
  filters: [FilterInput!]
  orderBy: [OrderByInput!]
  limit: Int = 1000
  offset: Int = 0
}
```

### DimensionInput

```graphql
input DimensionInput {
  name: String!
}
```

### MetricInput

```graphql
input MetricInput {
  name: String!
}
```

### FilterInput

```graphql
input FilterInput {
  field: String!
  operator: String!  # eq, ne, gt, gte, lt, lte, in, between, like
  value: JSON!
}
```

### OrderByInput

```graphql
input OrderByInput {
  field: String!
  direction: String = "asc"  # asc or desc
}
```

---

## Mutations

### `refreshCache(datasetId: String!)`

Invalidate cache for a dataset. Requires admin role.

```graphql
mutation {
  refreshCache(datasetId: "orders")
}
```

---

## Examples

### Basic Query

```graphql
query {
  query(input: {
    dataset: "orders"
    dimensions: [{ name: "city" }]
    metrics: [{ name: "total_revenue" }, { name: "order_count" }]
    limit: 10
  }) {
    columns {
      name
      type
    }
    data
    rowCount
  }
}
```

### Query with Filters

```graphql
query {
  query(input: {
    dataset: "orders"
    dimensions: [{ name: "city" }, { name: "order_date" }]
    metrics: [{ name: "total_revenue" }]
    filters: [
      { field: "order_date", operator: "gte", value: "2024-01-01" }
      { field: "city", operator: "in", value: ["Mumbai", "Delhi"] }
    ]
    orderBy: [{ field: "total_revenue", direction: "desc" }]
    limit: 100
  }) {
    data
    rowCount
    cached
    executionTimeMs
  }
}
```

### Introspect Dataset

```graphql
query {
  dataset(id: "orders") {
    dimensions {
      name
      label
      type
    }
    metrics {
      name
      label
      description
    }
  }
}
```

---

## Using with cURL

```bash
curl -X POST http://localhost:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "query { datasets { id name } }"
  }'
```

---

## Using with JavaScript

```javascript
const query = `
  query GetData($input: QueryInput!) {
    query(input: $input) {
      data
      rowCount
    }
  }
`;

const variables = {
  input: {
    dataset: "orders",
    dimensions: [{ name: "city" }],
    metrics: [{ name: "total_revenue" }]
  }
};

fetch('http://localhost:8080/v1/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({ query, variables })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## Using with Python

```python
import requests

query = """
query GetData($input: QueryInput!) {
  query(input: $input) {
    data
    rowCount
  }
}
"""

variables = {
    "input": {
        "dataset": "orders",
        "dimensions": [{"name": "city"}],
        "metrics": [{"name": "total_revenue"}]
    }
}

response = requests.post(
    'http://localhost:8080/v1/graphql',
    headers={
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key'
    },
    json={'query': query, 'variables': variables}
)

print(response.json())
```

---

## Row-Level Security

GraphQL queries automatically apply RLS based on your API key's tenant:

```graphql
# With API key for tenant "acme-corp"
query {
  query(input: { dataset: "orders", metrics: [{ name: "total_revenue" }] }) {
    data  # Only returns data for acme-corp
  }
}
```

---

## Error Handling

Errors are returned in the standard GraphQL format:

```json
{
  "data": null,
  "errors": [
    {
      "message": "Dataset not found",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["query"]
    }
  ]
}
```

---

## Next Steps

- [REST API Reference](query.md)
- [Authentication](authentication.md)
- [Row-Level Security](../guides/rls.md)

