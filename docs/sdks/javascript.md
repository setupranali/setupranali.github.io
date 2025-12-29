# JavaScript/TypeScript SDK

Modern TypeScript SDK for Node.js and browsers.

## Installation

```bash
npm install @setupranali/client
# or
yarn add @setupranali/client
# or
pnpm add @setupranali/client
```

---

## Quick Start

```typescript
import { SetuPranali } from '@setupranali/client';

const client = new SetuPranali({
  url: 'http://localhost:8080',
  apiKey: 'your-api-key'
});

// List datasets
const datasets = await client.datasets();
console.log(datasets);

// Query data
const result = await client.query({
  dataset: 'orders',
  dimensions: ['city', 'product'],
  metrics: ['total_revenue', 'order_count'],
  filters: [
    { field: 'order_date', operator: 'gte', value: '2024-01-01' }
  ],
  orderBy: [{ field: 'total_revenue', direction: 'desc' }],
  limit: 100
});

console.log(result.data);
```

---

## Factory Function

```typescript
import { createClient } from '@setupranali/client';

const client = createClient({
  url: 'http://localhost:8080',
  apiKey: 'your-api-key'
});
```

---

## Configuration

```typescript
const client = new SetuPranali({
  url: 'https://api.example.com',  // Server URL (required)
  apiKey: 'sk_live_xxx',           // API key (optional for public endpoints)
  timeout: 30000,                  // Request timeout in ms (default: 30000)
  headers: {                       // Additional headers
    'X-Custom-Header': 'value'
  }
});
```

---

## API Reference

### `client.health()`

Check server health.

```typescript
const health = await client.health();
console.log(health.status);   // 'ok'
console.log(health.version);  // '1.0.0'
```

### `client.datasets()`

List available datasets.

```typescript
const datasets = await client.datasets();
datasets.forEach(ds => {
  console.log(`${ds.id}: ${ds.name}`);
});
```

### `client.dataset(id)`

Get dataset details.

```typescript
const dataset = await client.dataset('orders');
console.log(dataset.dimensions);
console.log(dataset.metrics);
```

### `client.query(options)`

Execute semantic query.

```typescript
const result = await client.query({
  dataset: 'orders',
  dimensions: ['city'],
  metrics: ['total_revenue'],
  filters: [
    { field: 'status', operator: 'eq', value: 'completed' }
  ],
  orderBy: [{ field: 'total_revenue', direction: 'desc' }],
  limit: 100,
  offset: 0
});

console.log(result.data);
console.log(result.rowCount);
console.log(result.cached);
```

### `client.graphql(query, variables)`

Execute GraphQL query.

```typescript
const result = await client.graphql(`
  query GetData($input: QueryInput!) {
    query(input: $input) {
      data
      rowCount
    }
  }
`, {
  input: {
    dataset: 'orders',
    dimensions: [{ name: 'city' }],
    metrics: [{ name: 'total_revenue' }]
  }
});
```

---

## TypeScript Types

Full type definitions included:

```typescript
import type {
  Dataset,
  DatasetSummary,
  Dimension,
  Metric,
  QueryResult,
  QueryOptions,
  Filter,
  OrderBy,
  HealthStatus,
  ClientConfig
} from '@setupranali/client';

// Typed query result
interface OrderRow {
  city: string;
  total_revenue: number;
}

const result: QueryResult<OrderRow> = await client.query({
  dataset: 'orders',
  dimensions: ['city'],
  metrics: ['total_revenue']
});

result.data.forEach(row => {
  console.log(row.city, row.total_revenue);
});
```

---

## Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `{ field: 'city', operator: 'eq', value: 'Mumbai' }` |
| `ne` | Not equal | `{ field: 'status', operator: 'ne', value: 'cancelled' }` |
| `gt` | Greater than | `{ field: 'amount', operator: 'gt', value: 100 }` |
| `gte` | Greater or equal | `{ field: 'date', operator: 'gte', value: '2024-01-01' }` |
| `lt` | Less than | `{ field: 'qty', operator: 'lt', value: 10 }` |
| `lte` | Less or equal | `{ field: 'price', operator: 'lte', value: 500 }` |
| `in` | In list | `{ field: 'city', operator: 'in', value: ['Mumbai', 'Delhi'] }` |
| `like` | Pattern match | `{ field: 'name', operator: 'like', value: '%Corp%' }` |

---

## Error Handling

```typescript
import {
  SetuPranali,
  AuthenticationError,
  DatasetNotFoundError,
  QueryError,
  RateLimitError,
  ConnectionError
} from '@setupranali/client';

try {
  const result = await client.query({ dataset: 'orders', metrics: ['revenue'] });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof DatasetNotFoundError) {
    console.error('Dataset not found');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof QueryError) {
    console.error('Query failed:', error.message);
  } else if (error instanceof ConnectionError) {
    console.error('Connection failed');
  }
}
```

---

## Browser Usage

Works in modern browsers with native `fetch`:

```html
<script type="module">
  import { SetuPranali } from 'https://cdn.jsdelivr.net/npm/@setupranali/client/dist/index.mjs';
  
  const client = new SetuPranali({
    url: 'http://localhost:8080',
    apiKey: 'your-key'
  });
  
  const datasets = await client.datasets();
  console.log(datasets);
</script>
```

---

## Node.js Usage

Works in Node.js 18+ (native fetch):

```javascript
const { SetuPranali } = require('@setupranali/client');

const client = new SetuPranali({
  url: 'http://localhost:8080',
  apiKey: 'your-key'
});

const result = await client.query({
  dataset: 'orders',
  metrics: ['revenue']
});
```

For Node.js < 18, use a fetch polyfill:

```javascript
const fetch = require('node-fetch');
globalThis.fetch = fetch;

const { SetuPranali } = require('@setupranali/client');
```

---

## React Example

```tsx
import { useEffect, useState } from 'react';
import { SetuPranali, QueryResult } from '@setupranali/client';

const client = new SetuPranali({
  url: process.env.REACT_APP_API_URL!,
  apiKey: process.env.REACT_APP_API_KEY!
});

function RevenueChart() {
  const [data, setData] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.query({
      dataset: 'orders',
      dimensions: ['month'],
      metrics: ['revenue']
    })
    .then(setData)
    .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading...</div>;
  
  return (
    <ul>
      {data?.data.map((row, i) => (
        <li key={i}>{row.month}: ${row.revenue}</li>
      ))}
    </ul>
  );
}
```

---

## Next Steps

- [API Reference](../api-reference/query.md)
- [GraphQL API](../api-reference/graphql.md)
- [Examples](../examples/index.md)

