# TimescaleDB

Connect SetuPranali to TimescaleDB for time-series analytics, IoT data, and real-time monitoring.

---

## Overview

**TimescaleDB** is ideal for:

- Time-series data and IoT analytics
- Real-time monitoring and observability
- Financial tick data and metrics
- Sensor data and telemetry
- Log analytics and events

!!! info "PostgreSQL Compatible"
    TimescaleDB is a PostgreSQL extension - all PostgreSQL features work seamlessly!

---

## Prerequisites

Install the PostgreSQL Python driver:

```bash
pip install psycopg2-binary
# or for better performance:
pip install psycopg[binary]
```

---

## Configuration

### Register via API

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-timescale",
    "type": "timescaledb",
    "connection": {
      "host": "timescale.company.com",
      "database": "metrics",
      "user": "analytics",
      "password": "secret"
    }
  }'
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `host` | ✅ | - | Server hostname or IP |
| `port` | | `5432` | Server port |
| `database` | ✅ | - | Database name |
| `user` | ✅ | - | Username |
| `password` | ✅ | - | Password |
| `schema` | | `public` | Default schema |
| `sslmode` | | `prefer` | SSL mode (disable, allow, prefer, require) |
| `connect_timeout` | | `30` | Connection timeout (seconds) |
| `application_name` | | `SetuPranali` | Application identifier |
| `compression_enabled` | | `true` | Query compressed chunks |

---

## Examples

### Self-Hosted TimescaleDB

```json
{
  "name": "timescale-metrics",
  "type": "timescaledb",
  "connection": {
    "host": "timescale.company.com",
    "port": 5432,
    "database": "metrics",
    "user": "analytics",
    "password": "secure_password"
  }
}
```

### Timescale Cloud

```json
{
  "name": "timescale-cloud",
  "type": "tsdb",
  "connection": {
    "host": "xxx.tsdb.cloud.timescale.com",
    "port": 5432,
    "database": "tsdb",
    "user": "tsdbadmin",
    "password": "secure_password",
    "sslmode": "require"
  }
}
```

### With SSL Certificate

```json
{
  "name": "timescale-ssl",
  "type": "timescaledb",
  "connection": {
    "host": "timescale.company.com",
    "database": "metrics",
    "user": "analytics",
    "password": "secure_password",
    "sslmode": "verify-full",
    "sslrootcert": "/path/to/ca.crt"
  }
}
```

---

## Dataset Configuration

### Time-Series Dataset

```yaml
datasets:
  - id: sensor_metrics
    name: Sensor Metrics
    description: IoT sensor data from TimescaleDB
    source: my-timescale
    table: sensor_data
    dimensions:
      - name: device_id
        expr: device_id
      - name: location
        expr: location
      - name: time
        expr: time
        type: timestamp
    metrics:
      - name: avg_temperature
        expr: "AVG(temperature)"
      - name: max_temperature
        expr: "MAX(temperature)"
      - name: readings
        expr: "COUNT(*)"
    rls:
      mode: tenant_column
      field: tenant_id
```

### Using Continuous Aggregates

```yaml
datasets:
  - id: hourly_metrics
    name: Hourly Metrics
    description: Pre-aggregated hourly metrics
    source: my-timescale
    table: hourly_metrics_view  # Continuous aggregate
    dimensions:
      - name: device_id
      - name: bucket
        expr: bucket
        type: timestamp
    metrics:
      - name: avg_value
        expr: "AVG(avg_value)"
      - name: total_readings
        expr: "SUM(count)"
```

### Using time_bucket

```yaml
datasets:
  - id: bucketed_metrics
    name: Bucketed Metrics
    source: my-timescale
    sql: |
      SELECT 
        time_bucket('1 hour', time) AS hour,
        device_id,
        AVG(value) AS avg_value,
        COUNT(*) AS readings
      FROM sensor_data
      WHERE time > NOW() - INTERVAL '7 days'
      GROUP BY hour, device_id
    dimensions:
      - name: hour
        type: timestamp
      - name: device_id
    metrics:
      - name: avg_value
      - name: readings
```

---

## TimescaleDB Features

### Hypertables

Hypertables automatically partition time-series data:

```sql
-- Create a hypertable
SELECT create_hypertable('sensor_data', 'time');

-- View hypertables
SELECT * FROM timescaledb_information.hypertables;
```

### Continuous Aggregates

Pre-compute aggregations for fast queries:

