# PostgreSQL

Connect to PostgreSQL databases.

---

## Requirements

- PostgreSQL 11 or later
- Network access from connector to database
- User with SELECT permissions

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres-prod",
    "type": "postgres",
    "connection": {
      "host": "db.example.com",
      "port": 5432,
      "database": "analytics",
      "user": "bi_readonly",
      "password": "your-password",
      "sslmode": "require"
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `host` | Database hostname | Required |
| `port` | Database port | `5432` |
| `database` | Database name | Required |
| `user` | Username | Required |
| `password` | Password | Required |
| `sslmode` | SSL mode | `prefer` |
| `connect_timeout` | Connection timeout (seconds) | `10` |

### SSL Modes

| Mode | Description |
|------|-------------|
| `disable` | No SSL |
| `allow` | Try SSL, fallback to non-SSL |
| `prefer` | Try SSL, fallback to non-SSL |
| `require` | Require SSL |
| `verify-ca` | Require SSL + verify CA |
| `verify-full` | Require SSL + verify CA + hostname |

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: public.orders
    
    dimensions:
      - name: region
        type: string
        expr: region
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(amount)"
```

---

## Database Setup

### Create Read-Only User

```sql
-- Create user
CREATE USER bi_readonly WITH PASSWORD 'secure-password';

-- Grant connect
GRANT CONNECT ON DATABASE analytics TO bi_readonly;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO bi_readonly;

-- Grant select on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_readonly;

-- Grant for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT SELECT ON TABLES TO bi_readonly;
```

### Network Configuration

Edit `pg_hba.conf` for external access:

```
# Allow from connector IP
host    analytics    bi_readonly    10.0.0.0/8    scram-sha-256
```

---

## Performance

### Connection Pooling

The adapter uses connection pooling:

```
min_connections: 1
max_connections: 10
```

### Recommended Indexes

```sql
-- Index tenant column for RLS
CREATE INDEX idx_orders_tenant ON orders(tenant_id);

-- Index date column for incremental refresh
CREATE INDEX idx_orders_date ON orders(order_date);

-- Composite index for common queries
CREATE INDEX idx_orders_tenant_date 
  ON orders(tenant_id, order_date);
```

---

## Troubleshooting

### Connection Refused

```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solutions**:
1. Verify PostgreSQL is running
2. Check host and port
3. Check `pg_hba.conf` allows connections
4. Check firewall rules

### Authentication Failed

```
FATAL: password authentication failed for user "bi_readonly"
```

**Solutions**:
1. Verify username and password
2. Check user exists: `\du`
3. Check `pg_hba.conf` authentication method

### SSL Error

```
SSL connection is required
```

**Solutions**:
1. Add `sslmode: require` to connection
2. Or disable SSL on server (not recommended)

