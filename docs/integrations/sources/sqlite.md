# SQLite

Connect SetuPranali to SQLite databases for local development, testing, and embedded analytics.

---

## Overview

**SQLite** is ideal for:

- Local development and testing
- Single-file embedded databases
- Edge computing and IoT devices
- Mobile and desktop applications
- Quick prototyping and demos

!!! success "Zero Dependencies"
    SQLite is built into Python's standard library - no additional installation required!

---

## Prerequisites

None! SQLite support is included in Python by default.

```bash
# Verify SQLite is available
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

---

## Configuration

### Register via API

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-sqlite",
    "type": "sqlite",
    "connection": {
      "database": "/path/to/data.db"
    }
  }'
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `database` | ✅ | - | Path to SQLite file or `:memory:` |
| `read_only` | | `true` | Open in read-only mode |
| `timeout` | | `30` | Connection timeout (seconds) |
| `journal_mode` | | `WAL` | WAL, DELETE, TRUNCATE, PERSIST, MEMORY, OFF |
| `cache_size` | | `2000` | Page cache size in KB |
| `foreign_keys` | | `true` | Enable foreign key constraints |
| `check_same_thread` | | `false` | Allow multi-threaded access |
| `isolation_level` | | `None` | Transaction isolation level |
| `create` | | `false` | Create database if not exists |
| `extensions` | | `[]` | List of extensions to load |

---

## Examples

### File-Based Database

```json
{
  "name": "analytics-db",
  "type": "sqlite",
  "connection": {
    "database": "/data/analytics.db"
  }
}
```

### In-Memory Database

```json
{
  "name": "memory-db",
  "type": "sqlite",
  "connection": {
    "database": ":memory:"
  }
}
```

### Read-Write Access

```json
{
  "name": "writable-db",
  "type": "sqlite",
  "connection": {
    "database": "/data/app.db",
    "read_only": false
  }
}
```

### High-Performance Settings

```json
{
  "name": "fast-db",
  "type": "sqlite",
  "connection": {
    "database": "/data/large.db",
    "journal_mode": "WAL",
    "cache_size": 10000
  }
}
```

### With Extensions

```json
{
  "name": "geo-db",
  "type": "sqlite",
  "connection": {
    "database": "/data/geo.db",
    "extensions": ["/usr/lib/mod_spatialite.so"]
  }
}
```

---

## Dataset Configuration

### catalog.yaml Example

```yaml
datasets:
  - id: orders
    name: Orders
    description: Order data from SQLite
    source: my-sqlite
    table: orders
    dimensions:
      - name: status
        expr: status
      - name: customer_id
        expr: customer_id
      - name: date
        expr: order_date
        type: date
    metrics:
      - name: total
        expr: "SUM(amount)"
      - name: count
        expr: "COUNT(*)"
      - name: avg_value
        expr: "AVG(amount)"
    rls:
      mode: tenant_column
      field: tenant_id
```

### Using Views

```yaml
datasets:
  - id: sales_summary
    source: my-sqlite
    table: v_sales_summary  # SQLite view
    dimensions:
      - name: region
      - name: product
    metrics:
      - name: revenue
        expr: "SUM(revenue)"
```

---

## Use Cases

### Local Development

Use SQLite for local development with the same schema as production:

```bash
# Export production data sample
pg_dump -t orders production_db | sqlite3 local.db

# Configure SetuPranali
setupranali sources add \
  --name local-dev \
  --type sqlite \
  --config '{"database":"local.db"}'
```

### Testing

Create test fixtures with in-memory SQLite:

```json
{
  "name": "test-db",
  "type": "sqlite",
  "connection": {
    "database": ":memory:"
  }
}
```

### Edge Analytics

Deploy SetuPranali at the edge with embedded SQLite:

```yaml
# Docker Compose for edge
services:
  setupranali:
    image: adeygifting/connector
    volumes:
      - ./data:/data
    environment:
      - UBI_DEFAULT_SOURCE=edge-db
```

---

## Performance Tips

### 1. Use WAL Mode

WAL (Write-Ahead Logging) allows concurrent reads:

```json
{
  "journal_mode": "WAL"
}
```

### 2. Increase Cache Size

For large databases:

```json
{
  "cache_size": 10000
}
```

### 3. Read-Only Mode

Always use read-only for analytics:

```json
{
  "read_only": true
}
```

### 4. Enable Query Caching

```yaml
# values.yaml (Helm)
config:
  cache:
    enabled: true
    ttl: 300
```

### 5. Analyze Tables

Keep optimizer statistics updated:

```sql
ANALYZE;
```

---

## Troubleshooting

### Database is Locked

```
sqlite3.OperationalError: database is locked
```

**Solutions:**
1. Increase timeout: `"timeout": 60`
2. Use WAL mode: `"journal_mode": "WAL"`
3. Close other connections to the database
4. Check for long-running transactions

### Read-Only Filesystem

```
sqlite3.OperationalError: attempt to write a readonly database
```

**Solutions:**
1. Ensure `read_only: true` is set
2. Check file permissions
3. Verify the directory is writable (for WAL mode)

### Database Not Found

```
ConnectionError: Database file not found
```

**Solutions:**
1. Check the path is correct
2. Use absolute paths for reliability
3. Set `create: true` to create new databases

### Corrupted Database

**Solutions:**
1. Run integrity check: `PRAGMA integrity_check;`
2. Restore from backup
3. Try recovery: `sqlite3 corrupt.db ".recover" | sqlite3 recovered.db`

---

## Security

### Row-Level Security

SetuPranali automatically applies RLS:

```yaml
datasets:
  - id: orders
    rls:
      mode: tenant_column
      field: tenant_id
```

### File Permissions

Secure your SQLite files:

```bash
# Set restrictive permissions
chmod 600 /data/analytics.db

# Set owner
chown app:app /data/analytics.db
```

### Read-Only Mode

Always use read-only for BI workloads:

```json
{
  "read_only": true
}
```

---

## CLI Usage

```bash
# Add SQLite source
setupranali sources add \
  --name my-sqlite \
  --type sqlite \
  --config '{"database":"/data/analytics.db"}'

# Test connection
setupranali sources test my-sqlite

# List tables
setupranali introspect my-sqlite --tables

# Query
setupranali query orders -d status -m count
```

---

## API Examples

### Query via REST

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "orders",
    "dimensions": ["status"],
    "metrics": ["total", "count"],
    "limit": 100
  }'
```

### SQL Query

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status",
    "dataset": "orders"
  }'
```

---

## Comparison with DuckDB

| Feature | SQLite | DuckDB |
|---------|--------|--------|
| **Best For** | OLTP, small datasets | OLAP, analytics |
| **File Size Limit** | 281 TB (theoretical) | Unlimited |
| **Concurrent Reads** | Yes (WAL mode) | Yes |
| **Columnar Storage** | No | Yes |
| **Analytical Queries** | Slower | Optimized |
| **Dependencies** | None (built-in) | Requires install |

**Recommendation**: Use DuckDB for analytics workloads, SQLite for development and testing.

---

## Type Aliases

| Alias | Use Case |
|-------|----------|
| `sqlite` | Standard SQLite |
| `sqlite3` | Alternative name |

