# Installation

This guide covers all installation methods for SetuPranali.

---

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| Memory | 512 MB | 2+ GB |
| Python | 3.9+ | 3.11+ |
| Redis | 6.0+ | 7.0+ (optional) |

---

## Docker (Recommended)

The fastest way to get started.

### Quick Start

```bash
docker run -d \
  --name ubi-connector \
  -p 8080:8080 \
  -v $(pwd)/catalog.yaml:/app/catalog.yaml \
  adeygifting/connector:latest
```

### With Environment Variables

```bash
docker run -d \
  --name ubi-connector \
  -p 8080:8080 \
  -e UBI_SECRET_KEY=$(openssl rand -base64 32) \
  -e REDIS_URL=redis://redis:6379 \
  -e CACHE_TTL_SECONDS=300 \
  -v $(pwd)/catalog.yaml:/app/catalog.yaml \
  adeygifting/connector:latest
```

### Docker Compose

Create a `docker-compose.yml`:

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
      - RATE_LIMIT_QUERY=100/minute
    volumes:
      - ./catalog.yaml:/app/catalog.yaml:ro
      - ./data:/app/data
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

Start the stack:

```bash
# Generate secret key
echo "UBI_SECRET_KEY=$(openssl rand -base64 32)" > .env

# Start services
docker compose up -d

# View logs
docker compose logs -f connector
```

---

## Kubernetes

For production deployments.

### Using Helm

```bash
# Add the Helm repository
helm repo add setupranali https://charts.setupranali.io
helm repo update

# Install with default values
helm install ubi-connector adeygifting/connector

# Or with custom values
helm install ubi-connector adeygifting/connector \
  --set replicaCount=3 \
  --set redis.enabled=true \
  --set ingress.enabled=true \
  --set ingress.host=bi-api.example.com
```

### Manual Deployment

Apply the Kubernetes manifests:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

See [Kubernetes Deployment](../deployment/kubernetes.md) for complete manifests.

---

## From Source

For development or customization.

### Clone the Repository

```bash
git clone https://github.com/setupranali/setupranali.github.io.git
cd setupranali
```

### Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

### Configure Environment

```bash
# Copy example config
cp env.example .env

# Edit with your settings
vim .env
```

Minimum required settings:

```bash
# .env
UBI_SECRET_KEY=your-secret-key-here
```

### Start the Server

```bash
# Development mode (with auto-reload)
python -m uvicorn app.main:app --reload --port 8080

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

---

## Database Drivers

Install drivers for your data sources:

=== "All Drivers"

    ```bash
    pip install -r requirements.txt
    ```

=== "PostgreSQL"

    ```bash
    pip install psycopg2-binary
    ```

=== "MySQL"

    ```bash
    pip install mysql-connector-python
    ```

=== "Snowflake"

    ```bash
    pip install snowflake-connector-python
    ```

=== "BigQuery"

    ```bash
    pip install google-cloud-bigquery db-dtypes
    ```

=== "Databricks"

    ```bash
    pip install databricks-sql-connector
    ```

=== "Redshift"

    ```bash
    pip install redshift-connector
    ```

=== "ClickHouse"

    ```bash
    pip install clickhouse-connect
    ```

---

## Verify Installation

After installation, verify everything works:

```bash
# Check health endpoint
curl http://localhost:8080/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "redis": "connected",
  "sources": 0,
  "datasets": 0
}
```

Check the API documentation:

```bash
# Open in browser
open http://localhost:8080/docs
```

---

## Configuration

See [Configuration Reference](../deployment/configuration.md) for all options.

### Essential Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `UBI_SECRET_KEY` | Encryption key for sources | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `CACHE_TTL_SECONDS` | Query cache duration | `300` |
| `RATE_LIMIT_QUERY` | Query rate limit | `100/minute` |

---

## Next Steps

<div class="grid cards" markdown>

-   **Quick Start**

    ---

    Get your first query running.

    [:octicons-arrow-right-24: Quick Start](quickstart.md)

-   **Add Data Sources**

    ---

    Connect your databases.

    [:octicons-arrow-right-24: Data Sources](../integrations/sources/index.md)

-   **Configure Security**

    ---

    Set up API keys and RLS.

    [:octicons-arrow-right-24: Security](../concepts/security.md)

</div>

