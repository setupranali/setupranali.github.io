# Advanced API Features

Advanced API capabilities for streaming, batch queries, and JSON:API compliance.

---

## Streaming Responses

Stream large result sets without loading everything into memory.

### SSE (Server-Sent Events)

```bash
curl -N "http://localhost:8080/v1/stream" \
  -H "X-API-Key: your-key" \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "dimensions": ["order_date", "region"],
    "metrics": ["revenue", "order_count"],
    "format": "ndjson",
    "chunk_size": 1000
  }'
```

Response (SSE format):

```
event: metadata
data: {"stream_id":"stream_1703851200000","dataset":"orders","chunk_size":1000}

event: data
data: {"order_date":"2025-01-01","region":"US","revenue":15000,"order_count":120}

event: data
data: {"order_date":"2025-01-01","region":"EU","revenue":12000,"order_count":95}

event: progress
data: {"chunks_sent":1,"rows_sent":1000,"percent_complete":10.5}

event: complete
data: {"stream_id":"stream_1703851200000","total_chunks":10,"total_rows":9523}
```

### Stream Formats

| Format | Content-Type | Description |
|--------|--------------|-------------|
| `ndjson` | `application/x-ndjson` | Newline-delimited JSON (default) |
| `json` | `application/json` | JSON array chunks |
| `csv` | `text/csv` | CSV format |
| `sse` | `text/event-stream` | Server-Sent Events |

### WebSocket Streaming

```javascript
const ws = new WebSocket('ws://localhost:8080/v1/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'query',
    payload: {
      dataset: 'orders',
      dimensions: ['region'],
      metrics: ['revenue'],
      chunk_size: 500
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'stream_started':
      console.log('Streaming:', message.stream_id);
      break;
    case 'data':
      console.log('Chunk:', message.chunk_number, message.rows);
      break;
    case 'complete':
      console.log('Done:', message.total_rows, 'rows');
      break;
    case 'error':
      console.error('Error:', message.message);
      break;
  }
};
```

### Python Streaming

```python
import httpx

async def stream_query():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'POST',
            'http://localhost:8080/v1/stream',
            headers={'X-API-Key': 'your-key'},
            json={
                'dataset': 'orders',
                'dimensions': ['region'],
                'metrics': ['revenue'],
                'format': 'ndjson'
            }
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)
```

### Stream Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `format` | `ndjson` | Output format |
| `chunk_size` | `1000` | Rows per chunk |
| `include_metadata` | `true` | Include stream metadata |
| `include_progress` | `true` | Include progress updates |

---

## Batch Queries

Execute multiple queries in a single request.

### Basic Batch

```bash
curl -X POST "http://localhost:8080/v1/batch" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      {
        "id": "daily_revenue",
        "dataset": "orders",
        "dimensions": ["order_date"],
        "metrics": ["revenue"]
      },
      {
        "id": "regional_sales",
        "dataset": "orders",
        "dimensions": ["region"],
        "metrics": ["order_count"]
      },
      {
        "id": "top_products",
        "dataset": "products",
        "dimensions": ["product_name"],
        "metrics": ["sales"],
        "limit": 10
      }
    ],
    "parallel": true
  }'
```

Response:

```json
{
  "batch_id": "batch_1703851200000",
  "success": true,
  "summary": {
    "total": 3,
    "successful": 3,
    "failed": 0
  },
  "results": {
    "daily_revenue": {
      "success": true,
      "data": [
        {"order_date": "2025-01-01", "revenue": 45000},
        {"order_date": "2025-01-02", "revenue": 52000}
      ],
      "rows": 365,
      "cache_hit": true,
      "duration_ms": 45.2
    },
    "regional_sales": {
      "success": true,
      "data": [
        {"region": "US", "order_count": 15000},
        {"region": "EU", "order_count": 12000}
      ],
      "rows": 5,
      "cache_hit": false,
      "duration_ms": 120.5
    },
    "top_products": {
      "success": true,
      "data": [...],
      "rows": 10,
      "cache_hit": false,
      "duration_ms": 85.3
    }
  },
  "metadata": {
    "started_at": "2025-12-29T10:30:00.000Z",
    "completed_at": "2025-12-29T10:30:00.250Z",
    "total_duration_ms": 250.5,
    "execution_order": ["daily_revenue", "regional_sales", "top_products"],
    "parallel_groups": [["daily_revenue", "regional_sales", "top_products"]]
  }
}
```

