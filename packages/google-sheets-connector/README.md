# SetuPranali Google Sheets Connector

Query SetuPranali semantic layer directly from Google Sheets.

## Features

- **Query Builder**: Visual sidebar to build semantic queries
- **Natural Language Queries**: Ask questions in plain English
- **Custom Functions**: Use `=SETUPRANALI()` formulas in cells
- **Auto Refresh**: Refresh all queries with one click
- **Data Formatting**: Results inserted as formatted tables

## Installation

### From Google Workspace Marketplace (Coming Soon)

1. Open Google Sheets
2. Go to **Extensions** > **Add-ons** > **Get add-ons**
3. Search for "SetuPranali"
4. Click **Install**

### Manual Installation

1. Open Google Sheets
2. Go to **Extensions** > **Apps Script**
3. Copy files from this repository:
   - `Code.gs`
   - `QueryBuilder.html`
   - `Settings.html`
   - `NLQ.html`
4. Save and reload spreadsheet

## Configuration

1. Open Google Sheets
2. Go to **SetuPranali** > **Settings**
3. Enter:
   - **Server URL**: Your SetuPranali server
   - **API Key**: Your API key
4. Click **Test Connection**
5. Click **Save**

## Usage

### Query Builder

1. Go to **SetuPranali** > **Query Builder**
2. Select a dataset
3. Choose dimensions and metrics
4. Click **Run Query**
5. Data is inserted at cursor position

### Natural Language Query

1. Go to **SetuPranali** > **Natural Language Query**
2. Type your question (e.g., "Show revenue by region")
3. Click **Ask**
4. Data is inserted at cursor position

### Custom Functions

Use SetuPranali directly in cell formulas:

```
=SETUPRANALI("orders", "region", "revenue,order_count")
=SETUPRANALI("orders", "order_date,region", "revenue", 100)
```

| Parameter | Description |
|-----------|-------------|
| dataset | Dataset ID |
| dimensions | Comma-separated dimensions |
| metrics | Comma-separated metrics |
| limit | Maximum rows (optional) |

#### Single Metric

Get a single metric value:

```
=SETUPRANALI_METRIC("orders", "total_revenue")
=SETUPRANALI_METRIC("orders", "revenue", "{\"region\": \"US\"}")
```

#### Natural Language

Ask a question:

```
=SETUPRANALI_ASK("What was revenue last month?")
=SETUPRANALI_ASK("Top 10 products by sales", "products")
```

### Refreshing Data

- **Single Query**: Click on query cell, go to **SetuPranali** > **Refresh Current Query**
- **All Queries**: Go to **SetuPranali** > **Refresh All Queries**

## Examples

### Revenue by Region

```
1. Query Builder:
   - Dataset: orders
   - Dimensions: region
   - Metrics: revenue, order_count
   
2. Click "Run Query"

Result:
| region | revenue | order_count |
|--------|---------|-------------|
| US     | 150000  | 1200        |
| EU     | 120000  | 950         |
| APAC   | 80000   | 650         |
```

### Monthly Trend

```
=SETUPRANALI("orders", "order_month", "revenue")

Result:
| order_month | revenue |
|-------------|---------|
| 2025-01     | 45000   |
| 2025-02     | 52000   |
| 2025-03     | 48000   |
```

### KPI Dashboard

Create a dashboard with single metrics:

```
A1: Total Revenue
B1: =SETUPRANALI_METRIC("orders", "total_revenue")

A2: Orders Today
B2: =SETUPRANALI_METRIC("orders", "order_count", "{\"date\": \"today\"}")

A3: Average Order Value
B3: =SETUPRANALI_METRIC("orders", "avg_order_value")
```

## Scheduled Refresh

Set up automatic refresh using Google Sheets triggers:

1. Go to **Extensions** > **Apps Script**
2. Click **Triggers** (clock icon)
3. Add trigger:
   - Function: `refreshAllQueries`
   - Event: Time-driven
   - Interval: Hourly/Daily

## Troubleshooting

### "Please configure settings first"

Go to **SetuPranali** > **Settings** and enter your server URL and API key.

### Connection Failed

1. Check server URL includes protocol (https://)
2. Verify API key is valid
3. Ensure server is accessible

### Slow Queries

1. Reduce row limit
2. Add filters to narrow results
3. Select fewer dimensions/metrics

### Custom Function Errors

1. Check formula syntax
2. Verify dataset and column names
3. Check server connectivity

## Development

### Project Structure

```
google-sheets-connector/
├── Code.gs              # Main Apps Script code
├── QueryBuilder.html    # Query builder sidebar
├── Settings.html        # Settings dialog
├── NLQ.html            # Natural language dialog
├── appsscript.json     # Apps Script manifest
└── README.md
```

### Testing Locally

1. Open Apps Script editor
2. Use **Run** > **Test as add-on**
3. Select test spreadsheet

### Publishing

See `PUBLISHING.md` for Google Workspace Marketplace submission.

## License

Apache 2.0 - See [LICENSE](../../LICENSE)

