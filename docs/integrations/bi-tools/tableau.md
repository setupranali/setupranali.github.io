# Tableau

Connect Tableau to SetuPranali using Web Data Connector.

---

## Overview

Tableau connects via Web Data Connector (WDC):

```
Tableau → WDC → SetuPranali → Your Data
```

---

## Quick Start

### Step 1: Open WDC

1. Open **Tableau Desktop**
2. Click **Connect** → **Web Data Connector**

### Step 2: Enter URL

```
http://localhost:8080/wdc/
```

### Step 3: Authenticate

1. Enter your **API Key**
2. Click **Connect**

### Step 4: Select Data

1. Choose a **Dataset**
2. Preview data
3. Click **Get Data**

---

## Web Data Connector Interface

The WDC provides a simple interface:

### Authentication

- **API Key**: Your authentication key
- **Server URL**: Auto-detected or manual

### Dataset Selection

- Dropdown of available datasets
- Preview sample data before loading

### Options

- Select dimensions
- Select metrics
- Apply filters

---

## Using in Tableau

### Create Visualizations

After loading data:

1. Drag **Dimensions** to Rows/Columns
2. Drag **Metrics** to Values
3. Build your visualization

### Refresh Data

- Click **Refresh** to reload data
- WDC will use the same API key and dataset

---

## Tableau Server/Online

### Allowlist the WDC

On Tableau Server, allowlist the connector:

```bash
tsm configuration set -k vizqlserver.url_allowlist -v "http://your-connector:8080"
tsm pending-changes apply
```

### Publish Workbooks

1. Create workbook in Desktop
2. Publish to Server/Online
3. Configure refresh schedule

### Authentication on Server

- Users can enter their own API keys
- Or use a shared service account key

---

## Row-Level Security

RLS is handled automatically by the connector.

### Per-User Keys

For user-level security:

1. Each Tableau user gets their own API key
2. API key includes tenant context
3. Connector filters data per-tenant

### Shared Key

For shared access:

1. Use a single team API key
2. All users see the same tenant's data

---

## Troubleshooting

### "Cannot connect to WDC"

**Causes**:
- WDC URL incorrect
- Server not running
- CORS issues

**Solutions**:
1. Verify URL: `http://localhost:8080/wdc/`
2. Test server health
3. Check browser console for CORS errors

### "Authentication failed"

**Causes**:
- Invalid API key
- Key expired

**Solutions**:
1. Verify API key is correct
2. Test with curl:
```bash
curl http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -d '{"dataset": "sales", "metrics": ["revenue"]}'
```

### "No data returned"

**Causes**:
- RLS filtering all rows
- Empty dataset
- Wrong dataset selected

**Solutions**:
1. Check API key tenant has data
2. Verify dataset in connector
3. Test via REST API

### "Slow performance"

**Causes**:
- Large dataset
- No caching
- Complex queries

**Solutions**:
1. Enable connector caching
2. Reduce dimensions/metrics
3. Add filters

---

## Best Practices

### 1. Use Extracts

For large datasets:

1. Connect via WDC
2. Create Extract (not Live connection)
3. Schedule extract refresh

### 2. Filter Early

Apply filters in WDC, not Tableau:

```
WDC: Select date range 2024
Tableau: Build visualization

Better than:
WDC: Load all data
Tableau: Filter to 2024
```

### 3. Monitor Performance

Check:
- Query execution times
- Data volumes
- Refresh durations

### 4. Secure API Keys

- Don't embed keys in published workbooks
- Use Tableau's authentication prompts
- Rotate keys regularly

