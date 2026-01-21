# Recent Queries API Documentation

## Endpoint: GET /v1/analytics/recent-queries

Get recent query execution records from DuckDB storage.

### Authentication
Requires API key in header: `X-API-Key: <your-api-key>`

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Number of queries to return (max: 100) |
| `dataset` | string | optional | Filter by dataset name |
| `tenant_id` | string | optional | Filter by tenant ID (admin only) |

### Response Format

```json
{
  "items": [
    {
      "query_id": "uuid-string",
      "dataset": "orders",
      "tenant_id": "default",
      "dimensions": ["order_date", "city"],
      "metrics": ["total_revenue"],
      "duration_ms": 45.2,
      "duration": "45ms",
      "rows_returned": 100,
      "cache_hit": false,
      "success": true,
      "status": "success",
      "error_code": null,
      "error_message": null,
      "timestamp": "2025-01-20T10:30:00Z",
      "source_ip": "127.0.0.1"
    }
  ],
  "total": 1,
  "limit": 10
}
```

### Status Values

- `"success"`: Query completed successfully and quickly (< 1 second)
- `"warning"`: Query completed but took > 1 second
- `"error"`: Query failed with an error

### Example Requests

#### Get last 10 queries
```bash
curl -X GET "http://localhost:8080/v1/analytics/recent-queries?limit=10" \
  -H "X-API-Key: dev-key-123"
```

#### Get last 5 queries for a specific dataset
```bash
curl -X GET "http://localhost:8080/v1/analytics/recent-queries?limit=5&dataset=orders" \
  -H "X-API-Key: dev-key-123"
```

#### Get recent queries for a tenant (admin only)
```bash
curl -X GET "http://localhost:8080/v1/analytics/recent-queries?limit=20&tenant_id=tenantA" \
  -H "X-API-Key: admin-key"
```

### Alternative: Get from Analytics Endpoint

Recent queries are also included in the main analytics endpoint:

```bash
GET /v1/analytics?hours=24
```

This returns:
```json
{
  "query_volume": [...],
  "latency": [...],
  "recent_queries": [...],  // Last 5 queries
  "stats": {...}
}
```

### Data Source

Queries are stored in DuckDB at: `app/db/state.db` in the `query_records` table.

### Notes

- Queries are ordered by timestamp (most recent first)
- Non-admin users can only see queries for their own tenant
- Maximum limit is 100 queries per request
- Data persists across server restarts (stored in DuckDB)
