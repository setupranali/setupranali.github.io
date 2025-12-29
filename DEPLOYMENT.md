# Deployment Guide

This guide covers deploying SetuPranali from local development to production.

---

## Quick Start

### Local Development (Docker Compose)

```bash
# Clone and enter directory
cd ubi-connector

# Copy environment file
cp env.example .env

# Generate encryption key and add to .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Edit .env and set UBI_SECRET_KEY=<generated-key>

# Start services
docker compose up -d

# Verify
curl http://localhost:8080/v1/health
```

### Local Development (Without Docker)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export UBI_SECRET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export REDIS_URL=redis://localhost:6379/0

# Start Redis (separate terminal)
docker run -d -p 6379:6379 redis:alpine

# Run application
uvicorn app.main:app --reload --port 8080
```

---

## Docker Commands

### Build Image

```bash
# Development build
docker compose build

# Production build (no cache)
docker compose build --no-cache

# Build with specific tag
docker build -t ubi-connector:v1.0.0 .
```

### Run Containers

```bash
# Start all services (detached)
docker compose up -d

# Start with logs visible
docker compose up

# Start specific service
docker compose up api

# Production mode (skip override file)
docker compose -f docker-compose.yml up -d
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api
```

### Stop & Cleanup

```bash
# Stop services
docker compose down

# Stop and remove volumes (DATA LOSS!)
docker compose down -v

# Remove unused images
docker image prune
```

---

## Production Checklist

### Pre-Deployment

- [ ] **Generate production encryption key**
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  Store this securely (AWS Secrets Manager, Vault, etc.)

- [ ] **Configure Redis**
  - Provision Redis with persistence (AWS ElastiCache, Redis Cloud, etc.)
  - Enable TLS for network encryption
  - Set appropriate maxmemory (256MB minimum)

- [ ] **Set all required environment variables**
  - `UBI_SECRET_KEY` - Encryption key
  - `REDIS_URL` - Redis connection string
  - `ENV=production`

- [ ] **Review security settings**
  - `RATE_LIMIT_ENABLED=true`
  - `SAFETY_GUARDS_ENABLED=true`
  - `CACHE_ADMIN_BYPASS=false`

- [ ] **Configure logging**
  - Set up log aggregation (CloudWatch, Datadog, etc.)
  - Configure `LOG_LEVEL=INFO` (not DEBUG)

### Deployment

- [ ] **Deploy to container orchestrator**
  - Kubernetes, ECS, Cloud Run, etc.
  - Configure health checks
  - Set resource limits

- [ ] **Configure networking**
  - TLS termination at load balancer
  - Private network for Redis
  - Firewall rules

- [ ] **Set up monitoring**
  - Uptime monitoring on `/v1/health`
  - Alerting on 5xx errors
  - Redis memory alerts

### Post-Deployment

- [ ] **Verify deployment**
  ```bash
  curl https://your-domain/v1/health
  ```

- [ ] **Test BI tool connectivity**
  - Power BI: Connect via OData Feed
  - Tableau: Test WDC connection

- [ ] **Configure backups**
  - Schedule sources.db backup
  - Document encryption key recovery

---

## Required Secrets

| Secret | Purpose | Rotation |
|--------|---------|----------|
| `UBI_SECRET_KEY` | Encrypt source credentials | Yearly (re-encrypt sources) |
| `REDIS_URL` (password) | Redis authentication | As needed |
| API Keys | Client authentication | Per tenant policy |

### Secret Management Options

**AWS**:
```yaml
# ECS Task Definition
secrets:
  - name: UBI_SECRET_KEY
    valueFrom: arn:aws:secretsmanager:region:account:secret:ubi-secret-key
```

**Kubernetes**:
```yaml
# See k8s/secret.yaml
envFrom:
  - secretRef:
      name: ubi-connector-secrets
