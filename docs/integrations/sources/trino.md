# Trino / Presto

Connect SetuPranali to Trino or Presto for federated SQL queries across multiple data sources.

---

## Overview

**Trino** (formerly PrestoSQL) and **Presto** are distributed SQL query engines optimized for:

- Interactive analytics on large datasets
- Federated queries across multiple data sources
- Data lake analytics (HDFS, S3, Azure Blob)
- Real-time data exploration

!!! info "Trino vs Presto"
    Trino is the community fork of PrestoSQL. Both are supported by SetuPranali.
    Use `mode: trino` (default) or `mode: presto` in your configuration.

---

## Prerequisites

Install the Trino Python client:

```bash
# For Trino (recommended)
pip install trino

# For legacy Presto
pip install presto-python-client
```

---

## Configuration

### Register via API

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-trino",
    "type": "trino",
    "connection": {
      "host": "trino.example.com",
      "port": 8443,
      "user": "analyst",
      "password": "secret",
      "catalog": "hive",
      "schema": "default",
      "http_scheme": "https"
    }
  }'
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `host` | ✅ | - | Trino/Presto coordinator host |
| `port` | | `8080` / `8443` | Coordinator port |
| `user` | ✅ | - | Username |
| `password` | | - | Password for basic auth |
| `catalog` | ✅ | - | Default catalog |
| `schema` | | `default` | Default schema |
| `mode` | | `trino` | Engine mode: `trino` or `presto` |
| `http_scheme` | | `https` | `http` or `https` |
| `source` | | `setupranali` | Query source identifier |
| `auth_type` | | `basic` | Auth type: `none`, `basic`, `jwt` |
| `jwt_token` | | - | JWT token (for jwt auth) |
| `verify_ssl` | | `true` | Verify SSL certificates |
| `request_timeout` | | `30` | Request timeout (seconds) |
| `query_timeout` | | `300` | Query timeout (seconds) |

---

## Examples

### Basic Trino Connection

```json
{
  "name": "trino-analytics",
  "type": "trino",
  "connection": {
    "host": "trino.company.com",
    "port": 8443,
    "user": "bi_user",
    "password": "secure_password",
    "catalog": "hive",
    "schema": "analytics",
    "http_scheme": "https"
  }
}
```

### Presto Mode

```json
{
  "name": "presto-legacy",
  "type": "presto",
  "connection": {
    "host": "presto.company.com",
    "port": 8080,
    "user": "analyst",
    "catalog": "hive",
    "schema": "default",
    "mode": "presto"
  }
}
```

### JWT Authentication

```json
{
  "name": "trino-jwt",
  "type": "trino",
  "connection": {
    "host": "trino.company.com",
    "port": 8443,
    "user": "service_account",
    "catalog": "iceberg",
    "schema": "analytics",
    "http_scheme": "https",
    "auth_type": "jwt",
    "jwt_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### No Authentication (Development)

```json
{
  "name": "trino-dev",
  "type": "trino",
  "connection": {
    "host": "localhost",
    "port": 8080,
    "user": "developer",
    "catalog": "memory",
    "schema": "default",
    "http_scheme": "http",
    "auth_type": "none",
    "verify_ssl": false
  }
}
```

---

## Dataset Configuration

### catalog.yaml Example

```yaml
datasets:
  - id: sales
    name: Sales Analytics
    description: Sales data from data lake
    source: my-trino
    table: hive.analytics.fact_sales
    dimensions:
      - name: region
        expr: region_name
      - name: product
        expr: product_category
      - name: date
        expr: sale_date
        type: date
    metrics:
      - name: revenue
        expr: "SUM(amount)"
      - name: orders
        expr: "COUNT(*)"
      - name: avg_order_value
        expr: "AVG(amount)"
    rls:
      mode: tenant_column
      field: tenant_id
