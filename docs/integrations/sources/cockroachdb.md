# CockroachDB

Connect SetuPranali to CockroachDB for globally distributed, resilient SQL analytics.

---

## Overview

**CockroachDB** is ideal for:

- Globally distributed databases
- Multi-region deployments
- High availability requirements
- Cloud-native applications
- Horizontal scaling with consistency

!!! info "PostgreSQL Compatible"
    CockroachDB uses the PostgreSQL wire protocol - all PostgreSQL tools work seamlessly!

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
    "name": "my-cockroach",
    "type": "cockroachdb",
    "connection": {
      "host": "cockroach.company.com",
      "port": 26257,
      "database": "defaultdb",
      "user": "root",
      "password": "secret"
    }
  }'
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `host` | ✅ | - | Server hostname or IP |
| `port` | | `26257` | Server port |
| `database` | ✅ | - | Database name |
| `user` | ✅ | - | Username |
| `password` | ✅ | - | Password |
| `sslmode` | | `verify-full`* | SSL mode |
| `sslrootcert` | | - | Path to CA certificate |
| `cluster` | | - | CockroachDB Cloud cluster ID |
| `connect_timeout` | | `30` | Connection timeout (seconds) |
| `application_name` | | `SetuPranali` | Application identifier |

*Default `verify-full` for CockroachDB Cloud hosts

---

## Examples

### Self-Hosted CockroachDB

```json
{
  "name": "crdb-cluster",
  "type": "cockroachdb",
  "connection": {
    "host": "cockroach-1.company.com",
    "port": 26257,
    "database": "analytics",
    "user": "analytics_user",
    "password": "secure_password",
    "sslmode": "verify-full",
    "sslrootcert": "/certs/ca.crt"
  }
}
```

### CockroachDB Cloud (Serverless)

```json
{
  "name": "crdb-cloud",
  "type": "crdb",
  "connection": {
    "host": "free-tier.gcp-us-central1.cockroachlabs.cloud",
    "port": 26257,
    "database": "defaultdb",
    "user": "username",
    "password": "your_password",
    "cluster": "your-cluster-123"
  }
}
```

### CockroachDB Cloud (Dedicated)

```json
{
  "name": "crdb-dedicated",
  "type": "cockroachdb",
  "connection": {
    "host": "your-cluster.aws-us-east-1.cockroachlabs.cloud",
    "port": 26257,
    "database": "analytics",
    "user": "admin",
    "password": "secure_password",
    "sslmode": "verify-full"
  }
}
```

### Insecure Mode (Development Only)

```json
{
  "name": "crdb-dev",
  "type": "cockroachdb",
  "connection": {
    "host": "localhost",
    "port": 26257,
    "database": "defaultdb",
    "user": "root",
    "password": "",
    "sslmode": "disable"
  }
}
```

---

## Dataset Configuration

### catalog.yaml Example

```yaml
datasets:
  - id: orders
    name: Global Orders
    description: Order data distributed across regions
    source: my-cockroach
    table: orders
    dimensions:
      - name: region
        expr: region
      - name: status
        expr: status
      - name: date
        expr: created_at
        type: timestamp
    metrics:
      - name: total_revenue
        expr: "SUM(amount)"
      - name: order_count
        expr: "COUNT(*)"
      - name: avg_order_value
        expr: "AVG(amount)"
    rls:
      mode: tenant_column
      field: tenant_id
```

### Multi-Region Table

```yaml
datasets:
  - id: global_users
    name: Global Users
    source: my-cockroach
    table: users
    dimensions:
      - name: region
        expr: crdb_region
      - name: country
      - name: signup_date
        type: date
    metrics:
      - name: user_count
        expr: "COUNT(*)"
```

---

## CockroachDB Features

### Multi-Region Tables

```sql
-- Create multi-region database
ALTER DATABASE mydb PRIMARY REGION "us-east1";
ALTER DATABASE mydb ADD REGION "us-west1";
ALTER DATABASE mydb ADD REGION "eu-west1";

-- Create regional table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    region crdb_internal_region,
    name STRING
) LOCALITY REGIONAL BY ROW;
```