```

**Docker**:
```bash
# Docker secrets (Swarm mode)
echo "your-key" | docker secret create ubi_secret_key -
```

---

## Redis Sizing

### Memory Requirements

| Workload | Queries/day | Recommended Memory |
|----------|-------------|-------------------|
| Small | < 10,000 | 128 MB |
| Medium | 10,000 - 100,000 | 256 MB |
| Large | 100,000 - 1,000,000 | 512 MB - 1 GB |
| Enterprise | > 1,000,000 | 2 GB+ |

### Configuration

```conf
# Redis configuration for production
maxmemory 256mb
maxmemory-policy allkeys-lru  # Evict least recently used keys
appendonly yes                 # Enable persistence
appendfsync everysec          # Sync every second
```

### High Availability

For production:
- Use Redis Sentinel (3+ nodes) for automatic failover
- Or use Redis Cluster for horizontal scaling
- Or use managed Redis (ElastiCache, Redis Cloud)

---

## Scaling Strategy

### Horizontal Scaling (API)

The API is stateless and scales horizontally:

```yaml
# Kubernetes
spec:
  replicas: 3  # Adjust based on load
```

```yaml
# Docker Compose with replicas
deploy:
  replicas: 3
```

### Load Balancer Configuration

```nginx
# nginx.conf example
upstream ubi_api {
    least_conn;  # Route to least busy server
    server api-1:8080;
    server api-2:8080;
    server api-3:8080;
}
```

### Scaling Triggers

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU | > 70% for 2 min | < 30% for 5 min |
| Memory | > 80% | < 40% |
| Request latency | p95 > 2s | p95 < 500ms |

---

## Backup Strategy

### What to Backup

1. **sources.db** - Encrypted source credentials
2. **Encryption key** - Required to decrypt sources.db
3. **catalog.yaml** - Semantic layer definitions

### Backup Script

```bash
#!/bin/bash
# backup.sh - Run daily via cron

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/ubi-connector"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup sources database from Docker volume
docker cp ubi-api:/app/app/db/sources.db $BACKUP_DIR/sources_$DATE.db

# Compress
gzip $BACKUP_DIR/sources_$DATE.db

# Upload to S3 (example)
aws s3 cp $BACKUP_DIR/sources_$DATE.db.gz s3://my-bucket/backups/

# Cleanup old local backups (keep 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: sources_$DATE.db.gz"
```

### Restore Process

```bash
# Stop API
docker compose stop api

# Restore database
gunzip sources_backup.db.gz
docker cp sources_backup.db ubi-api:/app/app/db/sources.db

# Restart API
docker compose start api
```

---

## Log Aggregation

### Log Format

Logs are structured with request IDs:

```
2025-12-23 11:45:32 - app.main - INFO - [abc12345] Query: dataset=orders tenant=tenantA
```

### Docker Logging

```yaml
# docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### CloudWatch (AWS)

```yaml
# ECS Task Definition
logConfiguration:
  logDriver: awslogs
  options:
    awslogs-group: /ecs/ubi-connector
    awslogs-region: us-east-1
    awslogs-stream-prefix: api
```

### Datadog

```yaml
# docker-compose.yml
services:
  api:
    labels:
      com.datadoghq.ad.logs: '[{"source": "python", "service": "ubi-connector"}]'
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `GET /v1/health` | Basic health | No |
| `GET /internal/status` | Detailed status | Yes (internal-admin-key) |

### Load Balancer Health Check

```nginx
# nginx or ALB
location /health {
    proxy_pass http://api:8080/v1/health;
    proxy_connect_timeout 5s;
    proxy_read_timeout 5s;
}
```

### Kubernetes Probes

```yaml
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
```

---

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker compose logs api

# Common issues:
# - Missing UBI_SECRET_KEY → Set in .env
# - Redis not ready → Check redis health
# - Port conflict → Change API_PORT
```

### Redis Connection Failed

```bash
# Test Redis connectivity
docker compose exec api redis-cli -u $REDIS_URL ping

# Check Redis logs
docker compose logs redis
```

### Permission Denied on sources.db

```bash
# Fix permissions
docker compose exec api chown -R appuser:appuser /app/app/db
```

### High Memory Usage

```bash
# Check container stats
docker stats ubi-api

# Possible causes:
# - QUERY_MAX_ROWS too high
# - Large cached results
# - Memory leak (report bug)
```

---

## Support

- **Documentation**: See `README.md` and `PRODUCTION_READINESS.md`
- **API Reference**: http://localhost:8080/docs
- **Issues**: GitHub Issues

