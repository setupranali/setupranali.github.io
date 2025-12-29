# Metabase Integration

Connect Metabase to your data warehouse through SetuPranali's semantic layer.

## Overview

SetuPranali integrates with Metabase in two ways:

1. **HTTP API Driver** - Query SetuPranali's REST API directly
2. **Database Proxy** - Use SetuPranali as a governance layer

---

## Method 1: HTTP API Integration (Recommended)

### Step 1: Install HTTP Driver

Metabase supports custom drivers. Install the HTTP driver:

```bash
# Download the HTTP driver
curl -L -o metabase-http-driver.jar \
  https://github.com/server/metabase-http-driver/releases/latest/download/http-driver.jar

# Copy to Metabase plugins directory
cp metabase-http-driver.jar /path/to/metabase/plugins/
```

### Step 2: Configure Connection

1. Go to **Admin → Databases → Add database**
2. Select **HTTP** as database type
3. Configure:

```yaml
Base URL: http://setupranali:8080/v1
Headers:
  X-API-Key: your-api-key
  Content-Type: application/json
```

### Step 3: Create Questions

Use Metabase's native query mode to query SetuPranali:

```json
{
  "dataset": "orders",
  "dimensions": ["customer_name", "order_date"],
  "measures": ["total_revenue"],
  "filters": [
    {"field": "order_date", "operator": ">=", "value": "2024-01-01"}
  ],
  "limit": 1000
}
```

---

## Method 2: Using Metabase REST API Sync

Create a sync script to expose SetuPranali datasets in Metabase:

### `sync_metabase.py`

```python
"""
Sync SetuPranali datasets to Metabase as saved questions
"""

import requests
import os

SETUPRANALI_URL = os.getenv('SETUPRANALI_URL', 'http://localhost:8080')
SETUPRANALI_KEY = os.getenv('SETUPRANALI_API_KEY')
METABASE_URL = os.getenv('METABASE_URL', 'http://localhost:3000')
METABASE_USER = os.getenv('METABASE_USER')
METABASE_PASS = os.getenv('METABASE_PASS')

def get_metabase_session():
    """Get Metabase session token"""
    response = requests.post(f'{METABASE_URL}/api/session', json={
        'username': METABASE_USER,
        'password': METABASE_PASS
    })
    return response.json()['id']

def get_setupranali_datasets():
    """Fetch datasets from SetuPranali"""
    response = requests.get(
        f'{SETUPRANALI_URL}/v1/datasets',
        headers={'X-API-Key': SETUPRANALI_KEY}
    )
    return response.json()

def create_metabase_question(session, dataset):
    """Create a Metabase question for a SetuPranali dataset"""
    question = {
        'name': f"SetuPranali: {dataset['name']}",
        'description': dataset.get('description', ''),
        'display': 'table',
        'visualization_settings': {},
        'dataset_query': {
            'type': 'native',
            'native': {
                'query': f'''
                    -- SetuPranali Dataset: {dataset['id']}
                    -- This queries through the SetuPranali API
                    SELECT * FROM {dataset['id']} LIMIT 1000
                ''',
                'template-tags': {}
            },
            'database': 1  # Your database ID
        }
    }
    
    response = requests.post(
        f'{METABASE_URL}/api/card',
        headers={'X-Metabase-Session': session},
        json=question
    )
    return response.json()

def main():
    session = get_metabase_session()
    datasets = get_setupranali_datasets()
    
    for dataset in datasets.get('items', []):
        print(f"Creating question for: {dataset['name']}")
        result = create_metabase_question(session, dataset)
        print(f"  Created: {result.get('id')}")

if __name__ == '__main__':
    main()
```

---

## Method 3: Database Proxy Mode

Connect Metabase to your data warehouse directly, using SetuPranali for governance:

### Architecture

```
┌──────────┐     ┌─────────────┐     ┌───────────────┐
│ Metabase │────▶│ SetuPranali │────▶│ Data Warehouse│
└──────────┘     └─────────────┘     └───────────────┘
     │                  │
     │    REST API      │    RLS + Caching
     │                  │
```

### Docker Compose Setup

```yaml
version: '3.8'
services:
  setupranali:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./catalog.yaml:/app/catalog.yaml

  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    environment:
      - MB_DB_TYPE=h2
    depends_on:
      - setupranali

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Configure Metabase Database

In Metabase Admin:

1. **Add Database** → Select your warehouse type (PostgreSQL, Snowflake, etc.)
2. Configure connection through SetuPranali:
   - Host: `setupranali` (Docker service name)
   - Port: `8080`

---

## Embedding SetuPranali in Metabase

Use Metabase's embedding to create dashboards with SetuPranali data:

### Enable Embedding

1. **Admin → Settings → Embedding**
2. Enable **Signed embedding**
3. Copy the **Embedding secret key**

### Embed a Question

```javascript
// Generate signed embed URL
const jwt = require('jsonwebtoken');

const payload = {
  resource: { question: 123 },
  params: {
    tenant_id: 'acme-corp'  // Pass to SetuPranali for RLS
  },
  exp: Math.round(Date.now() / 1000) + (10 * 60) // 10 minutes
};

const token = jwt.sign(payload, METABASE_SECRET_KEY);
const embedUrl = `${METABASE_URL}/embed/question/${token}`;
```

---

## Row-Level Security

### Per-User API Keys

Create tenant-specific API keys for Metabase groups:

```bash
# Create API key for sales team
curl -X POST http://localhost:8080/v1/sources/api-keys \
  -H "X-Internal-Admin-Key: admin-key" \
  -d '{"name": "metabase-sales", "tenant_id": "sales-team"}'

# Create API key for marketing team  
curl -X POST http://localhost:8080/v1/sources/api-keys \
  -H "X-Internal-Admin-Key: admin-key" \
  -d '{"name": "metabase-marketing", "tenant_id": "marketing-team"}'
```

### Configure in Metabase

Use Metabase's **User Groups** to assign different database connections:

1. Create group: "Sales Team"
2. Add database connection with sales API key
3. Assign users to group
4. They automatically see only sales data

---

## Performance Optimization

### Enable Caching

SetuPranali caches queries automatically when Redis is available:

```yaml
# docker-compose.yml
services:
  setupranali:
    environment:
      - REDIS_URL=redis://redis:6379
      - CACHE_TTL=300  # 5 minutes
```

### Metabase Query Caching

Additionally, enable Metabase's caching:

1. **Admin → Settings → Caching**
2. Set **Minimum Query Duration** to cache
3. Configure **Cache TTL**

---

## Troubleshooting

### Connection Failed

```bash
# Test SetuPranali from Metabase container
docker exec metabase curl http://setupranali:8080/v1/health
```

### Slow Queries

1. Check SetuPranali caching:
   ```bash
   curl http://localhost:8080/v1/health
   # Look for "cache": "connected"
   ```

2. Enable Metabase caching in Admin settings

### Authentication Issues

Verify API key:
```bash
curl -H "X-API-Key: your-key" http://localhost:8080/v1/datasets
```

---

## Example Dashboard

### Sales Overview

1. **Create Questions:**
   - Revenue by Month (line chart)
   - Top Customers (bar chart)
   - Regional Breakdown (map)

2. **Combine into Dashboard**
3. **Add Filters** (auto-applied via RLS)
4. **Share** with team

---

## Next Steps

- [Configure Row-Level Security](../../guides/rls.md)
- [Set Up Caching](../../concepts/caching.md)
- [Multi-Tenant Setup](../../guides/multi-tenant.md)