```

### Cross-Catalog Queries

Trino supports querying across multiple catalogs:

```yaml
datasets:
  - id: unified_customers
    name: Unified Customer View
    source: my-trino
    # Join data from multiple catalogs
    sql: |
      SELECT 
        c.customer_id,
        c.name,
        c.email,
        p.total_purchases,
        s.support_tickets
      FROM hive.customers.customer c
      LEFT JOIN postgresql.sales.customer_summary p 
        ON c.customer_id = p.customer_id
      LEFT JOIN mysql.support.ticket_counts s
        ON c.customer_id = s.customer_id
    dimensions:
      - name: customer_id
      - name: name
      - name: email
    metrics:
      - name: total_purchases
      - name: support_tickets
```

---

## Catalogs and Connectors

Trino supports many catalogs/connectors:

| Catalog Type | Use Case |
|--------------|----------|
| `hive` | Hive Metastore (HDFS, S3) |
| `iceberg` | Apache Iceberg tables |
| `delta` | Delta Lake |
| `postgresql` | PostgreSQL databases |
| `mysql` | MySQL databases |
| `mongodb` | MongoDB collections |
| `elasticsearch` | Elasticsearch indices |
| `kafka` | Kafka topics |
| `memory` | In-memory (testing) |

### Example: Multiple Catalogs

```yaml
# Register Trino with access to multiple catalogs
connection:
  host: trino.company.com
  catalog: hive  # Default catalog
  schema: default

# Query across catalogs in your datasets
datasets:
  - id: data_lake_sales
    source: my-trino
    table: hive.analytics.sales  # Hive catalog
    
  - id: operational_orders
    source: my-trino
    table: postgresql.orders.order_summary  # PostgreSQL catalog
```

---

## Performance Tips

### 1. Use Appropriate Catalogs

```sql
-- Good: Use Hive/Iceberg for large scans
SELECT region, SUM(amount) FROM hive.analytics.sales GROUP BY region

-- Good: Use PostgreSQL for small lookups
SELECT * FROM postgresql.dims.regions WHERE active = true
```

### 2. Enable Caching

```yaml
# values.yaml (Helm)
config:
  cache:
    enabled: true
    ttl: 300  # 5 minutes
```

### 3. Limit Result Sets

```yaml
datasets:
  - id: sales
    # ...
    defaultLimit: 10000
```

### 4. Use Partitioning

```yaml
datasets:
  - id: sales
    source: my-trino
    table: hive.analytics.fact_sales
    incremental:
      enabled: true
      column: sale_date
      partitionField: sale_date
```

---

## Troubleshooting

### Connection Refused

```
ConnectionError: Failed to connect to Trino
```

**Solutions:**
1. Verify host and port are correct
2. Check firewall rules
3. Verify Trino coordinator is running

### Authentication Failed

```
QueryError: Authentication failed
```

**Solutions:**
1. Check username and password
2. Verify auth_type matches server config
3. For JWT, ensure token is not expired

### Catalog Not Found

```
QueryError: Catalog 'xyz' not found
```

**Solutions:**
1. List available catalogs: `SHOW CATALOGS`
2. Check catalog configuration in Trino
3. Verify user has access to the catalog

### Query Timeout

```
QueryError: Query exceeded timeout
```

**Solutions:**
1. Increase `query_timeout` in config
2. Add filters to reduce data scanned
3. Check cluster resources

---

## Security

### SSL/TLS

For production, always use HTTPS:

```json
{
  "http_scheme": "https",
  "verify_ssl": true
}
```

### Row-Level Security

SetuPranali automatically applies RLS:

```yaml
datasets:
  - id: sales
    rls:
      mode: tenant_column
      field: tenant_id
```

This adds a `WHERE tenant_id = 'your_tenant'` filter to all queries.

---

## CLI Usage

```bash
# Add Trino source
setupranali sources add \
  --name my-trino \
  --type trino \
  --config '{"host":"trino.example.com","port":8443,"user":"analyst","password":"secret","catalog":"hive","schema":"default"}'

# Test connection
setupranali sources test my-trino

# Query
setupranali query sales -d region -m revenue
```

---

## API Examples

### Query via REST

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue", "orders"],
    "limit": 100
  }'
```

### Query via GraphQL

```graphql
query {
  query(input: {
    dataset: "sales"
    dimensions: ["region"]
    metrics: ["revenue"]
  }) {
    columns { name type }
    data
    stats { rowCount executionTimeMs cached }
  }
}
```