### Query Dependencies

Execute queries that depend on results from previous queries:

```json
{
  "queries": [
    {
      "id": "top_regions",
      "dataset": "orders",
      "dimensions": ["region"],
      "metrics": ["revenue"],
      "order_by": ["-revenue"],
      "limit": 3
    },
    {
      "id": "top_region_products",
      "dataset": "orders",
      "dimensions": ["product_category"],
      "metrics": ["revenue"],
      "filters": {
        "region": "$ref:top_regions[0].region"
      },
      "depends_on": ["top_regions"]
    }
  ]
}
```

### Mixed Operations

Combine different operation types:

```json
{
  "queries": [
    {
      "id": "semantic_query",
      "operation": "query",
      "dataset": "orders",
      "dimensions": ["region"],
      "metrics": ["revenue"]
    },
    {
      "id": "sql_query",
      "operation": "sql",
      "sql": "SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"
    },
    {
      "id": "nl_query",
      "operation": "nlq",
      "question": "What was total revenue last month?"
    },
    {
      "id": "schema_info",
      "operation": "introspect",
      "introspect_type": "datasets"
    }
  ]
}
```

### Batch Options

| Option | Default | Description |
|--------|---------|-------------|
| `parallel` | `true` | Execute queries in parallel |
| `stop_on_error` | `false` | Stop on first error |
| `transaction` | `false` | Execute as transaction |
| `include_metadata` | `true` | Include timing metadata |

### Error Handling

```json
{
  "batch_id": "batch_1703851200000",
  "success": false,
  "summary": {
    "total": 3,
    "successful": 2,
    "failed": 1
  },
  "results": {
    "query1": {
      "success": true,
      "data": [...]
    },
    "query2": {
      "success": false,
      "error": "Dataset 'invalid' not found",
      "error_code": "ERR_2001"
    },
    "query3": {
      "success": true,
      "data": [...]
    }
  }
}
```

---

## JSON:API Compliance

