# Tableau Integration Examples

Connect Tableau to SetuPranali using Web Data Connector.

## Overview

Tableau connects to SetuPranali via:
- **Web Data Connector (WDC)** - Primary method
- **REST API** - Using Tableau Prep or custom scripts

## Quick Start

### 1. Open Tableau Desktop

1. Click **Connect** → **Web Data Connector**
2. Enter URL: `http://localhost:8080/tableau/wdc`
3. Enter your API key when prompted
4. Select datasets to import
5. Click **Get Data**

## Connection Methods

### Method 1: Web Data Connector (Recommended)

```
WDC URL: http://your-server:8080/tableau/wdc
```

Features:
- Interactive dataset selection
- Automatic schema detection
- Native Tableau experience

### Method 2: Hyper File Export

For large datasets or offline analysis:

```bash
curl -X POST "http://localhost:8080/v1/enterprise/hyper/export" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dataset": "orders", "output": "orders.hyper"}'
```

Then open the `.hyper` file directly in Tableau.

### Method 3: REST API + Tableau Prep

Use Tableau Prep Builder for complex transformations:

1. Add **REST API** connector
2. Configure endpoint: `http://localhost:8080/v1/query`
3. Set authentication header
4. Build your flow

## Web Data Connector Features

### Dataset Selection

The WDC shows all available datasets with:
- Dataset name and description
- Available dimensions
- Available metrics

### Filtering

Apply filters before importing:

```javascript
// In WDC interface
{
  "dataset": "orders",
  "filters": [
    {"dimension": "order_date", "operator": ">=", "value": "2024-01-01"}
  ]
}
```

### Custom Queries

For advanced users, the WDC supports custom query mode:

```json
{
  "dataset": "orders",
  "dimensions": ["order_month", "region"],
  "metrics": ["revenue", "order_count"],
  "filters": [
    {"dimension": "status", "operator": "=", "value": "delivered"}
  ]
}
```

## Tableau Calculations

### Using SetuPranali Metrics

SetuPranali metrics come as pre-aggregated values. Create Tableau calculations:

```
// Revenue per Order
[Revenue] / [Order Count]

// Year-over-Year Growth
([Revenue] - LOOKUP([Revenue], -12)) / LOOKUP([Revenue], -12)
```

### Date Handling

SetuPranali returns dates in ISO format. Tableau automatically recognizes these.

## Live vs Extract

### Live Connection
- Real-time data
- Queries sent to SetuPranali
- Best for: Dashboards needing fresh data

### Extract
- Data snapshot
- Fast performance
- Best for: Complex visualizations, offline use

## Tableau Server/Online

### Publishing to Tableau Server

1. Publish workbook with embedded credentials
2. Or configure OAuth (if using SetuPranali OAuth)

### Data Source Publishing

1. Connect to SetuPranali in Tableau Desktop
2. Right-click data source → **Publish to Server**
3. Set refresh schedule

### Refresh Schedule

Configure in Tableau Server:
1. Go to published data source
2. Click **Refresh** tab
3. Set schedule (hourly, daily, etc.)

## Row-Level Security

### Option 1: API Key per User

Different API keys with different tenant_ids:

```yaml
api_keys:
  tableau_user1_key:
    tenant_id: "region_north"
  tableau_user2_key:
    tenant_id: "region_south"
```

### Option 2: User Filter

Pass Tableau username to SetuPranali:

```javascript
// In WDC
tableau.username // Available in WDC
```

## Performance Optimization

### Enable Caching

```yaml
cache:
  enabled: true
  ttl: 300  # 5 minutes
```

### Use Extracts for Complex Dashboards

1. Connect live for testing
2. Create extract for production
3. Schedule regular refreshes

### Filter Pushdown

Ensure filters are pushed to SetuPranali:
- Use context filters
- Avoid complex Tableau calculations in filters

## Troubleshooting

### WDC Not Loading

1. Check browser console for errors
2. Verify SetuPranali is accessible
3. Try different browser

### Authentication Failed

1. Verify API key
2. Check key has necessary permissions
3. Ensure key is not expired

### Slow Performance

1. Enable SetuPranali caching
2. Use extracts instead of live
3. Reduce dimensions/metrics in query

## Files in This Example

```
tableau/
├── README.md
├── SetuPranali-Template.twbx    # Tableau workbook template
├── wdc/
│   └── index.html               # Custom WDC if needed
└── screenshots/
    ├── wdc-connect.png
    └── sample-dashboard.png
```

