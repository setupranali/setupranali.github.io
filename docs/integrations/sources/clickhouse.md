# ClickHouse

Connect to ClickHouse OLAP database.

---

## Requirements

- ClickHouse 21.8+
- HTTP interface enabled
- User with SELECT permissions

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "clickhouse-prod",
    "type": "clickhouse",
    "connection": {
      "host": "clickhouse.example.com",
      "port": 8443,
      "database": "analytics",
      "user": "readonly",
      "password": "your-password",
      "secure": true
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `host` | ClickHouse hostname | Required |
| `port` | HTTP(S) port | `8443` (secure), `8123` (insecure) |
| `database` | Database name | `default` |
| `user` | Username | `default` |
| `password` | Password | Empty |
| `secure` | Use HTTPS | `true` |

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: events
    source: clickhouse-prod
    table: events
    
    dimensions:
      - name: event_type
        type: string
        expr: event_type
      
      - name: event_date
        type: date
        expr: toDate(event_time)
    
    metrics:
      - name: event_count
        type: number
        expr: "count()"
      
      - name: unique_users
        type: number
        expr: "uniqExact(user_id)"
```

---

## ClickHouse Setup

### Create Read-Only User

```sql
CREATE USER readonly IDENTIFIED BY 'secure-password';

GRANT SELECT ON analytics.* TO readonly;
```

---

## ClickHouse Cloud

For ClickHouse Cloud:

```json
{
  "host": "xxx.clickhouse.cloud",
  "port": 8443,
  "secure": true,
  "user": "default",
  "password": "your-cloud-password"
}
```

---

## Performance

### Materialized Views

For frequently queried aggregations:

```sql
CREATE MATERIALIZED VIEW events_by_day
ENGINE = SummingMergeTree()
ORDER BY (event_date, event_type)
AS SELECT
  toDate(event_time) as event_date,
  event_type,
  count() as event_count
FROM events
GROUP BY event_date, event_type;
```

Reference in catalog:

```yaml
datasets:
  - name: events_summary
    source: clickhouse-prod
    table: events_by_day
```

---

## Troubleshooting

### Connection Refused

```
Connection refused
```

**Solutions**:
1. Verify HTTP interface is enabled
2. Check port (8123 HTTP, 8443 HTTPS)
3. Check firewall rules

### Authentication Failed

```
Authentication failed
```

**Solutions**:
1. Verify username and password
2. Check user exists: `SHOW USERS`
3. Verify grants: `SHOW GRANTS FOR readonly`

