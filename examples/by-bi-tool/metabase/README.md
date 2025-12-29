# Metabase Integration Examples

Connect Metabase to SetuPranali using the native driver.

## Overview

SetuPranali provides a **native Metabase driver** for seamless integration:
- Appears as a database type in Metabase
- Full SQL support
- Automatic schema discovery
- Row-level security

## Quick Start

### 1. Install the Driver

```bash
# Download the driver JAR
curl -L -o setupranali.jar \
  https://github.com/setupranali/setupranali.github.io/releases/latest/download/setupranali-driver.jar

# Copy to Metabase plugins directory
cp setupranali.jar /path/to/metabase/plugins/
```

### 2. Restart Metabase

```bash
# Docker
docker restart metabase

# Or if running directly
systemctl restart metabase
```

### 3. Add Database Connection

1. Go to **Admin** → **Databases** → **Add Database**
2. Select **SetuPranali** as database type
3. Configure:
   - **Host**: `localhost`
   - **Port**: `8080`
   - **API Key**: `your_api_key`
4. Click **Save**

## Connection Configuration

### Basic Setup

| Field | Value |
|-------|-------|
| Host | `localhost` |
| Port | `8080` |
| API Key | `your_api_key` |
| SSL | Enabled for production |

### With SSL

| Field | Value |
|-------|-------|
| Host | `setupranali.example.com` |
| Port | `443` |
| API Key | `your_api_key` |
| Use SSL | ✓ |

## Features

### Automatic Schema Discovery

Metabase automatically discovers:
- All datasets
- Dimensions and metrics
- Data types
- Relationships (if defined)

### Native Questions

Create questions using Metabase's visual query builder:

1. Click **New** → **Question**
2. Select your SetuPranali database
3. Choose a dataset
4. Add dimensions and metrics
5. Apply filters
6. Visualize!

### SQL Mode

Write SQL queries directly:

```sql
SELECT 
  order_month,
  region,
  SUM(revenue) as total_revenue,
  COUNT(order_id) as order_count
FROM orders
WHERE status = 'delivered'
GROUP BY order_month, region
ORDER BY total_revenue DESC
```

### Dashboard Creation

1. Create questions
2. Click **New** → **Dashboard**
3. Add questions to dashboard
4. Add filters that apply across questions

## Row-Level Security

### Per-User API Keys

Create different API keys for different teams:

```yaml
# SetuPranali catalog.yaml
api_keys:
  metabase_sales_key:
    tenant_id: "sales"
  metabase_marketing_key:
    tenant_id: "marketing"
```

### Groups in Metabase

1. Create groups in Metabase (Sales, Marketing)
2. Create separate database connections per group
3. Assign users to appropriate groups

## Docker Setup

```yaml
version: '3.8'
services:
  setupranali:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"
    volumes:
      - ./catalog.yaml:/app/catalog.yaml

  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    volumes:
      - ./plugins:/plugins
      - metabase_data:/metabase-data
    environment:
      - MB_PLUGINS_DIR=/plugins

volumes:
  metabase_data:
```

## Troubleshooting

### Driver Not Appearing

1. Check JAR is in plugins directory
2. Restart Metabase completely
3. Check Metabase logs for errors

### Connection Failed

1. Verify SetuPranali is running
2. Check host/port configuration
3. Test API key with curl:

```bash
curl http://localhost:8080/v1/datasets \
  -H "Authorization: Bearer your_api_key"
```

### Slow Queries

1. Enable caching in SetuPranali
2. Create saved questions instead of ad-hoc
3. Use sync schedules appropriately

## Alternative: HTTP API Driver

If you can't install the native driver, use Metabase's HTTP API driver:

1. Add database → HTTP
2. Base URL: `http://setupranali:8080/v1`
3. Configure authentication header

## Files in This Example

```
metabase/
├── README.md
├── docker-compose.yml
├── plugins/
│   └── setupranali.jar
└── screenshots/
    ├── add-database.png
    ├── create-question.png
    └── sample-dashboard.png
```

## Best Practices

1. **Use Native Driver** - Better performance and features
2. **Enable Caching** - Reduce load on data sources
3. **Sync Schedules** - Configure appropriate sync frequency
4. **Saved Questions** - Reuse common queries
5. **Data Model** - Configure in Admin → Data Model for better UX

