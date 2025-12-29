# Deployment

Deploy SetuPranali to production.

---

## Deployment Options

<div class="grid cards" markdown>

-   :material-docker:{ .lg .middle } **Docker**

    ---

    Single container or Docker Compose deployment.

    [:octicons-arrow-right-24: Docker Guide](docker.md)

-   :material-kubernetes:{ .lg .middle } **Kubernetes**

    ---

    Scalable Kubernetes deployment with Helm.

    [:octicons-arrow-right-24: Kubernetes Guide](kubernetes.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Environment variables and settings.

    [:octicons-arrow-right-24: Configuration](configuration.md)

-   :material-clipboard-check:{ .lg .middle } **Production Checklist**

    ---

    Pre-launch verification steps.

    [:octicons-arrow-right-24: Checklist](production-checklist.md)

</div>

---

## Quick Start

### Docker

```bash
docker run -d \
  --name ubi-connector \
  -p 8080:8080 \
  -e UBI_SECRET_KEY=$(openssl rand -base64 32) \
  -v $(pwd)/catalog.yaml:/app/catalog.yaml \
  adeygifting/connector:latest
```

### Docker Compose

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
    volumes:
      - ./catalog.yaml:/app/catalog.yaml
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
```

---

## Architecture

### Minimal Setup

```
┌─────────────────────────────────┐
│  SetuPranali (8080)  │
└─────────────────────────────────┘
```

### Production Setup

```
┌─────────────────────────────────────────────────────┐
│                  Load Balancer                       │
│                  (HTTPS/TLS)                         │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
  │ Connector │  │ Connector │  │ Connector │
  │  (8080)   │  │  (8080)   │  │  (8080)   │
  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
              ┌────────▼────────┐
              │  Redis Cluster  │
              └─────────────────┘
```

---

## Resource Requirements

### Minimum

| Resource | Value |
|----------|-------|
| CPU | 1 core |
| Memory | 512 MB |
| Storage | 100 MB |

### Recommended

| Resource | Value |
|----------|-------|
| CPU | 2+ cores |
| Memory | 2+ GB |
| Storage | 1 GB |

---

## Scaling

### Horizontal Scaling

Add more connector replicas:

```yaml
# docker-compose.yml
services:
  connector:
    deploy:
      replicas: 3
```

### Vertical Scaling

Increase resources per instance:

```yaml
services:
  connector:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

---

## Health Monitoring

### Health Endpoint

```bash
curl http://localhost:8080/health
```

### Docker Health Check

```yaml
services:
  connector:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
```

