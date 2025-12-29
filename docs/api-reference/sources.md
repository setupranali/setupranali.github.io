# Sources API

Manage data source connections.

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/sources` | List all sources |
| POST | `/v1/sources` | Create source |
| GET | `/v1/sources/{name}` | Get source details |
| DELETE | `/v1/sources/{name}` | Delete source |
| GET | `/v1/sources/{name}/health` | Test connection |

---

## List Sources

### Request

```bash
curl http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key"
```

### Response

```json
{
  "sources": [
    {
      "name": "postgres-prod",
      "type": "postgres",
      "created_at": "2024-01-15T10:00:00Z"
    },
    {
      "name": "snowflake-dw",
      "type": "snowflake",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ]
}
```

---

## Create Source

### Request

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
      "user": "readonly",
      "password": "secure-password"
    }
  }'
```

### Response

```json
{
  "name": "postgres-prod",
  "type": "postgres",
  "created_at": "2024-01-15T10:00:00Z",
  "status": "connected"
}
```

### Source Types

| Type | Description |
|------|-------------|
| `postgres` | PostgreSQL |
| `mysql` | MySQL / MariaDB |
| `snowflake` | Snowflake |
| `bigquery` | Google BigQuery |
| `databricks` | Databricks SQL |
| `redshift` | Amazon Redshift |
| `clickhouse` | ClickHouse |
| `duckdb` | DuckDB |

---

## Connection Parameters

### PostgreSQL

```json
{
  "host": "db.example.com",
  "port": 5432,
  "database": "analytics",
  "user": "readonly",
  "password": "password",
  "sslmode": "require"
}
```

### Snowflake

```json
{
  "account": "abc123.us-east-1",
  "user": "BI_SERVICE",
  "password": "password",
  "warehouse": "ANALYTICS_WH",
  "database": "ANALYTICS",
  "schema": "PUBLIC",
  "role": "ANALYST"
}
```

### BigQuery

```json
{
  "project_id": "my-project",
  "credentials_json": "{...service-account-json...}",
  "location": "US"
}
```

### Databricks

```json
{
  "server_hostname": "abc123.cloud.databricks.com",
  "http_path": "/sql/1.0/warehouses/xyz789",
  "access_token": "dapi..."
}
```

---

## Get Source

### Request

```bash
curl http://localhost:8080/v1/sources/postgres-prod \
  -H "X-API-Key: admin-key"
```

### Response

```json
{
  "name": "postgres-prod",
  "type": "postgres",
  "created_at": "2024-01-15T10:00:00Z",
  "connection": {
    "host": "db.example.com",
    "port": 5432,
    "database": "analytics",
    "user": "readonly"
  }
}
```

!!! note "Security"
    Passwords are never returned in API responses.

---

## Delete Source

### Request

```bash
curl -X DELETE http://localhost:8080/v1/sources/postgres-prod \
  -H "X-API-Key: admin-key"
```

### Response

```json
{
  "deleted": true,
  "name": "postgres-prod"
}
```

---

## Health Check

Test source connection.

### Request

```bash
curl http://localhost:8080/v1/sources/postgres-prod/health \
  -H "X-API-Key: admin-key"
```

### Response (Healthy)

```json
{
  "status": "connected",
  "latency_ms": 45,
  "version": "PostgreSQL 15.2"
}
```

### Response (Unhealthy)

```json
{
  "status": "error",
  "error": "Connection refused"
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid source type 'unknown'"
}
```

### 401 Unauthorized

```json
{
  "detail": "Admin API key required"
}
```

### 404 Not Found

```json
{
  "detail": "Source 'unknown' not found"
}
```

### 409 Conflict

```json
{
  "detail": "Source 'postgres-prod' already exists"
}
```

---

## Security

### Admin Access Required

Source management requires an admin API key:

```yaml
api_keys:
  - key: "admin-key"
    role: admin  # Required
```

### Credential Encryption

All credentials are encrypted at rest using Fernet (AES-128):

```
User provides password → Encrypted → Stored
Retrieved → Decrypted → Used → Never logged
```

