# Snowflake

Connect to Snowflake data warehouse.

---

## Requirements

- Snowflake account
- User with SELECT permissions
- Warehouse for query execution

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "snowflake-prod",
    "type": "snowflake",
    "connection": {
      "account": "abc123.us-east-1",
      "user": "BI_SERVICE",
      "password": "your-password",
      "warehouse": "ANALYTICS_WH",
      "database": "ANALYTICS",
      "schema": "PUBLIC",
      "role": "ANALYST"
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `account` | Snowflake account identifier | Required |
| `user` | Username | Required |
| `password` | Password | Required |
| `warehouse` | Warehouse name | Required |
| `database` | Database name | Required |
| `schema` | Schema name | `PUBLIC` |
| `role` | Role to use | User's default |

### Account Identifier Format

```
# Standard
account: xyz12345

# With region
account: xyz12345.us-east-1

# With cloud provider
account: xyz12345.us-east-1.aws
```

---

## Authentication Methods

### Password

```json
{
  "account": "xyz12345",
  "user": "BI_SERVICE",
  "password": "your-password"
}
```

### Key Pair

```json
{
  "account": "xyz12345",
  "user": "BI_SERVICE",
  "private_key_path": "/path/to/rsa_key.p8",
  "private_key_passphrase": "optional-passphrase"
}
```

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: sales
    source: snowflake-prod
    table: ANALYTICS.FACT_SALES
    
    dimensions:
      - name: region
        type: string
        expr: REGION_NAME
    
    metrics:
      - name: revenue
        type: number
        expr: "SUM(SALE_AMOUNT)"
```

---

## Snowflake Setup

### Create Service User

```sql
-- Create role
CREATE ROLE BI_READER;

-- Grant warehouse usage
GRANT USAGE ON WAREHOUSE ANALYTICS_WH TO ROLE BI_READER;

-- Grant database access
GRANT USAGE ON DATABASE ANALYTICS TO ROLE BI_READER;
GRANT USAGE ON SCHEMA ANALYTICS.PUBLIC TO ROLE BI_READER;

-- Grant table access
GRANT SELECT ON ALL TABLES IN SCHEMA ANALYTICS.PUBLIC TO ROLE BI_READER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA ANALYTICS.PUBLIC TO ROLE BI_READER;

-- Create user
CREATE USER BI_SERVICE
  PASSWORD = 'secure-password'
  DEFAULT_ROLE = BI_READER
  DEFAULT_WAREHOUSE = ANALYTICS_WH;

-- Assign role
GRANT ROLE BI_READER TO USER BI_SERVICE;
```

### Network Policy (Optional)

Restrict access to connector IPs:

```sql
CREATE NETWORK POLICY bi_connector_policy
  ALLOWED_IP_LIST = ('10.0.0.0/8', '192.168.1.100')
  BLOCKED_IP_LIST = ();

ALTER USER BI_SERVICE SET NETWORK_POLICY = bi_connector_policy;
```

---

## Performance

### Warehouse Sizing

| Query Pattern | Recommended Size |
|---------------|-----------------|
| Light dashboards | X-Small |
| Standard reports | Small |
| Heavy analytics | Medium+ |

### Auto-Suspend

Configure warehouse to suspend when idle:

```sql
ALTER WAREHOUSE ANALYTICS_WH SET
  AUTO_SUSPEND = 60        -- Suspend after 60 seconds
  AUTO_RESUME = TRUE;      -- Resume on query
```

### Result Caching

Snowflake has built-in result caching. Combined with connector caching:

1. Connector cache hit → Instant response
2. Connector miss, Snowflake cache hit → Fast response
3. Both miss → Full query execution

---

## Troubleshooting

### Account Not Found

```
250001: Could not connect to Snowflake backend
```

**Solutions**:
1. Verify account identifier format
2. Check account is active
3. Verify region/cloud in account identifier

### Warehouse Unavailable

```
Warehouse 'ANALYTICS_WH' is not available
```

**Solutions**:
1. Check warehouse is not suspended
2. Verify user has USAGE privilege
3. Check warehouse size/credits

### Access Denied

```
Object 'ANALYTICS.FACT_SALES' does not exist or not authorized
```

**Solutions**:
1. Verify table exists
2. Check role has SELECT privilege
3. Verify database/schema context

