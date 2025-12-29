# Minimal Quick Start Example

The simplest possible SetuPranali setup - get running in under 2 minutes!

## What This Example Does

- Uses **SQLite** (no database setup required)
- Creates a simple **orders** dataset
- Tests with **REST API**

## Prerequisites

- Docker installed
- curl (for testing)

## Quick Start

### 1. Start SetuPranali

```bash
docker-compose up -d
```

### 2. Verify It's Running

```bash
curl http://localhost:8080/v1/health
```

Expected response:
```json
{"status": "healthy", "version": "1.3.0"}
```

### 3. List Available Datasets

```bash
curl http://localhost:8080/v1/datasets \
  -H "Authorization: Bearer demo_api_key"
```

### 4. Run Your First Query

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer demo_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "dimensions": ["order_date", "status"],
    "metrics": ["total_revenue", "order_count"]
  }'
```

### 5. Try Natural Language Query

```bash
curl -X POST http://localhost:8080/v1/nlq \
  -H "Authorization: Bearer demo_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the total revenue by status?"
  }'
```

## Files in This Example

| File | Purpose |
|------|---------|
| `docker-compose.yml` | One-command startup |
| `catalog.yaml` | SetuPranali configuration |
| `data/orders.db` | Sample SQLite database |
| `queries/` | Example query files |

## What's Next?

1. **Connect a BI Tool**: See [Power BI](../../by-bi-tool/powerbi/) or [Tableau](../../by-bi-tool/tableau/)
2. **Use Your Database**: See [PostgreSQL](../../by-source/postgresql/) or [MySQL](../../by-source/mysql/)
3. **Add Security**: See [Multi-tenant example](../../use-cases/multi-tenant/)

## Cleanup

```bash
docker-compose down -v
```

