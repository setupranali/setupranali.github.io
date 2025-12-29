# Databricks

Connect to Databricks SQL.

---

## Requirements

- Databricks workspace
- SQL Warehouse (Serverless or Pro)
- Personal Access Token

---

## Configuration

### Register Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "databricks-prod",
    "type": "databricks",
    "connection": {
      "server_hostname": "abc123.cloud.databricks.com",
      "http_path": "/sql/1.0/warehouses/xyz789",
      "access_token": "dapi..."
    }
  }'
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `server_hostname` | Databricks workspace URL | Required |
| `http_path` | SQL Warehouse HTTP path | Required |
| `access_token` | Personal Access Token | Required |
| `catalog` | Unity Catalog name | `hive_metastore` |
| `schema` | Default schema | `default` |

---

## Getting Connection Details

### Server Hostname

Found in your Databricks workspace URL:

```
https://abc123.cloud.databricks.com
         ↑ server_hostname
```

### HTTP Path

1. Go to **SQL Warehouses**
2. Select your warehouse
3. **Connection details** tab
4. Copy **HTTP path**

### Access Token

1. Go to **User Settings**
2. **Access Tokens** tab
3. Generate new token

---

## Dataset Configuration

```yaml
# catalog.yaml
datasets:
  - name: sales
    source: databricks-prod
    table: catalog.schema.sales
    
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

## Unity Catalog

For Unity Catalog-enabled workspaces:

```json
{
  "catalog": "main",
  "schema": "analytics"
}
```

Table reference:

```yaml
table: main.analytics.sales
```

---

## Performance

### Warehouse Sizing

| Size | Use Case |
|------|----------|
| 2X-Small | Development, light queries |
| Small | Standard dashboards |
| Medium+ | Heavy analytics |

### Serverless vs Pro

| Type | Best For |
|------|----------|
| Serverless | Variable workloads, cost optimization |
| Pro | Predictable workloads, low latency |

---

## Troubleshooting

### Invalid Token

```
Invalid access token
```

**Solutions**:
1. Generate new access token
2. Verify token hasn't expired
3. Check token permissions

### Warehouse Not Found

```
SQL warehouse not found
```

**Solutions**:
1. Verify HTTP path is correct
2. Check warehouse is running
3. Verify user has access to warehouse

