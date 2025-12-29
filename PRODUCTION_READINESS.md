# Production Readiness Guide

This document outlines everything needed to deploy SetuPranali in production.

## Pre-Deployment Checklist

### Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `UBI_SECRET_KEY` | **Yes** | 32-byte Fernet key for encryption | `dGhpcyBpcyBhIDMyIGJ5dGUga2V5...` |
| `REDIS_URL` | **Yes** | Redis connection URL | `redis://localhost:6379/0` |

### Recommended Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_ENABLED` | `true` | Enable query caching |
| `CACHE_TTL_SECONDS` | `60` | Cache TTL |
| `CACHE_MAX_ROWS` | `10000` | Skip caching large results |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_QUERY` | `60/minute` | Query endpoint limit |
| `RATE_LIMIT_ODATA` | `120/minute` | OData endpoint limit |
| `QUERY_MAX_ROWS` | `100000` | Maximum rows per query |
| `QUERY_TIMEOUT_SECONDS` | `30` | Query timeout |

---

## Secret Management

### Encryption Key Generation

Generate a production encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Critical Rules:**
- Never commit keys to version control
- Rotate keys periodically (monthly recommended)
- Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- Keep backup of keys (encrypted)

### API Key Management

Current implementation uses in-memory API keys. For production:

1. **Database Storage**: Move API keys to encrypted database
2. **Key Rotation**: Implement automated key rotation
3. **Audit Logging**: Log all key usage (without raw keys)
4. **Key Scopes**: Limit keys to specific datasets/operations

---

## Redis Setup

### Docker (Development/Staging)

```bash
docker run -d \
  --name ubi-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:alpine \
  redis-server --appendonly yes
```

### Production Redis

Recommended configuration:
- Redis 6.x or later
- Enable persistence (AOF recommended)
- Configure maxmemory and eviction policy
- Enable TLS for network encryption
- Use Redis Sentinel or Cluster for HA

Example Redis configuration:

```conf
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec
```

### Redis Connection String

```bash
# Local
REDIS_URL=redis://localhost:6379/0

# With password
REDIS_URL=redis://:password@localhost:6379/0

# TLS
REDIS_URL=rediss://:password@redis.example.com:6380/0
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/v1/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  ubi-connector:
    build: .
    ports:
      - "8080:8080"
    environment:
      - UBI_SECRET_KEY=${UBI_SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
      - CACHE_ENABLED=true
      - RATE_LIMIT_ENABLED=true
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:alpine
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis-data:
```

---

## Kubernetes Deployment

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ubi-connector-config
data:
  CACHE_ENABLED: "true"
  CACHE_TTL_SECONDS: "60"
  RATE_LIMIT_ENABLED: "true"
  QUERY_MAX_ROWS: "100000"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ubi-connector-secrets
type: Opaque
stringData:
  UBI_SECRET_KEY: "your-generated-key-here"
  REDIS_URL: "redis://redis:6379/0"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ubi-connector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ubi-connector
  template:
    metadata:
      labels:
        app: ubi-connector
    spec:
      containers:
      - name: ubi-connector
        image: ubi-connector:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: ubi-connector-config
        - secretRef:
            name: ubi-connector-secrets
        livenessProbe:
          httpGet:
            path: /v1/health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /v1/health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

## Backup Strategy

### What to Backup

1. **Sources Database** (`app/db/sources.db`)
   - Contains encrypted data source credentials
   - Backup frequency: Daily
   - Retention: 30 days

2. **Encryption Key** (`UBI_SECRET_KEY`)
   - Store in secrets manager
   - Keep secure backup
   - Document rotation procedure

3. **Catalog** (`catalog.yaml`)
   - Version control (Git)
   - Review changes before deployment

### Backup Script

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/ubi-connector"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup sources database
cp app/db/sources.db $BACKUP_DIR/sources_$DATE.db

# Compress
gzip $BACKUP_DIR/sources_$DATE.db

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/sources_$DATE.db.gz"
```

---

## Monitoring Checklist

### Health Endpoints

| Endpoint | Purpose | Access |
|----------|---------|--------|
| `/v1/health` | Basic health check | Public |
| `/internal/status` | Detailed system status | Admin only |

### Metrics to Monitor

1. **Request Metrics**
   - Request rate (per endpoint)
   - Response latency (p50, p95, p99)
   - Error rate (4xx, 5xx)

2. **Cache Metrics**
   - Hit rate
   - Miss rate
   - Redis memory usage

3. **Query Metrics**
   - Query duration
   - Result size
   - Timeout rate

4. **Security Metrics**
   - Authentication failures
   - Rate limit hits
   - Revoked key usage attempts

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate | > 1% | > 5% |
| P99 latency | > 5s | > 10s |
| Cache hit rate | < 50% | < 20% |
| Rate limit hits | > 10/min | > 50/min |
| Redis memory | > 70% | > 90% |

### Logging

Logs are structured with request IDs:

```
2025-12-23 11:45:32 - app.main - INFO - [abc12345] Query: dataset=orders tenant=tenantA dims=2 metrics=1
```

Key fields:
- `request_id`: For tracing across services
- `tenant`: For multi-tenant debugging
- `dataset`: For query analysis

**Never logged:**
- Raw API keys
- Database credentials
- Query results

---

## Security Hardening

### Network Security

1. **HTTPS Only**: Use TLS termination at load balancer
2. **Private Network**: Keep Redis and databases on private network
3. **Firewall Rules**: Restrict access to necessary ports only

### Application Security

1. **Rate Limiting**: Enabled by default
2. **Request Validation**: Safety guards on all queries
3. **Credential Encryption**: Fernet encryption at rest
4. **API Key Rotation**: Implement regular rotation

### Headers

The application sets these security headers:
- `X-Request-ID`: For request tracing
- `Retry-After`: On rate limit (429)

Add these at your load balancer:
- `Strict-Transport-Security`
- `X-Content-Type-Options`
- `X-Frame-Options`

---

## Scaling Considerations

### Horizontal Scaling

The application is stateless and can scale horizontally:
- Use Redis for shared cache/rate limits
- Use load balancer for distribution
- Session affinity NOT required

### Vertical Scaling

For query-heavy workloads:
- Increase memory for large result sets
- Increase CPU for complex aggregations

### Database Scaling

- DuckDB: In-memory, scale vertically
- PostgreSQL: Use connection pooling (PgBouncer)
- Consider read replicas for analytics

---

## Troubleshooting

### Common Issues

**Issue**: Startup warnings about missing configuration
**Solution**: Set required environment variables

**Issue**: Cache always misses
**Solution**: Check Redis connectivity (`redis-cli ping`)

**Issue**: Rate limit exceeded errors
**Solution**: Increase limits or distribute requests

**Issue**: Query timeout
**Solution**: Reduce result size or increase timeout

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
```

### Health Check

```bash
# Basic health
curl http://localhost:8080/v1/health

# Detailed status (requires admin key)
curl -H "X-API-Key: internal-admin-key" http://localhost:8080/internal/status
```

---

## Support Contacts

- **Documentation**: [README.md](./README.md)
- **API Reference**: http://localhost:8080/docs
- **Issues**: GitHub Issues

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-23 | Initial production release |

---

*Last updated: 2025-12-23*

