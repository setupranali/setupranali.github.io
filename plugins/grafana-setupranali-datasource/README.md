# SetuPranali Data Source Plugin for Grafana

Connect Grafana to your SetuPranali semantic layer for unified metrics and analytics.

## Features

- **Semantic Queries**: Query datasets using dimensions and metrics
- **SQL Mode**: Execute raw SQL with automatic RLS
- **Time Series**: Native time-series support with granularity options
- **Variables**: Template variable support for dynamic dashboards
- **Alerting**: Full alerting support
- **Annotations**: Query-based annotations

## Installation

### From Grafana Plugin Catalog (Recommended)

1. In Grafana, go to **Configuration** > **Plugins**
2. Search for "SetuPranali"
3. Click **Install**

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/setupranali/setupranali.github.io/releases)
2. Extract to your Grafana plugins directory:
   ```bash
   unzip setupranali-datasource-1.0.0.zip -d /var/lib/grafana/plugins/
   ```
3. Restart Grafana:
   ```bash
   systemctl restart grafana-server
   ```

### Docker

Mount the plugin in your Grafana container:

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./plugins/setupranali-datasource:/var/lib/grafana/plugins/setupranali-datasource
    environment:
      - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=setupranali-datasource
```

## Configuration

### Add Data Source

1. Go to **Configuration** > **Data Sources**
2. Click **Add data source**
3. Search for "SetuPranali"
4. Configure:

| Setting | Description | Example |
|---------|-------------|---------|
| **URL** | SetuPranali server URL | `http://setupranali:8080` |
| **API Key** | Your API key | `sk-...` |
| **Default Dataset** | Default dataset for queries | `orders` |

### Test Connection

Click **Save & Test** to verify the connection.

## Usage

### Semantic Query Mode

1. Select a **Dataset** from the dropdown
2. Choose **Dimensions** to group by
3. Select **Metrics** to aggregate
4. Optionally set:
   - **Time Dimension** for time-series data
   - **Granularity** (hour, day, week, month)
   - **Limit** for result count

### SQL Mode

1. Switch to **SQL** query type
2. Select a **Dataset** for RLS context
3. Write your SQL query:
   ```sql
   SELECT region, SUM(amount) as revenue
   FROM orders
   WHERE order_date >= $__timeFrom()
   GROUP BY region
   ```

### Template Variables

Create dashboard variables using these queries:

| Query | Description |
|-------|-------------|
| `datasets` | List all datasets |
| `dimensions(orders)` | List dimensions for a dataset |
| `metrics(orders)` | List metrics for a dataset |

### Time Range

The plugin automatically applies Grafana's time range when:
- A **Time Dimension** is selected
- Using `$__timeFrom()` and `$__timeTo()` in SQL mode

## Examples

### Time Series Chart

```
Dataset: orders
Dimensions: order_date
Metrics: revenue, order_count
Time Dimension: order_date
Granularity: day
```

### Table View

```
Dataset: orders
Dimensions: region, status
Metrics: revenue, order_count
Limit: 100
```

### SQL Query

```sql
SELECT 
    DATE_TRUNC('day', order_date) as day,
    region,
    SUM(amount) as revenue
FROM orders
WHERE order_date BETWEEN $__timeFrom() AND $__timeTo()
GROUP BY day, region
ORDER BY day
```

## Development

### Prerequisites

- Node.js 18+
- Go 1.21+ (for backend)
- Yarn or npm

### Setup

```bash
# Install dependencies
npm install

# Development mode (watch)
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint
npm run lint
```

### Backend Plugin (Optional)

For backend features (alerting, secure API calls):

```bash
cd pkg
go build -o gpx_setupranali ./...
```

## Troubleshooting

### Plugin Not Loading

1. Check Grafana logs: `journalctl -u grafana-server -f`
2. Verify plugin path: `/var/lib/grafana/plugins/setupranali-datasource`
3. For unsigned plugins, set: `GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=setupranali-datasource`

### Connection Failed

1. Verify SetuPranali server is running
2. Check URL is accessible from Grafana
3. Verify API key is correct
4. Check network/firewall settings

### No Data Returned

1. Verify dataset exists
2. Check dimensions and metrics are valid
3. Review time range settings
4. Check browser console for errors

## License

Apache 2.0 - See [LICENSE](../../LICENSE)

## Support

- [Documentation](https://setupranali.github.io)
- [GitHub Issues](https://github.com/setupranali/setupranali.github.io/issues)
- [Discord Community](https://discord.gg/setupranali)

