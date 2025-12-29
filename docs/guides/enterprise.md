# Enterprise Features

SetuPranali provides enterprise-grade capabilities for large-scale deployments.

## Overview

| Feature | Description | Status |
|---------|-------------|--------|
| **Tableau Hyper Export** | Export datasets as Hyper files | ✅ Available |
| **Power BI Push Datasets** | Push data directly to Power BI | ✅ Available |
| **Embedded Analytics** | Embed-ready endpoints with tokens | ✅ Available |
| **White-Label Support** | Custom branding for OEM deployments | ✅ Available |
| **Multi-Region Deployment** | Geo-distributed caching and routing | ✅ Available |

---

## Tableau Hyper Export

Export query results and datasets as Tableau Hyper files for high-performance analytics.

### Export Dataset

```bash
curl -X POST "http://localhost:8080/v1/enterprise/hyper/export" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "dataset_id": "orders",
    "output_path": "/exports/orders.hyper",
    "data": [
      {"order_id": "1", "region": "US", "revenue": 1000},
      {"order_id": "2", "region": "EU", "revenue": 2000}
    ]
  }'
```

### Export Query Results

```bash
curl -X POST "http://localhost:8080/v1/enterprise/hyper/export-query" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "output_path": "/exports/query_result.hyper",
    "table_name": "SalesData",
    "data": [{"region": "US", "total_revenue": 125000}]
  }'
```

### Export Multiple Datasets

```bash
curl -X POST "http://localhost:8080/v1/enterprise/hyper/export-multiple" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "output_path": "/exports/analytics.hyper",
    "datasets": {
      "orders": [{"order_id": "1", "revenue": 1000}],
      "customers": [{"customer_id": "c1", "name": "Acme"}]
    }
  }'
```

### Requirements

Install the Tableau Hyper API:

```bash
pip install tableauhyperapi
```

---

## Power BI Push Datasets

Push data directly to Power BI Service. See [Ecosystem Integrations](ecosystem.md#power-bi-service-sync) for full documentation.

```bash
# Push data to Power BI
curl -X POST "http://localhost:8080/v1/ecosystem/powerbi/push" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "dataset_id": "dataset-guid",
    "table_name": "orders",
    "data": [
      {"order_id": "1", "region": "US", "revenue": 1000}
    ]
  }'
```

---

## Embedded Analytics

Embed SetuPranali analytics in your applications with secure, scoped tokens.

### Create Embed Token

```bash
curl -X POST "http://localhost:8080/v1/enterprise/embed/token" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "datasets": ["orders", "customers"],
    "permissions": ["query", "filter", "export"],
    "filters": {"region": "US"},
    "rls_context": {"tenant_id": "acme"},
    "expiry_hours": 24,
    "max_rows": 10000,
    "allowed_dimensions": ["region", "product_category"],
    "allowed_metrics": ["revenue", "order_count"]
  }'
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "type": "embed",
  "expires_in_hours": 24
}
```

### Get Embed Code

```bash
# Get iframe HTML
curl -X POST "http://localhost:8080/v1/enterprise/embed/code" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "format": "iframe",
    "config": {
      "theme": "dark",
      "show_toolbar": true,
      "show_filters": true,
      "show_export": false
    }
  }'
```

Response:
```json
{
  "html": "<iframe src=\"http://localhost:8080/embed/view?token=...\" width=\"100%\" height=\"600px\"></iframe>",
  "url": "http://localhost:8080/embed/view?token=..."
}
```

### Embed Permissions

| Permission | Description |
|------------|-------------|
| `query` | Execute queries |
| `filter` | Apply filters |
| `export` | Export data |
| `explore` | Explore datasets |
| `drill` | Drill down/up |

### Embedding in Your App

**React:**
```jsx
function AnalyticsEmbed({ token }) {
  return (
    <iframe
      src={`https://your-setupranali.com/embed/view?token=${token}`}
      width="100%"
      height="600px"
      frameBorder="0"
      allow="clipboard-write"
    />
  );
}
```

**JavaScript SDK:**
```html
<script src="https://your-setupranali.com/embed/sdk.js"></script>
<div id="analytics-container"></div>
<script>
  SetuPranali.embed({
    container: '#analytics-container',
    token: 'your-embed-token',
    theme: 'dark',
    onReady: () => console.log('Analytics loaded')
  });
