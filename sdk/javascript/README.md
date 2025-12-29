# @setupranali/client

JavaScript/TypeScript SDK for the SetuPranali semantic analytics layer.

## Installation

```bash
npm install @setupranali/client
# or
yarn add @setupranali/client
# or
pnpm add @setupranali/client
```

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
console.log(`Rows: ${result.rowCount}, Cached: ${result.cached}`);
```

## Factory Function

```typescript
import { createClient } from '@setupranali/client';

const client = createClient({
  url: 'http://localhost:8080',
  apiKey: 'your-api-key'
});
```

## API Reference

### `client.health()`

Check server health.

```typescript
const health = await client.health();
console.log(health.status); // 'ok'
console.log(health.version); // '1.0.0'
```

### `client.datasets()`

List all available datasets.

```typescript
const datasets = await client.datasets();
datasets.forEach(ds => {
  console.log(`${ds.id}: ${ds.name}`);
});
```

### `client.dataset(id)`

Get details of a specific dataset.

```typescript
const dataset = await client.dataset('orders');
console.log(dataset.dimensions);
console.log(dataset.metrics);
```

### `client.query(options)`

Execute a semantic query.

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
```

### `client.graphql(query, variables?)`

Execute a GraphQL query.

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

## Error Handling

```typescript
import {
  SetuPranali,
  AuthenticationError,
  DatasetNotFoundError,
  QueryError,
  RateLimitError
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
  }
}
```

## TypeScript Support

Full TypeScript support with type definitions:

```typescript
import type {
  Dataset,
  QueryResult,
  QueryOptions,
  Filter
} from '@setupranali/client';

const options: QueryOptions = {
  dataset: 'orders',
  dimensions: ['city'],
  metrics: ['revenue']
};

const result: QueryResult<{ city: string; revenue: number }> = 
  await client.query(options);
```

## Configuration Options

```typescript
const client = new SetuPranali({
  url: 'https://api.example.com',  // Server URL
  apiKey: 'sk_live_xxx',           // API key
  timeout: 30000,                  // Request timeout (ms)
  headers: {                       // Additional headers
    'X-Custom-Header': 'value'
  }
});
```

## Browser Support

Works in modern browsers with `fetch` support:

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

## Node.js Support

Works in Node.js 18+ (native fetch) or with a fetch polyfill:

```javascript
// Node.js 18+
const { SetuPranali } = require('@setupranali/client');

// Node.js < 18
const fetch = require('node-fetch');
globalThis.fetch = fetch;
const { SetuPranali } = require('@setupranali/client');
```

## License

Apache 2.0 - See [LICENSE](../../LICENSE) for details.

