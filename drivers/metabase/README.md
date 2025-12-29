# SetuPranali Metabase Driver

Native Metabase driver for SetuPranali semantic layer.

## Features

- 🔌 **Native Integration** - Appears as "SetuPranali" in Metabase database list
- 🔒 **Secure** - Uses API key authentication
- 📊 **Auto-Discovery** - Automatically discovers datasets, dimensions, and metrics
- ⚡ **Row-Level Security** - RLS applied automatically based on API key

## Installation

### Method 1: Pre-built JAR (Recommended)

1. Download the latest driver JAR:
   ```bash
   curl -L -o setupranali-driver.metabase-driver.jar \
     https://github.com/setupranali/setupranali.github.io/releases/download/v1.0.0/setupranali-driver.metabase-driver.jar
   ```

2. Copy to Metabase plugins directory:
   ```bash
   cp setupranali-driver.metabase-driver.jar /path/to/metabase/plugins/
   ```

3. Restart Metabase

### Method 2: Build from Source

Requirements:
- Java 11+
- Leiningen

```bash
cd drivers/metabase
lein uberjar
cp target/uberjar/setupranali-driver.metabase-driver.jar /path/to/metabase/plugins/
```

### Method 3: Docker

```dockerfile
FROM metabase/metabase:latest

# Copy SetuPranali driver
COPY setupranali-driver.metabase-driver.jar /plugins/
```

Or use docker-compose:

```yaml
version: '3.8'
services:
  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    volumes:
      - ./setupranali-driver.metabase-driver.jar:/plugins/setupranali-driver.metabase-driver.jar
    depends_on:
      - setupranali

  setupranali:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"
```

## Configuration

### Add SetuPranali Database

1. Go to **Admin Settings → Databases → Add database**
2. Select **SetuPranali** from the dropdown
3. Configure connection:

| Field | Description | Example |
|-------|-------------|---------|
| Host | SetuPranali server hostname | `localhost` or `setupranali` |
| Port | SetuPranali server port | `8080` |
| API Key | Your API key | `sk_live_xxx` |
| Use SSL | Enable HTTPS | `false` (for local) |

4. Click **Save**

### Connection Test

The driver will automatically test connectivity when you save.

## Usage

### Browsing Data

After adding the database:

1. Go to **Browse Data**
2. Select your SetuPranali database
3. You'll see all available datasets as tables
4. Each dataset shows:
   - Dimensions (groupable fields)
   - Metrics (aggregatable measures)

### Creating Questions

#### Simple Question (GUI)

1. Click **New → Question**
2. Select **SetuPranali** as the database
3. Choose a dataset (table)
4. Select dimensions and metrics
5. Add filters if needed
6. **Get Answer**

#### Native Query

1. Click **New → Question → Native query**
2. Select SetuPranali database
3. Write a JSON query:

```json
{
  "dataset": "orders",
  "dimensions": ["city", "product"],
  "metrics": ["total_revenue", "order_count"],
  "filters": [
    {"field": "order_date", "operator": "gte", "value": "2024-01-01"}
  ],
  "orderBy": [{"field": "total_revenue", "direction": "desc"}],
  "limit": 100
}
```

4. Click **Get Answer**

### Dashboard

Create dashboards combining multiple SetuPranali questions with filters.

## Row-Level Security

RLS is automatically applied based on your API key's tenant:

```
API Key: tenant_id = "acme-corp"
↓
All queries automatically filtered to acme-corp data
```

Different Metabase users can have different API keys to see different data.

## Troubleshooting

### "Can't connect to SetuPranali"

1. Check SetuPranali is running:
   ```bash
   curl http://localhost:8080/v1/health
   ```

2. Verify network connectivity from Metabase container:
   ```bash
   docker exec metabase curl http://setupranali:8080/v1/health
   ```

### "Invalid API key"

1. Verify your API key is correct
2. Check the key hasn't expired
3. Ensure the key has necessary permissions

### "No tables found"

1. Check that your SetuPranali has datasets configured
2. Verify API key has access to datasets:
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8080/v1/datasets
   ```

### Driver Not Appearing

1. Check JAR is in plugins directory:
   ```bash
   ls /path/to/metabase/plugins/
   ```

2. Check Metabase logs for driver loading:
   ```bash
   docker logs metabase | grep -i setupranali
   ```

3. Restart Metabase

## Development

### Running Tests

```bash
lein test
```

### Building

```bash
lein uberjar
```

### Local Testing

```bash
# Start SetuPranali
docker run -p 8080:8080 adeygifting/connector:latest

# Start Metabase with driver
docker run -p 3000:3000 \
  -v $(pwd)/target/uberjar/setupranali-driver.metabase-driver.jar:/plugins/setupranali-driver.metabase-driver.jar \
  metabase/metabase:latest
```

## License

Apache 2.0 - See [LICENSE](../../LICENSE) for details.

## Support

- Issues: https://github.com/setupranali/setupranali.github.io/issues
- Discussions: https://github.com/setupranali/setupranali.github.io/discussions