Standardized REST responses following [JSON:API v1.1](https://jsonapi.org/).

### Enable JSON:API Format

```bash
curl "http://localhost:8080/v1/datasets" \
  -H "X-API-Key: your-key" \
  -H "Accept: application/vnd.api+json"
```

Response:

```json
{
  "jsonapi": {"version": "1.1"},
  "data": [
    {
      "type": "dataset",
      "id": "orders",
      "attributes": {
        "name": "Orders",
        "description": "Order-level facts",
        "tags": ["sales", "core"]
      },
      "relationships": {
        "dimensions": {
          "data": [
            {"type": "dimension", "id": "orders_dim_order_date"},
            {"type": "dimension", "id": "orders_dim_region"}
          ]
        },
        "metrics": {
          "data": [
            {"type": "metric", "id": "orders_met_revenue"},
            {"type": "metric", "id": "orders_met_order_count"}
          ]
        }
      },
      "links": {
        "self": "/v1/datasets/orders"
      }
    }
  ],
  "links": {
    "self": "/v1/datasets?page[number]=1&page[size]=25",
    "first": "/v1/datasets?page[number]=1&page[size]=25",
    "last": "/v1/datasets?page[number]=1&page[size]=25"
  },
  "meta": {
    "total": 5,
    "page": 1,
    "pageSize": 25,
    "totalPages": 1
  }
}
```

### Pagination

```bash
# Page-based pagination
curl "http://localhost:8080/v1/datasets?page[number]=2&page[size]=10"

# Or simple style
curl "http://localhost:8080/v1/datasets?page=2&limit=10"
```

### Sorting

```bash
# Sort ascending
curl "http://localhost:8080/v1/query?sort=order_date"

# Sort descending
curl "http://localhost:8080/v1/query?sort=-revenue"

# Multiple fields
curl "http://localhost:8080/v1/query?sort=-revenue,order_date"
```

### Filtering

```bash
# Filter by field
curl "http://localhost:8080/v1/query?filter[region]=US"

# Multiple filters
curl "http://localhost:8080/v1/query?filter[region]=US&filter[status]=completed"
```

### Sparse Fieldsets

Request only specific attributes:

```bash
curl "http://localhost:8080/v1/datasets?fields[dataset]=name,description"
```

### Including Related Resources

```bash
curl "http://localhost:8080/v1/datasets/orders?include=dimensions,metrics"
```

Response:

```json
{
  "data": {
    "type": "dataset",
    "id": "orders",
    "attributes": {...},
    "relationships": {...}
  },
  "included": [
    {
      "type": "dimension",
      "id": "orders_dim_order_date",
      "attributes": {
        "name": "order_date",
        "type": "date"
      }
    },
    {
      "type": "metric",
      "id": "orders_met_revenue",
      "attributes": {
        "name": "revenue",
        "type": "number",
        "aggregation": "sum"
      }
    }
  ]
}
```

### JSON:API Errors

```json
{
  "jsonapi": {"version": "1.1"},
  "errors": [
    {
      "id": "abc123def456",
      "status": "404",
      "code": "ERR_2001",
      "title": "Not Found",
      "detail": "Dataset 'invalid' not found",
      "source": {
        "parameter": "dataset"
      },
      "meta": {
        "suggestion": "Check that 'invalid' is defined in catalog.yaml"
      }
    }
  ]
}
```

### Query Results in JSON:API

```bash
curl -X POST "http://localhost:8080/v1/query" \
  -H "Accept: application/vnd.api+json" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "dimensions": ["region"], "metrics": ["revenue"]}'
```

Response:

```json
{
  "jsonapi": {"version": "1.1"},
  "data": [
    {
      "type": "orders_result",
      "id": "abc123",
      "attributes": {
        "region": "US",
        "revenue": 150000
      },
      "meta": {"index": 0}
    },
    {
      "type": "orders_result",
      "id": "def456",
      "attributes": {
        "region": "EU",
        "revenue": 120000
      },
      "meta": {"index": 1}
    }
  ],
  "meta": {
    "dataset": "orders",
    "dimensions": ["region"],
    "metrics": ["revenue"],
    "cacheHit": true,
    "durationMs": 45.2,
    "total": 5
  },
  "links": {
    "self": "/v1/query?page[number]=1&page[size]=25"
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAM_ENABLED` | `true` | Enable streaming |
| `STREAM_CHUNK_SIZE` | `1000` | Default chunk size |
| `STREAM_MAX_ROWS` | `1000000` | Max streaming rows |
| `STREAM_TIMEOUT` | `300` | Stream timeout (seconds) |
| `BATCH_ENABLED` | `true` | Enable batch queries |
| `BATCH_MAX_QUERIES` | `20` | Max queries per batch |
| `BATCH_MAX_PARALLEL` | `5` | Max parallel executions |
| `BATCH_TIMEOUT` | `300` | Batch timeout (seconds) |
| `JSONAPI_ENABLED` | `true` | Enable JSON:API |
| `JSONAPI_DEFAULT_PAGE_SIZE` | `25` | Default page size |
| `JSONAPI_MAX_PAGE_SIZE` | `1000` | Max page size |

### Helm Configuration

```yaml
# values.yaml
api:
  streaming:
    enabled: true
    chunkSize: 1000
    maxRows: 1000000
    timeoutSeconds: 300
  
  batch:
    enabled: true
    maxQueries: 20
    maxParallel: 5
    timeoutSeconds: 300
  
  jsonapi:
    enabled: true
    defaultPageSize: 25
    maxPageSize: 1000
```

---

## Best Practices

### Streaming

1. **Use for large datasets**: Stream when expecting >10,000 rows
2. **Choose right format**: NDJSON for processing, CSV for exports
3. **Handle disconnects**: Implement retry logic for long streams
4. **Monitor progress**: Use progress events for UI feedback

### Batch Queries

1. **Group related queries**: Reduce HTTP overhead
2. **Use dependencies wisely**: Only when results are needed
3. **Enable parallel**: Default parallel=true for speed
4. **Handle partial failures**: Check individual query success

### JSON:API

1. **Use sparse fieldsets**: Request only needed fields
2. **Include related resources**: Reduce additional requests
3. **Implement pagination**: Use cursor for large datasets
4. **Follow spec**: Use proper Content-Type headers