</script>
```

---

## White-Label Support

Customize branding for OEM deployments and multi-tenant environments.

### Set Branding

```bash
curl -X PUT "http://localhost:8080/v1/enterprise/branding" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "colors": {
      "primary": "#FF5722",
      "secondary": "#2196F3",
      "accent": "#4CAF50"
    },
    "assets": {
      "logoUrl": "https://your-company.com/logo.svg",
      "faviconUrl": "https://your-company.com/favicon.ico"
    },
    "text": {
      "companyName": "Your Company",
      "productName": "Your Analytics",
      "tagline": "Insights that matter",
      "supportEmail": "support@your-company.com"
    },
    "custom_domain": "analytics.your-company.com"
  }'
```

### Get Branding

```bash
# Get branding for current tenant
curl "http://localhost:8080/v1/enterprise/branding" \
  -H "Authorization: Bearer sk_demo_123"

# Get branding by custom domain
curl "http://localhost:8080/v1/enterprise/branding/domain/analytics.your-company.com"
```

### Get Generated CSS

```bash
# Get full CSS
curl "http://localhost:8080/v1/enterprise/branding/css" \
  -H "Authorization: Bearer sk_demo_123"

# Get CSS variables only
curl "http://localhost:8080/v1/enterprise/branding/css-variables" \
  -H "Authorization: Bearer sk_demo_123"
```

### Branding Configuration

```yaml
# white_label.yaml
default:
  enabled: true
  colors:
    primary: "#6366F1"
    secondary: "#8B5CF6"
  text:
    company_name: "SetuPranali"
    product_name: "Analytics"

tenants:
  acme:
    enabled: true
    colors:
      primary: "#FF5722"
      secondary: "#2196F3"
    assets:
      logo_url: "https://acme.com/logo.svg"
    text:
      company_name: "Acme Analytics"
    custom_domain: "analytics.acme.com"
```

---

## Multi-Region Deployment

Deploy SetuPranali across multiple regions for low latency and data residency.

### Register Regions

```bash
# Register US region
curl -X POST "http://localhost:8080/v1/enterprise/regions" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "region_id": "us-east-1",
    "name": "US East",
    "endpoint": "https://us-east.setupranali.com",
    "priority": 1,
    "weight": 100,
    "is_primary": true,
    "latitude": 37.7749,
    "longitude": -122.4194
  }'

# Register EU region with data residency
curl -X POST "http://localhost:8080/v1/enterprise/regions" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "region_id": "eu-west-1",
    "name": "EU West",
    "endpoint": "https://eu-west.setupranali.com",
    "priority": 2,
    "weight": 100,
    "data_residency": ["DE", "FR", "GB", "NL"],
    "latitude": 52.3676,
    "longitude": 4.9041
  }'
```

### Select Optimal Region

```bash
# By geo-location
curl -X POST "http://localhost:8080/v1/enterprise/regions/select" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "latitude": 51.5074,
    "longitude": -0.1278
  }'

# By country (data residency)
curl -X POST "http://localhost:8080/v1/enterprise/regions/select" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "country_code": "DE"
  }'
```

### Routing Strategies

| Strategy | Description |
|----------|-------------|
| `priority` | Route to highest priority healthy region |
| `latency` | Route to lowest latency region |
| `geo` | Route to geographically closest region |
| `residency` | Route based on data residency requirements |
| `weighted` | Weighted random distribution |

```bash
# Set routing strategy
curl -X PUT "http://localhost:8080/v1/enterprise/regions/strategy/geo" \
  -H "Authorization: Bearer sk_demo_123"
```

### Region Health

```bash
# List all regions with health
curl "http://localhost:8080/v1/enterprise/regions" \
  -H "Authorization: Bearer sk_demo_123"

# Get specific region health
curl "http://localhost:8080/v1/enterprise/regions/us-east-1/health" \
  -H "Authorization: Bearer sk_demo_123"
```

Response:
```json
{
  "region_id": "us-east-1",
  "status": "healthy",
  "latency_ms": 45.2,
  "error_rate": 0.001,
  "cache_hit_rate": 0.94,
  "active_connections": 128,
  "last_check": "2024-01-15T10:30:00Z"
}
```

### Distributed Cache

```bash
# Get cache stats
curl "http://localhost:8080/v1/enterprise/regions/cache/stats" \
  -H "Authorization: Bearer sk_demo_123"