### Geo-Partitioning

```sql
-- Partition by region
ALTER TABLE orders 
PARTITION BY LIST (region) (
    PARTITION us VALUES IN ('us-east', 'us-west'),
    PARTITION eu VALUES IN ('eu-west', 'eu-central')
);
```

### Follower Reads

For analytics, use follower reads for lower latency:

```sql
SET TRANSACTION AS OF SYSTEM TIME follower_read_timestamp();
SELECT * FROM large_table;
```

---

## Performance Tips

### 1. Use Follower Reads

For analytics workloads, enable follower reads:

```sql
-- In your queries
SET TRANSACTION AS OF SYSTEM TIME follower_read_timestamp();
```

### 2. Index Optimization

Create indexes on frequently queried columns:

```sql
CREATE INDEX idx_orders_region ON orders (region, created_at);
```

### 3. Connection Load Balancing

Connect through a load balancer across nodes:

```json
{
  "host": "crdb-lb.company.com",
  "port": 26257
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

### 5. Monitor Query Performance

```sql
-- Check slow queries
SELECT * FROM crdb_internal.cluster_queries
WHERE elapsed > '10s'
ORDER BY start DESC;
```

---

## Troubleshooting

### Connection Refused

```
connection refused
```

**Solutions:**
1. Verify host and port (default 26257)
2. Check firewall rules
3. Ensure cluster is running
4. For Cloud, verify IP allowlist

### Certificate Errors

```
x509: certificate signed by unknown authority
```

**Solutions:**
1. Download CA cert from CockroachDB Cloud
2. Set `sslrootcert` to CA path
3. For dev, use `sslmode: disable`

### Authentication Failed

```
password authentication failed
```

**Solutions:**
1. Verify username and password
2. For Cloud, use the connection string from console
3. Check user has database access

### Cluster Not Found

```
cluster not found
```

**Solutions:**
1. Verify `cluster` option is correct
2. Use the cluster ID from CockroachDB Cloud console
3. Check cluster is running

---

## Security

### Row-Level Security

```yaml
datasets:
  - id: orders
    rls:
      mode: tenant_column
      field: tenant_id
```

### Minimal Permissions

```sql
-- Create read-only user
CREATE USER bi_reader WITH PASSWORD 'secure_password';

-- Grant read access
GRANT SELECT ON DATABASE analytics TO bi_reader;
GRANT SELECT ON TABLE orders, products, customers TO bi_reader;
```

### SSL/TLS Configuration

For production, always use SSL:

```json
{
  "sslmode": "verify-full",
  "sslrootcert": "/path/to/ca.crt"
}
```

---

## CLI Usage

```bash
# Add CockroachDB source
setupranali sources add \
  --name my-cockroach \
  --type cockroachdb \
  --config '{"host":"cockroach.example.com","port":26257,"database":"analytics","user":"root","password":"secret"}'

# Test connection
setupranali sources test my-cockroach

# Query
setupranali query orders -d region -m total_revenue
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
    "dimensions": ["region"],
    "metrics": ["total_revenue", "order_count"],
    "limit": 100
  }'
```

### SQL Query

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT region, SUM(amount) as revenue FROM orders GROUP BY region",
    "dataset": "orders"
  }'
```

---

## Comparison with PostgreSQL

| Feature | CockroachDB | PostgreSQL |
|---------|-------------|------------|
| **Distribution** | Built-in | Requires extensions |
| **Multi-Region** | Native | Complex setup |
| **Scaling** | Horizontal | Vertical primarily |
| **Consistency** | Serializable | Configurable |
| **Availability** | 99.99%+ | Requires HA setup |
| **Wire Protocol** | PostgreSQL | Native |

---

## Type Aliases

| Alias | Use Case |
|-------|----------|
| `cockroachdb` | Standard CockroachDB |
| `cockroach` | Alternative name |
| `crdb` | Short alias |

