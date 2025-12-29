# Grafana Integration Examples

Connect Grafana to SetuPranali using the data source plugin.

## Overview

The SetuPranali Grafana plugin provides:
- Native data source integration
- Time-series and table visualizations
- Template variables
- Alerting support
- Annotations

## Quick Start

### 1. Install the Plugin

```bash
# Using grafana-cli
grafana-cli plugins install setupranali-datasource

# Or download manually
cd /var/lib/grafana/plugins
unzip setupranali-datasource.zip
```

### 2. Restart Grafana

```bash
systemctl restart grafana-server
```

### 3. Add Data Source

1. Go to **Configuration** → **Data Sources** → **Add data source**
2. Search for **SetuPranali**
3. Configure:
   - **URL**: `http://localhost:8080`
   - **API Key**: `your_api_key`
4. Click **Save & Test**

## Configuration

### Basic Setup

| Field | Value |
|-------|-------|
| URL | `http://localhost:8080` |
| API Key | `your_api_key` |

### With SSL

| Field | Value |
|-------|-------|
| URL | `https://api.setupranali.io` |
| API Key | `your_api_key` |
| TLS Skip Verify | Uncheck for production |

## Query Editor

### Semantic Query Mode

Build queries visually:

1. Select **Dataset**: `orders`
2. Add **Dimensions**: `order_date`
3. Add **Metrics**: `revenue`, `order_count`
4. Add **Filters**: `status = delivered`

### SQL Mode

Write raw SQL:

```sql
SELECT 
  $__timeGroup(order_date, $__interval),
  SUM(revenue) as revenue
FROM orders
WHERE $__timeFilter(order_date)
GROUP BY 1
ORDER BY 1
```

### GraphQL Mode

```graphql
query {
  orders(
    dimensions: ["order_date"]
    metrics: ["revenue"]
    filters: [{dimension: "order_date", operator: ">=", value: "$__from"}]
  ) {
    data
  }
}
```

## Time Series Queries

### Basic Time Series

```
Dataset: orders
Time Field: order_date
Metrics: revenue, order_count
```

### With Grouping

```
Dataset: orders
Time Field: order_date
Group By: region
Metrics: revenue
```

## Panel Examples

### Single Stat

Show total revenue:

```yaml
Dataset: orders
Metrics: total_revenue
Filters: order_date >= $__from
```

### Time Series Graph

Revenue over time:

```yaml
Dataset: orders
Time Field: order_date
Metrics: revenue
Interval: $__interval
```

### Table

Top customers:

```yaml
Dataset: orders
Dimensions: customer_id, region
Metrics: revenue, order_count
Order By: revenue DESC
Limit: 10
```

### Pie Chart

Revenue by region:

```yaml
Dataset: orders
Dimensions: region
Metrics: revenue
```

## Template Variables

### Dataset Variable

1. Go to **Dashboard Settings** → **Variables**
2. Add variable:
   - Name: `dataset`
   - Type: Query
   - Data source: SetuPranali
   - Query: `datasets()`

### Dimension Value Variable

```
Name: region
Query: dimension_values(orders, region)
```

Use in queries: `$region`

## Alerting

### Create Alert Rule

1. Edit panel → **Alert** tab
2. Create alert rule:
   - Condition: `avg() of query(A) > 10000`
   - Evaluate: `every 1m for 5m`
3. Configure notifications

## Annotations

Mark events on graphs:

```yaml
Query: events
Time Field: event_time
Title Field: event_name
Tags: type
```

## Docker Setup

```yaml
version: '3.8'
services:
  setupranali:
    image: adeygifting/connector:latest
    ports:
      - "8080:8080"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./plugins:/var/lib/grafana/plugins
      - grafana_data:/var/lib/grafana
    environment:
      - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=setupranali-datasource

volumes:
  grafana_data:
```

## Provisioning

### Data Source

```yaml
# provisioning/datasources/setupranali.yaml
apiVersion: 1
datasources:
  - name: SetuPranali
    type: setupranali-datasource
    url: http://setupranali:8080
    jsonData:
      apiKey: ${SETUPRANALI_API_KEY}
```

### Dashboard

```yaml
# provisioning/dashboards/dashboard.yaml
apiVersion: 1
providers:
  - name: 'default'
    folder: ''
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

## Troubleshooting

### Plugin Not Loading

1. Check plugin is in correct directory
2. Restart Grafana
3. Enable unsigned plugins if needed:

```ini
[plugins]
allow_loading_unsigned_plugins = setupranali-datasource
```

### Connection Failed

1. Test SetuPranali is accessible
2. Check API key
3. Verify URL doesn't have trailing slash

## Files in This Example

```
grafana/
├── README.md
├── docker-compose.yml
├── plugins/
│   └── setupranali-datasource/
├── provisioning/
│   ├── datasources/
│   └── dashboards/
└── dashboards/
    └── sample-dashboard.json
```

