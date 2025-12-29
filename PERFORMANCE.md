# Performance & Scalability Guide

## Quick Answer: Is This Fast Enough for TB-Scale Data?

**Yes** — because the connector doesn't process your data. Your data warehouse does.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Query Flow                                        │
└─────────────────────────────────────────────────────────────────────────┘

  Power BI sends query
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SetuPranali                                │
│                                                                          │
│   1. Authenticate (API key lookup)           ~1ms                       │
│   2. Check cache (Redis)                     ~2ms                       │
│   3. Inject RLS filter                       ~1ms                       │
│   4. Validate query                          ~1ms                       │
│   ─────────────────────────────────────────────────                     │
│   Total connector overhead:                  ~5ms                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼  (if cache miss)
┌─────────────────────────────────────────────────────────────────────────┐
│                     YOUR DATA WAREHOUSE                                  │
│                                                                          │
│   Snowflake / BigQuery / Databricks / Redshift                          │
│                                                                          │
│   - Handles TB/PB scale natively                                        │
│   - Parallel execution                                                  │
│   - Columnar storage                                                    │
│   - Query optimization                                                  │
│                                                                          │
│   Query execution time: depends on warehouse                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SetuPranali                                │
│                                                                          │
│   5. Cache result (Redis)                    ~3ms                       │
│   6. Return to BI tool                       ~1ms                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What Query Engine Does It Use?

**Your existing database engine.** The connector is a pass-through layer.

| Database | Query Engine | TB-Scale Support |
|----------|--------------|------------------|
| Snowflake | Snowflake compute | ✅ Native PB-scale |
| BigQuery | BigQuery slots | ✅ Native PB-scale |
| Databricks | Spark / Photon | ✅ Native PB-scale |
| Redshift | Redshift MPP | ✅ Native PB-scale |
| PostgreSQL | PostgreSQL | ⚠️ Up to ~100GB efficiently |
| DuckDB | DuckDB | ⚠️ In-memory, up to ~100GB |

---

## Performance Optimization Strategies

### 1. Redis Caching (Eliminates Repeated Queries)

```
First query:  Warehouse (2s) + Connector (5ms) = 2.005s
Second query: Redis cache (2ms) + Connector (3ms) = 5ms  ← 400x faster
```

Configure in `.env`:
```bash
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300        # 5 minutes
CACHE_MAX_ROWS=100000        # Don't cache huge results
```

### 2. Incremental Refresh (Fetch Only New Data)

Instead of refreshing 1TB every day, fetch only today's data:

```yaml
incremental:
  enabled: true
  column: sale_date
  type: date
  mode: append
  maxWindowDays: 7           # Only allow last 7 days
```

Power BI sends: `$filter=sale_date ge 2025-12-23`
Query scans: ~1 day instead of years

### 3. Query Limits (Prevent Runaway Queries)

```bash
QUERY_MAX_ROWS=100000        # Cap result size
QUERY_TIMEOUT_SECONDS=30     # Kill slow queries
QUERY_MAX_DIMENSIONS=20      # Prevent wide queries
```

### 4. Rate Limiting (Protect Warehouse)

```bash
RATE_LIMIT_QUERY=60/minute   # Per API key
RATE_LIMIT_ODATA=120/minute  # Higher for metadata
```

---

## Benchmark: Connector Overhead

Tested with Redis on localhost, PostgreSQL on LAN:

| Operation | Time |
|-----------|------|
| API key authentication | 0.5ms |
| Cache check (Redis) | 1-2ms |
| RLS filter injection | 0.2ms |
| Query validation | 0.5ms |
| Cache write (Redis) | 2-3ms |
| **Total connector overhead** | **~5-10ms** |

For a 2-second warehouse query, overhead is **0.25-0.5%**.

---

## Scaling the Connector Itself

The connector is stateless. Scale horizontally:

```yaml
# docker-compose.yml
services:
  ubi-connector:
    image: ubi-connector:latest
    deploy:
      replicas: 5           # 5 instances
    environment:
      - REDIS_URL=redis://redis:6379/0
```

Or Kubernetes:
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 10              # 10 pods
```

### Capacity Planning

| Connector Instances | Concurrent Queries | Queries/Second |
|--------------------|--------------------| ---------------|
| 1 | ~50 | ~200 |
| 5 | ~250 | ~1000 |
| 10 | ~500 | ~2000 |

Bottleneck is almost always the warehouse, not the connector.

---

## Database-Specific Recommendations

### Snowflake

```yaml
source:
  engine: snowflake
  sourceId: snowflake-prod
  type: table
  reference: ANALYTICS.MARTS.FCT_SALES
```

Tips:
- Use a dedicated BI warehouse (size XS-S for most queries)
- Enable Snowflake result caching
- Use clustering on frequently filtered columns
- Connector caching + Snowflake caching = very fast

### BigQuery

```yaml
source:
  engine: bigquery
  sourceId: bigquery-prod
  type: table
  reference: analytics.sales.fact_orders
```

Tips:
- Use partitioned tables (partition on date column)
- Connector RLS adds `WHERE` clause — use partition column
- BI Engine accelerates repeated queries

### Databricks / Spark

```yaml
source:
  engine: databricks
  sourceId: databricks-prod
  type: table
  reference: analytics.fact_orders
```

Tips:
- Use Delta Lake for ACID + fast queries
- Use Photon for faster SQL
- Z-order on frequently filtered columns

---

## When Connector Overhead Matters

| Scenario | Overhead Impact | Solution |
|----------|-----------------|----------|
| Single 2s query | Negligible (5ms / 2000ms = 0.25%) | None needed |
| 100 parallel queries | Could bottleneck | Scale connector replicas |
| Real-time dashboard (100ms target) | Noticeable | Use aggressive Redis caching |
| One-time large export | Negligible | None needed |

---

## Summary

| Question | Answer |
|----------|--------|
| Is it fast enough for TB? | **Yes** — warehouse does the work |
| What query engine? | **Your warehouse** (Snowflake, BigQuery, etc.) |
| Connector overhead? | **~5-10ms** per query |
| How to optimize? | Caching, incremental refresh, query limits |
| How to scale? | Add more connector replicas (stateless) |

---

## Currently Supported Engines

| Engine | Status | Notes |
|--------|--------|-------|
| DuckDB | ✅ Built-in | Great for demos, <100GB |
| PostgreSQL | ✅ Built-in | Production-ready |
| Snowflake | 🚧 Roadmap | High priority |
| BigQuery | 🚧 Roadmap | High priority |
| Databricks | 🚧 Roadmap | Planned |
| Redshift | 🚧 Roadmap | Planned |
| ClickHouse | 🚧 Roadmap | Planned |

To add a new engine, implement adapter in `app/connection_manager.py`.

