# Configuration

Environment variables and configuration options.

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `UBI_SECRET_KEY` | Encryption key for source credentials |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |

### Caching

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL_SECONDS` | `300` | Cache duration in seconds |
| `CACHE_ENABLED` | `true` | Enable/disable caching |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_QUERY` | `100/minute` | Query endpoint limit |
| `RATE_LIMIT_ODATA` | `50/minute` | OData endpoint limit |
| `RATE_LIMIT_SOURCES` | `10/minute` | Sources endpoint limit |

### Query Guards

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DIMENSIONS` | `10` | Max dimensions per query |
| `MAX_METRICS` | `20` | Max metrics per query |
| `MAX_ROWS` | `100000` | Max rows returned |
| `MAX_FILTER_DEPTH` | `5` | Max nested filter depth |
| `QUERY_TIMEOUT_SECONDS` | `30` | Query timeout |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `json` | Log format (json, text) |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8080` | Server port |
| `WORKERS` | `1` | Number of workers |

---

## Example .env File

```bash
# Required
UBI_SECRET_KEY=your-secret-key-base64-encoded

# Redis
REDIS_URL=redis://localhost:6379

# Caching
CACHE_TTL_SECONDS=300
CACHE_ENABLED=true

# Rate Limiting
RATE_LIMIT_QUERY=100/minute
RATE_LIMIT_ODATA=50/minute
RATE_LIMIT_SOURCES=10/minute

# Query Guards
MAX_DIMENSIONS=10
MAX_METRICS=20
MAX_ROWS=100000
MAX_FILTER_DEPTH=5
QUERY_TIMEOUT_SECONDS=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Generating Secret Key

```bash
# OpenSSL
openssl rand -base64 32

# Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Rate Limit Format

```
{count}/{period}
```

| Period | Description |
|--------|-------------|
| `second` | Per second |
| `minute` | Per minute |
| `hour` | Per hour |
| `day` | Per day |

Examples:
- `100/minute`
- `1000/hour`
- `10/second`

---

## Catalog Configuration

### File Location

The catalog file (`catalog.yaml`) defines your semantic layer.

Default location: `/app/catalog.yaml`

### Structure

```yaml
datasets:
  - name: dataset_name
    source: source_name
    table: schema.table_name
    
    dimensions:
      - name: dimension_name
        type: string|number|date
        expr: column_expression
    
    metrics:
      - name: metric_name
        type: number
        expr: aggregation_expression
    
    rls:
      tenant_column: column_name
    
    incremental:
      date_column: column_name
```

---

## API Keys Configuration

### In Configuration File

```yaml
# config.yaml
api_keys:
  - key: "admin-key-xxxxx"
    role: admin
  
  - key: "pk_tenant_abc123"
    tenant: tenant_name
    role: analyst
```

### Environment Variable

```bash
API_KEYS='[{"key":"admin-key","role":"admin"},{"key":"pk_tenant","tenant":"tenant","role":"analyst"}]'
```

---

## Docker Configuration

### Environment Variables

```yaml
services:
  connector:
    environment:
      - UBI_SECRET_KEY=${UBI_SECRET_KEY}
      - REDIS_URL=redis://redis:6379
```

### Volume Mounts

```yaml
services:
  connector:
    volumes:
      - ./catalog.yaml:/app/catalog.yaml:ro
      - ./data:/app/data
```

---

## Kubernetes Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ubi-config
data:
  CACHE_TTL_SECONDS: "300"
  RATE_LIMIT_QUERY: "100/minute"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ubi-secrets
stringData:
  UBI_SECRET_KEY: "your-secret-key"
```

### Using in Deployment

```yaml
containers:
  - name: connector
    envFrom:
      - configMapRef:
          name: ubi-config
      - secretRef:
          name: ubi-secrets
```

