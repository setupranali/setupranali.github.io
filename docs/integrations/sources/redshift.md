# Redshift

Connect to Amazon Redshift.

---

## Requirements

- Redshift cluster or Serverless
- VPC/Network access
- User with SELECT permissions

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "redshift-prod",
    "type": "redshift",
    "connection": {
      "host": "cluster.xxx.us-east-1.redshift.amazonaws.com",
      "port": 5439,
      "database": "analytics",
      "user": "bi_readonly",
      "password": "your-password",
      "ssl": true
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `host` | Cluster endpoint | Required |
| `port` | Database port | `5439` |
| `database` | Database name | Required |
| `user` | Username | Required |
| `password` | Password | Required |
| `ssl` | Enable SSL | `true` |

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: events
    source: redshift-prod
    table: analytics.events
    
    dimensions:
      - name: event_type
        type: string
        expr: event_type
    
    metrics:
      - name: event_count
        type: number
        expr: "COUNT(*)"
```

---

## Redshift Setup

### Create Read-Only User

```sql
-- Create user
CREATE USER bi_readonly PASSWORD 'secure-password';

-- Grant schema usage
GRANT USAGE ON SCHEMA analytics TO bi_readonly;

-- Grant select on tables
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO bi_readonly;
```

---

## Redshift Serverless

For Serverless workgroups:

```bash
curl -X POST http://localhost:8080/v1/sources \
  -d '{
    "name": "redshift-serverless",
    "type": "redshift",
    "connection": {
      "host": "workgroup.xxx.us-east-1.redshift-serverless.amazonaws.com",
      "port": 5439,
      "database": "dev",
      "user": "admin",
      "password": "your-password"
    }
  }'
```

---

## Troubleshooting

### Connection Timeout

```
Connection timed out
```

**Solutions**:
1. Check VPC security groups
2. Verify cluster is publicly accessible (or use VPN)
3. Check network ACLs

### Access Denied

```
Permission denied for relation
```

**Solutions**:
1. Verify GRANT SELECT was executed
2. Check schema permissions
3. Verify user exists

