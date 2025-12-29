# Docker Deployment

Deploy SetuPranali with Docker.

---

## Quick Start

```bash
docker run -d \
  --name ubi-connector \
  -p 8080:8080 \
  -e UBI_SECRET_KEY=$(openssl rand -base64 32) \
  adeygifting/connector:latest
```

---

## Docker Compose

### Basic Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  connector:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"
    environment:
      - UBI_SECRET_KEY=${UBI_SECRET_KEY}
    volumes:
      - ./catalog.yaml:/app/catalog.yaml:ro
```

### With Redis

```yaml
version: '3.8'

services:
  connector:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"
    environment:
      - UBI_SECRET_KEY=${UBI_SECRET_KEY}
      - REDIS_URL=redis://redis:6379
      - CACHE_TTL_SECONDS=300
    volumes:
      - ./catalog.yaml:/app/catalog.yaml:ro
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis-data:
```

### Start

```bash
# Create .env with secret key
echo "UBI_SECRET_KEY=$(openssl rand -base64 32)" > .env

# Start services
docker compose up -d

# View logs
docker compose logs -f connector
```

---

## Configuration

### Environment File

```bash
# .env
UBI_SECRET_KEY=your-secret-key-here
REDIS_URL=redis://redis:6379
CACHE_TTL_SECONDS=300
RATE_LIMIT_QUERY=100/minute
MAX_ROWS=100000
```

### Volume Mounts

| Mount | Purpose |
|-------|---------|
| `/app/catalog.yaml` | Semantic catalog |
| `/app/data` | SQLite sources database |

---

## Production Configuration

```yaml
version: '3.8'

services:
  connector:
    image: adeygifting/connector:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - UBI_SECRET_KEY=${UBI_SECRET_KEY}
      - REDIS_URL=redis://redis:6379
      - CACHE_TTL_SECONDS=300
      - RATE_LIMIT_QUERY=100/minute
      - MAX_ROWS=100000
      - LOG_LEVEL=INFO
    volumes:
      - ./catalog.yaml:/app/catalog.yaml:ro
      - ./data:/app/data
    depends_on:
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis-data:
```

---

## Scaling

### Multiple Replicas

```yaml
services:
  connector:
    deploy:
      replicas: 3
```

### With Load Balancer

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - connector

  connector:
    deploy:
      replicas: 3
```

nginx.conf:

```nginx
events {}

http {
    upstream connectors {
        server connector:8080;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://connectors;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

## Maintenance

### Update Image

```bash
docker compose pull
docker compose up -d
```

### View Logs

```bash
docker compose logs -f connector
```

### Restart

```bash
docker compose restart connector
```

### Backup Data

```bash
docker compose exec connector tar -czf - /app/data > backup.tar.gz
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs connector

# Check container status
docker compose ps
```

### Connection Refused

```bash
# Verify port mapping
docker compose ps

# Test from inside container
docker compose exec connector curl localhost:8080/health
```

### Redis Connection Failed

```bash
# Check Redis is running
docker compose exec redis redis-cli ping

# Verify REDIS_URL
docker compose exec connector env | grep REDIS
```

