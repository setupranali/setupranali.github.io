# Google Sheets Integration

Query SetuPranali semantic layer directly from Google Sheets.

---

## Overview

The SetuPranali Google Sheets Connector provides:

- **Query Builder**: Visual sidebar to build queries
- **Natural Language Queries**: Ask questions in plain English
- **Custom Functions**: Use `=SETUPRANALI()` formulas
- **Auto Refresh**: Refresh all queries with one click

---

## Installation

### From Google Workspace Marketplace (Coming Soon)

1. Open Google Sheets
2. Go to **Extensions** > **Add-ons** > **Get add-ons**
3. Search for "SetuPranali"
4. Click **Install**

### Manual Installation

1. Open Google Sheets
2. Go to **Extensions** > **Apps Script**
3. Copy files from repository:
   - `Code.gs`
   - `QueryBuilder.html`
   - `Settings.html`
   - `NLQ.html`
4. Save and reload spreadsheet

---

## Configuration

1. Open Google Sheets
2. Go to **SetuPranali** > **Settings**
3. Enter:
   - **Server URL**: Your SetuPranali server
   - **API Key**: Your API key
4. Click **Test Connection**
5. Click **Save**

---

## Usage

### Query Builder

1. Go to **SetuPranali** > **Query Builder**
2. Select a dataset
3. Choose dimensions and metrics
4. Set row limit (optional)
5. Click **Run Query**

Data is inserted at the active cell as a formatted table.

### Natural Language Query

1. Go to **SetuPranali** > **Natural Language Query**
2. Type your question:
   - "Show revenue by region"
   - "Top 10 products by sales"
   - "Monthly revenue trend"
3. Click **Ask**

### Custom Functions

Use SetuPranali directly in cell formulas:

#### Basic Query

```
=SETUPRANALI("orders", "region", "revenue,order_count")
```

| Parameter | Description |
|-----------|-------------|
| dataset | Dataset ID |
| dimensions | Comma-separated dimensions |
| metrics | Comma-separated metrics |
| limit | Maximum rows (optional) |

#### Single Metric

```
=SETUPRANALI_METRIC("orders", "total_revenue")
=SETUPRANALI_METRIC("orders", "revenue", "{\"region\": \"US\"}")
```

#### Natural Language

```
=SETUPRANALI_ASK("What was revenue last month?")
```

---

## Examples

### Revenue by Region

```
Formula: =SETUPRANALI("orders", "region", "revenue,order_count")

Result:
| region | revenue | order_count |
|--------|---------|-------------|
| US     | 150000  | 1200        |
| EU     | 120000  | 950         |
| APAC   | 80000   | 650         |
```

### Monthly Trend

```
Formula: =SETUPRANALI("orders", "order_month", "revenue")

Result:
| order_month | revenue |
|-------------|---------|
| 2025-01     | 45000   |
| 2025-02     | 52000   |
| 2025-03     | 48000   |
```

### KPI Dashboard

Create a dashboard with single metrics:

| Cell | Formula | Result |
|------|---------|--------|
| A1 | Total Revenue | |
| B1 | `=SETUPRANALI_METRIC("orders", "total_revenue")` | 350000 |
| A2 | Orders Today | |
| B2 | `=SETUPRANALI_METRIC("orders", "order_count", "{\"date\":\"today\"}")` | 125 |
| A3 | Average Order Value | |
| B3 | `=SETUPRANALI_METRIC("orders", "avg_order_value")` | 2800 |

---

## Refreshing Data

### Manual Refresh

- **Single Query**: Click on query cell, go to **SetuPranali** > **Refresh Current Query**
- **All Queries**: Go to **SetuPranali** > **Refresh All Queries**

### Scheduled Refresh

Set up automatic refresh using Google Sheets triggers:

1. Go to **Extensions** > **Apps Script**
2. Click **Triggers** (clock icon)
3. Add trigger:
   - Function: `refreshAllQueries`
   - Event: Time-driven
   - Interval: Hourly / Daily / Weekly

---

## Troubleshooting

### "Please configure settings first"

1. Go to **SetuPranali** > **Settings**
2. Enter your server URL and API key
3. Click **Save**

### Connection Failed

1. Check server URL includes protocol (`https://`)
2. Verify API key is valid
3. Ensure server is accessible from Google's servers

### Custom Function Errors

1. Check formula syntax
2. Verify dataset and column names exist
3. Check server connectivity
4. View execution logs in Apps Script

### Slow Queries

1. Reduce row limit
2. Add filters to narrow results
3. Select fewer dimensions/metrics
4. Check server performance

---

## Security

- API keys stored in Google user properties
- Keys are per-user, not shared
- All requests use HTTPS
- No data stored outside Google Sheets

---

## Source Code

```
packages/google-sheets-connector/
├── Code.gs              # Main Apps Script code
├── QueryBuilder.html    # Query builder sidebar
├── Settings.html        # Settings dialog
├── NLQ.html            # Natural language dialog
├── appsscript.json     # Apps Script manifest
└── README.md
```

---

## Support

- [GitHub Issues](https://github.com/setupranali/setupranali.github.io/issues)
- [Documentation](https://setupranali.github.io)
- [Discord Community](https://discord.gg/setupranali)

