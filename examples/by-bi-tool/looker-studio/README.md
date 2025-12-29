# Looker Studio Integration Examples

Connect Google Looker Studio to SetuPranali.

## Overview

Looker Studio connects via:
- **Community Connector** - Built-in connector
- **NPM Package** - For custom development

## Quick Start

### 1. Use the Community Connector

1. Open [Looker Studio](https://lookerstudio.google.com)
2. Click **Create** → **Data Source**
3. Search for **SetuPranali** (or use partner connector link)
4. Click **Connect**
5. Enter:
   - **API Endpoint**: `https://your-server:8080`
   - **API Key**: `your_api_key`
6. Select dataset
7. Click **Connect**

### 2. Create Report

1. Click **Create Report**
2. Add charts and tables
3. Share with your team

## Configuration

### Connector Settings

| Field | Description | Example |
|-------|-------------|---------|
| API Endpoint | SetuPranali server URL | `https://api.setupranali.io` |
| API Key | Your API key | `sk_live_xxx` |
| Dataset | Dataset to query | `orders` |

### Advanced Options

| Field | Description |
|-------|-------------|
| Cache TTL | How long to cache data (seconds) |
| Timeout | Request timeout (seconds) |

## Using the Connector

### Select Fields

After connecting, you'll see available fields:
- **Dimensions** - Green fields (text, dates)
- **Metrics** - Blue fields (numbers)

Select the fields you need for your report.

### Apply Filters

1. In your report, add a **Filter Control**
2. Select dimension to filter on
3. Choose filter type (dropdown, date range, etc.)

### Date Range Control

1. Add **Date Range Control** to report
2. Ensure your dataset has a date dimension
3. The connector automatically handles date filtering

## Chart Examples

### Time Series

1. Add **Time Series** chart
2. Dimension: `order_date`
3. Metric: `revenue`

### Bar Chart

1. Add **Bar Chart**
2. Dimension: `region`
3. Metric: `revenue`
4. Sort: Descending by metric

### Scorecard

1. Add **Scorecard**
2. Metric: `total_revenue`
3. Comparison: Previous period

### Table

1. Add **Table**
2. Dimensions: `customer_id`, `region`
3. Metrics: `revenue`, `order_count`
4. Sort by revenue

## Data Freshness

### Automatic Refresh

Looker Studio caches data by default. Configure refresh:

1. Click data source
2. Go to **Resource** → **Manage added data sources**
3. Click **Edit**
4. Set **Data freshness** (hourly, daily, etc.)

### Manual Refresh

Click **Refresh data** icon in the report toolbar.

## Calculated Fields

### In Looker Studio

```
Revenue per Order = revenue / order_count
```

### Percentage

```
Revenue Share = revenue / SUM(revenue)
```

### Date Formatting

```
Order Month = FORMAT_DATETIME("%Y-%m", order_date)
```

## Sharing & Permissions

### Share Report

1. Click **Share** button
2. Add email addresses
3. Choose permission level (View, Edit)

### Embed Report

1. Click **File** → **Embed report**
2. Copy embed code
3. Paste in your website

## NPM Package (Advanced)

For custom connector development:

```bash
npm install @setupranali/looker-studio
```

```javascript
import { SetuPranaliConnector } from '@setupranali/looker-studio';

const connector = new SetuPranaliConnector({
  apiEndpoint: 'https://api.setupranali.io',
  apiKey: 'your_api_key'
});

// In Apps Script
function getConfig() {
  return connector.getConfig();
}

function getSchema() {
  return connector.getSchema();
}

function getData(request) {
  return connector.getData(request);
}
```

## Troubleshooting

### Cannot Connect

1. Verify API endpoint is accessible
2. Check API key is correct
3. Ensure CORS is configured in SetuPranali

### No Data Showing

1. Check dataset has data
2. Verify date filters aren't too restrictive
3. Refresh data source

### Slow Performance

1. Reduce number of dimensions
2. Add date range filter
3. Enable caching in connector settings

## Files in This Example

```
looker-studio/
├── README.md
├── connector/
│   ├── Code.gs
│   └── appsscript.json
└── screenshots/
    ├── connect.png
    └── sample-report.png
```

## Best Practices

1. **Use Date Controls** - Always add date range control
2. **Limit Dimensions** - Don't over-complicate queries
3. **Cache Appropriately** - Balance freshness vs. performance
4. **Name Fields Clearly** - Rename fields for business users
5. **Use Calculated Fields** - Create derived metrics in Looker Studio