# Sync cache between regions
curl -X POST "http://localhost:8080/v1/enterprise/regions/cache/sync" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "from_region": "us-east-1",
    "to_region": "eu-west-1"
  }'
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Global Load Balancer                      │
│                 (Latency/Geo-based routing)                  │
└─────────────────────┬───────────────────┬───────────────────┘
                      │                   │
        ┌─────────────▼─────────┐ ┌───────▼──────────────┐
        │     US Region         │ │     EU Region        │
        │  ┌─────────────────┐  │ │ ┌─────────────────┐  │
        │  │  SetuPranali    │  │ │ │  SetuPranali    │  │
        │  │   Instances     │  │ │ │   Instances     │  │
        │  └────────┬────────┘  │ │ └────────┬────────┘  │
        │           │           │ │          │          │
        │  ┌────────▼────────┐  │ │ ┌────────▼────────┐  │
        │  │  Redis Cache    │◄─┼─┼─► Redis Cache    │  │
        │  └─────────────────┘  │ │ └─────────────────┘  │
        │                       │ │                     │
        │  ┌─────────────────┐  │ │ ┌─────────────────┐  │
        │  │  Data Sources   │  │ │ │  Data Sources   │  │
        │  └─────────────────┘  │ │ └─────────────────┘  │
        └───────────────────────┘ └─────────────────────┘
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBED_SECRET_KEY` | Secret for embed tokens | `UBI_SECRET_KEY` |
| `EMBED_TOKEN_EXPIRY_HOURS` | Default token expiry | `24` |
| `EMBED_ALLOWED_ORIGINS` | CORS origins for embeds | `*` |
| `WHITE_LABEL_CONFIG` | Path to branding config | `white_label.yaml` |
| `ROUTING_STRATEGY` | Default routing strategy | `priority` |
| `BASE_URL` | Base URL for embed links | `http://localhost:8080` |

### Docker Compose Example

```yaml
version: '3.8'

services:
  setupranali-us:
    image: setupranali/connector
    environment:
      - REGION_ID=us-east-1
      - IS_PRIMARY=true
      - REDIS_URL=redis://redis-us:6379
    deploy:
      replicas: 3

  setupranali-eu:
    image: setupranali/connector
    environment:
      - REGION_ID=eu-west-1
      - DATA_RESIDENCY=DE,FR,GB,NL
      - REDIS_URL=redis://redis-eu:6379
    deploy:
      replicas: 3

  redis-us:
    image: redis:7-alpine

  redis-eu:
    image: redis:7-alpine
```

---

## API Reference

### Tableau Hyper Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/enterprise/hyper/export` | Export dataset |
| POST | `/v1/enterprise/hyper/export-query` | Export query results |
| POST | `/v1/enterprise/hyper/export-multiple` | Export multiple datasets |

### Embedded Analytics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/enterprise/embed/token` | Create embed token |
| POST | `/v1/enterprise/embed/code` | Get embed code |
| POST | `/v1/enterprise/embed/query` | Validate embed query |
| GET | `/v1/enterprise/embed/tokens` | List tokens |
| DELETE | `/v1/enterprise/embed/token/{id}` | Revoke token |

### White-Label Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/enterprise/branding` | Get branding |
| PUT | `/v1/enterprise/branding` | Set branding |
| GET | `/v1/enterprise/branding/css` | Get CSS |
| GET | `/v1/enterprise/branding/domain/{domain}` | Get by domain |
| DELETE | `/v1/enterprise/branding/{tenant_id}` | Delete branding |

### Multi-Region Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/enterprise/regions` | Register region |
| DELETE | `/v1/enterprise/regions/{id}` | Unregister region |
| GET | `/v1/enterprise/regions` | List regions |
| GET | `/v1/enterprise/regions/{id}/health` | Get health |
| POST | `/v1/enterprise/regions/select` | Select region |
| PUT | `/v1/enterprise/regions/strategy/{strategy}` | Set strategy |
| GET | `/v1/enterprise/regions/cache/stats` | Cache stats |
| POST | `/v1/enterprise/regions/cache/sync` | Sync cache |

