# Google Sheets Integration Examples

Connect Google Sheets to SetuPranali.

## Overview

Google Sheets connects via:
- **Apps Script Add-on** - Custom functions and sidebar
- **IMPORTDATA** - Simple data import
- **Apps Script** - Custom automation

## Quick Start

### Method 1: SetuPranali Add-on

1. Open Google Sheets
2. **Extensions** → **Add-ons** → **Get add-ons**
3. Search for **SetuPranali**
4. Click **Install**
5. **Extensions** → **SetuPranali** → **Connect**
6. Enter API endpoint and key
7. Use the query builder!

### Method 2: Custom Functions

After installing, use custom functions:

```
=SETUPRANALI_QUERY("orders", "order_date,region", "revenue,order_count")
```

## Add-on Features

### Connect

1. **Extensions** → **SetuPranali** → **Settings**
2. Enter:
   - API Endpoint: `https://your-server:8080`
   - API Key: `your_api_key`
3. Click **Save**

### Query Builder Sidebar

1. **Extensions** → **SetuPranali** → **Query Builder**
2. Select dataset
3. Choose dimensions and metrics
4. Add filters
5. Click **Insert Data**

### Natural Language Query

1. **Extensions** → **SetuPranali** → **Ask a Question**
2. Type: "What is the revenue by region?"
3. Click **Query**
4. Results appear in sheet

## Custom Functions

### Basic Query

```
=SETUPRANALI_QUERY(dataset, dimensions, metrics)
```

Example:
```
=SETUPRANALI_QUERY("orders", "region", "revenue,order_count")
```

### With Filters

```
=SETUPRANALI_QUERY("orders", "region", "revenue", "status=delivered")
```

### Date Range

```
=SETUPRANALI_QUERY("orders", "order_date", "revenue", "order_date>=2024-01-01")
```

### Reference Cells

```
=SETUPRANALI_QUERY("orders", A1, B1, "order_date>="&C1)
```

Where:
- A1: `order_date,region`
- B1: `revenue`
- C1: `2024-01-01`

### Natural Language

```
=SETUPRANALI_NLQ("What is the total revenue by month?")
```

## Apps Script Examples

### Basic Query Function

```javascript
function querySetuPranali(dataset, dimensions, metrics) {
  const API_KEY = PropertiesService.getUserProperties().getProperty('SETUPRANALI_API_KEY');
  const ENDPOINT = PropertiesService.getUserProperties().getProperty('SETUPRANALI_ENDPOINT');
  
  const payload = {
    dataset: dataset,
    dimensions: dimensions.split(','),
    metrics: metrics.split(',')
  };
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + API_KEY
    },
    payload: JSON.stringify(payload)
  };
  
  const response = UrlFetchApp.fetch(ENDPOINT + '/v1/query', options);
  const json = JSON.parse(response.getContentText());
  
  // Convert to 2D array for Sheets
  const headers = Object.keys(json.data[0]);
  const rows = json.data.map(row => headers.map(h => row[h]));
  
  return [headers, ...rows];
}
```

### Scheduled Refresh

```javascript
function refreshData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Data');
  
  const data = querySetuPranali('orders', 'order_date,region', 'revenue');
  
  sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
}

// Create time-based trigger
function createDailyTrigger() {
  ScriptApp.newTrigger('refreshData')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();
}
```

### Menu Integration

```javascript
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('SetuPranali')
    .addItem('Query Builder', 'showQueryBuilder')
    .addItem('Refresh Data', 'refreshData')
    .addItem('Settings', 'showSettings')
    .addToUi();
}

function showQueryBuilder() {
  const html = HtmlService.createHtmlOutputFromFile('QueryBuilder')
    .setWidth(400)
    .setHeight(600);
  SpreadsheetApp.getUi().showSidebar(html);
}
```

## Automatic Refresh

### Time-Based Trigger

1. **Extensions** → **Apps Script**
2. Add trigger:

```javascript
function createTrigger() {
  ScriptApp.newTrigger('refreshData')
    .timeBased()
    .everyHours(1)
    .create();
}
```

### On Edit Trigger

Refresh when a cell changes:

```javascript
function onEdit(e) {
  if (e.range.getA1Notation() === 'A1') {
    refreshData();
  }
}
```

## Sharing & Collaboration

### Share Sheet

Data refreshes work for all viewers with appropriate permissions.

### Publish to Web

1. **File** → **Share** → **Publish to web**
2. Select sheet/range
3. Get embed URL

## Troubleshooting

### Authorization Required

1. Run any function manually first
2. Accept OAuth permissions
3. Try again

### Quota Exceeded

Google Apps Script has quotas:
- 20,000 URL Fetch calls/day
- 6 minutes execution time

Solutions:
- Cache results
- Reduce refresh frequency
- Use triggers wisely

### Function Not Found

1. Ensure add-on is installed
2. Refresh the page
3. Check script permissions

## Files in This Example

```
google-sheets/
├── README.md
├── Code.gs
├── QueryBuilder.html
├── Settings.html
└── screenshots/
    ├── add-on-menu.png
    └── query-builder.png
```

## Best Practices

1. **Use Named Ranges** - Reference parameters easily
2. **Cache Results** - Avoid hitting API limits
3. **Schedule Smartly** - Don't over-refresh
4. **Handle Errors** - Show user-friendly messages
5. **Document Queries** - Add comments in cells

