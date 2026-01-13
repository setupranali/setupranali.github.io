# Grafana

Connect Grafana to SetuPranali using the native data source plugin.

---

## Overview

The **SetuPranali Grafana Plugin** provides:

- **Semantic Queries**: Visual query builder for dimensions and metrics
- **SQL Mode**: Raw SQL with automatic RLS
- **Time Series**: Native time-series support
- **Variables**: Template variable support
- **Alerting**: Full alerting capabilities
- **Annotations**: Query-based annotations

---

## Installation

### From Grafana Plugin Catalog

1. In Grafana, go to **Configuration** > **Plugins**
2. Search for "SetuPranali"
3. Click **Install**

### Manual Installation

```bash
# Download plugin
wget https://github.com/setupranali/setupranali.github.io/releases/download/v1.0.0/setupranali-datasource-1.0.0.zip

# Extract to plugins directory
unzip setupranali-datasource-1.0.0.zip -d /var/lib/grafana/plugins/

# Restart Grafana
sudo systemctl restart grafana-server
```

### Docker

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./plugins/setupranali-datasource:/var/lib/grafana/plugins/setupranali-datasource
    environment:
      - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=setupranali-datasource
```

---

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
| **Default Dataset** | Default dataset | `orders` |
| **Enable Cache** | Enable query caching | `true` |
| **Cache TTL** | Cache time-to-live | `300` |

5. Click **Save & Test**

---

## Query Types

### Semantic Query Mode

Use the visual query builder:

1. **Dataset**: Select from available datasets
2. **Dimensions**: Fields to group by
3. **Metrics**: Aggregations to calculate
4. **Time Dimension**: For time-series charts
5. **Granularity**: hour, day, week, month
6. **Limit**: Maximum rows

The semantic query builder provides a visual interface to select datasets, dimensions, and metrics without writing SQL.

### SQL Mode

Write raw SQL queries:

```sql
SELECT 
    DATE_TRUNC('day', order_date) as time,
    region,
    SUM(amount) as revenue
FROM orders
WHERE order_date BETWEEN $__timeFrom() AND $__timeTo()
GROUP BY time, region
ORDER BY time
```

**Variables:**

| Variable | Description |
|----------|-------------|
| `$__timeFrom()` | Start of time range |
| `$__timeTo()` | End of time range |
| `$__interval` | Suggested interval |

---

## Dashboard Examples

### Time Series

```
Dataset: orders
Dimensions: order_date
Metrics: revenue, order_count
Time Dimension: order_date
Granularity: day
```

### Bar Chart by Region

```
Dataset: orders
Dimensions: region
Metrics: revenue
Limit: 10
```

### Table View

```
Dataset: orders
Dimensions: region, status, customer_segment
Metrics: revenue, order_count, avg_order_value
Limit: 100
```

---

## Template Variables

Create dynamic dashboards using variables:

### Dataset List

```
Query: datasets
```

### Dimensions

```
Query: dimensions($dataset)
```

### Metrics

```
Query: metrics($dataset)
```

### Custom Values

```sql
SELECT DISTINCT region FROM orders
```

---

## Alerting

Create alerts based on SetuPranali queries:

1. Create a panel with your query
2. Go to **Alert** tab
3. Configure conditions:
   ```
   WHEN avg() OF query(A) IS ABOVE 1000
   ```
4. Set notification channels

---

## Annotations

Add annotations from SetuPranali data:

1. Go to **Dashboard Settings** > **Annotations**
2. Click **Add annotation query**
3. Select SetuPranali data source
4. Configure query:
   ```
   Dataset: events
   Dimensions: event_time, event_type
   Metrics: (none)
   Time Dimension: event_time
   ```

---

## Performance Tips

### 1. Use Caching

Enable caching in data source settings:
```
Enable Cache: true
Cache TTL: 300
```

### 2. Limit Results

Always set a reasonable limit:
```
Limit: 1000
```

### 3. Use Appropriate Granularity

For long time ranges, use larger granularity:
- Last 24h: `hour`
- Last 7d: `day`
- Last 30d: `day`
- Last year: `month`

### 4. Pre-aggregate Data

Use continuous aggregates in your data warehouse.

---

## Troubleshooting

### Plugin Not Loading

1. Check Grafana logs:
   ```bash
   journalctl -u grafana-server -f
   ```

2. For unsigned plugins:
   ```ini
   # /etc/grafana/grafana.ini
   [plugins]
   allow_loading_unsigned_plugins = setupranali-datasource
   ```

### Connection Failed

1. Verify SetuPranali is running
2. Check URL is accessible
3. Verify API key is correct
4. Check firewall settings

### No Data

1. Verify dataset exists
2. Check time range includes data
3. Verify dimensions/metrics are valid
4. Check browser console for errors

### Slow Queries

1. Enable caching
2. Reduce result limit
3. Use appropriate granularity
4. Add filters to narrow data

---

## Example Dashboard JSON

```json
{
  "panels": [
    {
      "title": "Revenue by Region",
      "type": "barchart",
      "datasource": "SetuPranali",
      "targets": [
        {
          "dataset": "orders",
          "dimensions": ["region"],
          "metrics": ["revenue"],
          "queryType": "semantic"
        }
      ]
    },
    {
      "title": "Daily Revenue",
      "type": "timeseries",
      "datasource": "SetuPranali",
      "targets": [
        {
          "dataset": "orders",
          "dimensions": ["order_date"],
          "metrics": ["revenue"],
          "timeDimension": "order_date",
          "timeGranularity": "day",
          "queryType": "semantic"
        }
      ]
    }
  ]
}
```

---

## Resources

- [Plugin Source Code](https://github.com/setupranali/setupranali.github.io/tree/main/plugins/grafana-setupranali-datasource)
- [Grafana Plugin Development](https://grafana.com/docs/grafana/latest/developers/plugins/)
- [SetuPranali API Reference](../../api-reference/query.md)