```sql
-- Create continuous aggregate
CREATE MATERIALIZED VIEW hourly_metrics
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    device_id,
    AVG(value) AS avg_value,
    COUNT(*) AS count
FROM sensor_data
GROUP BY bucket, device_id;

-- Add refresh policy
SELECT add_continuous_aggregate_policy('hourly_metrics',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### Compression

Reduce storage with compression:

```sql
-- Enable compression
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id'
);

-- Add compression policy
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
```

### Data Retention

Automatically drop old data:

```sql
-- Add retention policy
SELECT add_retention_policy('sensor_data', INTERVAL '90 days');
```

---

## Performance Tips

### 1. Use Continuous Aggregates

Pre-aggregate data for common query patterns:

```sql
CREATE MATERIALIZED VIEW daily_summary
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS day,
    COUNT(*),
    AVG(value)
FROM metrics
GROUP BY day;
```

### 2. Enable Compression

Compress old chunks:

```sql
SELECT add_compression_policy('metrics', INTERVAL '7 days');
```

### 3. Proper Chunk Intervals

Size chunks appropriately (1-2 days of data per chunk):

```sql
SELECT set_chunk_time_interval('metrics', INTERVAL '1 day');
```

### 4. Use time_bucket for Grouping

```sql
SELECT 
    time_bucket('1 hour', time) AS hour,
    AVG(value)
FROM metrics
WHERE time > NOW() - INTERVAL '1 day'
GROUP BY hour;
```

### 5. Enable Query Caching

```yaml
# values.yaml (Helm)
config:
  cache:
    enabled: true
    ttl: 60  # Short TTL for real-time data
```

---

## Troubleshooting

### Extension Not Found

```
WARNING: TimescaleDB extension not found
```

**Solutions:**
1. Install TimescaleDB extension: `CREATE EXTENSION timescaledb;`
2. Verify package is installed on server
3. Check user has permissions

### Slow Queries

**Solutions:**
1. Use continuous aggregates for common patterns
2. Add indexes on frequently filtered columns
3. Check chunk sizes aren't too large
4. Enable compression on old data
5. Use `EXPLAIN ANALYZE` to debug

### Out of Memory

**Solutions:**
1. Reduce `work_mem` for parallel queries
2. Limit concurrent connections
3. Use streaming aggregates
4. Reduce chunk size

### Connection Timeout

**Solutions:**
1. Increase `connect_timeout`
2. Check network connectivity
3. Verify firewall rules
4. For cloud, ensure IP is whitelisted

---

## Security

### Row-Level Security

```yaml
datasets:
  - id: sensor_data
    rls:
      mode: tenant_column
      field: tenant_id
```

### Minimal Permissions

```sql
-- Create read-only user
CREATE USER bi_reader WITH PASSWORD 'secure_password';

-- Grant access
GRANT CONNECT ON DATABASE metrics TO bi_reader;
GRANT USAGE ON SCHEMA public TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_reader;

-- For hypertable chunks
GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_internal TO bi_reader;
```

---

## CLI Usage

```bash
# Add TimescaleDB source
setupranali sources add \
  --name my-timescale \
  --type timescaledb \
  --config '{"host":"timescale.example.com","database":"metrics","user":"analytics","password":"secret"}'

# Test connection
setupranali sources test my-timescale

# Query
setupranali query sensor_metrics -d device_id -m avg_temperature
```

---

## API Examples

### Query via REST

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sensor_metrics",
    "dimensions": ["device_id"],
    "metrics": ["avg_temperature", "readings"],
    "filters": [
      {"dimension": "time", "operator": ">=", "value": "2024-01-01"}
    ],
    "limit": 100
  }'
```

### SQL with Time Functions

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT time_bucket('\''1 hour'\'', time) AS hour, device_id, AVG(value) FROM sensor_data WHERE time > NOW() - INTERVAL '\''1 day'\'' GROUP BY hour, device_id",
    "dataset": "sensor_metrics"
  }'
```

---

## Comparison with ClickHouse

| Feature | TimescaleDB | ClickHouse |
|---------|-------------|------------|
| **Base** | PostgreSQL | Custom engine |
| **SQL Compatibility** | Full PostgreSQL | ClickHouse SQL |
| **Best For** | Time-series with relations | Pure analytics |
| **Compression** | Good | Excellent |
| **JOINs** | Full support | Limited |
| **Updates/Deletes** | Full support | Limited |
| **Learning Curve** | Low (PostgreSQL) | Medium |

---

## Type Aliases

| Alias | Use Case |
|-------|----------|
| `timescaledb` | Standard TimescaleDB |
| `timescale` | Alternative name |
| `tsdb` | Short alias |

