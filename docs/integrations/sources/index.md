# Data Sources

Connect SetuPranali to your databases and data warehouses.

---

## Supported Sources

| Source | Type | Adapter | Status |
|--------|------|---------|--------|
| [PostgreSQL](postgresql.md) | Relational | `postgres` | ✅ GA |
| [MySQL](mysql.md) | Relational | `mysql` | ✅ GA |
| [Snowflake](snowflake.md) | Data Warehouse | `snowflake` | ✅ GA |
| [BigQuery](bigquery.md) | Data Warehouse | `bigquery` | ✅ GA |
| [Databricks](databricks.md) | Lakehouse | `databricks` | ✅ GA |
| [Redshift](redshift.md) | Data Warehouse | `redshift` | ✅ GA |
| [ClickHouse](clickhouse.md) | OLAP | `clickhouse` | ✅ GA |
| DuckDB | Embedded | `duckdb` | ✅ GA |

---

## Adding a Source

### Via API

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-warehouse",
    "type": "postgres",
    "connection": {
      "host": "db.example.com",
      "port": 5432,
      "database": "analytics",
      "user": "readonly",
      "password": "***"
    }
  }'
```

### Connection Properties

| Property | Description | Required |
|----------|-------------|----------|
| `name` | Unique source identifier | Yes |
| `type` | Adapter type (see table above) | Yes |
| `connection` | Connection parameters | Yes |

---

## Connection Security

### Credential Storage

Credentials are encrypted at rest using Fernet (AES-128):

```
User provides credentials → Encrypted → Stored in SQLite
                                       (never in plaintext)
```

### Best Practices

1. **Use service accounts** with minimal permissions
2. **Restrict network access** (VPN, allowlisting)
3. **Enable SSL** for database connections
4. **Rotate credentials** regularly

### Required Database Permissions

| Permission | Purpose |
|------------|---------|
| SELECT | Query data |
| (No INSERT/UPDATE/DELETE) | Read-only access |

---

## Testing Connections

### Health Check

```bash
curl http://localhost:8080/v1/sources/my-warehouse/health \
  -H "X-API-Key: admin-key"
```

Response:

```json
{
  "status": "connected",
  "latency_ms": 45,
  "version": "PostgreSQL 15.2"
}
```

### List Sources

```bash
curl http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key"
```

---

## Troubleshooting

### Connection Refused

```
Error: Connection refused
```

**Solutions**:
- Verify host and port
- Check firewall rules
- Ensure database is running

### Authentication Failed

```
Error: Authentication failed
```

**Solutions**:
- Verify username and password
- Check user permissions
- Ensure SSL mode is correct

### Timeout

```
Error: Connection timeout
```

**Solutions**:
- Check network connectivity
- Increase connection timeout
- Verify VPN connection (if required)

