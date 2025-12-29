# Qlik Sense

Connect Qlik Sense to SetuPranali using the REST connector for semantic layer analytics.

---

## Overview

**Qlik Sense** integration provides:

- **REST Connector**: Native Qlik REST connector support
- **Semantic Queries**: Query datasets with dimensions and metrics
- **Row-Level Security**: Automatic tenant isolation
- **Incremental Refresh**: Efficient data loading
- **Real-time Dashboards**: Live connection support

---

## Prerequisites

- Qlik Sense Desktop, Enterprise, or Cloud
- SetuPranali server running and accessible
- API key for authentication

---

## Connection Methods

### Method 1: REST Connector (Recommended)

Use Qlik's built-in REST connector for full control.

### Method 2: Web File Connector

For simpler use cases with JSON/CSV endpoints.

### Method 3: Qlik Application Automation

For automated data pipelines.

---

## REST Connector Setup

### Step 1: Create New Connection

1. Open Qlik Sense
2. Go to **Data Manager** or **Data Load Editor**
3. Click **Create new connection**
4. Select **REST**

### Step 2: Configure Connection

| Setting | Value |
|---------|-------|
| **URL** | `http://your-server:8080/v1/query` |
| **Method** | `POST` |
| **Request Headers** | `Content-Type: application/json` |
| **Request Headers** | `X-API-Key: your-api-key` |

### Step 3: Configure Request Body

```json
{
  "dataset": "orders",
  "dimensions": ["region", "product_category"],
  "metrics": ["revenue", "order_count"],
  "limit": 10000
}
```

### Step 4: Test Connection

Click **Test Connection** to verify.

---

## Data Load Script

### Basic Query

```qlik
LET vApiKey = 'your-api-key';
LET vBaseUrl = 'http://localhost:8080';

RestConnectorMasterTable:
SQL SELECT 
    "region",
    "product_category",
    "revenue",
    "order_count"
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""orders"",""dimensions"":[""region"",""product_category""],""metrics"":[""revenue"",""order_count""],""limit"":10000}"
);

Orders:
LOAD
    region,
    product_category,
    revenue,
    order_count
RESIDENT RestConnectorMasterTable;

DROP TABLE RestConnectorMasterTable;
```

### With Date Filters

```qlik
LET vStartDate = Date(Today()-30, 'YYYY-MM-DD');
LET vEndDate = Date(Today(), 'YYYY-MM-DD');

RestConnectorMasterTable:
SQL SELECT 
    "order_date",
    "region",
    "revenue"
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""orders"",""dimensions"":[""order_date"",""region""],""metrics"":[""revenue""],""filters"":[{""dimension"":""order_date"",""operator"":""gte"",""value"":""$(vStartDate)""},{""dimension"":""order_date"",""operator"":""lte"",""value"":""$(vEndDate)""}],""limit"":50000}"
);
```

### Multiple Datasets

```qlik
// Load Orders
Orders:
SQL SELECT *
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""orders"",""dimensions"":[""order_id"",""customer_id"",""region""],""metrics"":[""revenue""],""limit"":100000}"
);

// Load Customers
Customers:
SQL SELECT *
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""customers"",""dimensions"":[""customer_id"",""name"",""segment""],""metrics"":[],""limit"":50000}"
);
```

---

## SQL Endpoint

For raw SQL queries with RLS:

```qlik
RestConnectorMasterTable:
SQL SELECT *
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/sql",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""sql"":""SELECT region, DATE_TRUNC('month', order_date) as month, SUM(amount) as revenue FROM orders GROUP BY region, month ORDER BY month"",""dataset"":""orders""}"
);
```

---

## Qlik Cloud Setup

### 1. Create Generic REST Connection

1. Go to **Data Integration** > **Data Connections**
2. Click **Create Connection**
3. Select **REST**
4. Configure:

```yaml
Name: SetuPranali
URL: https://your-server.com/v1/query
Authentication: API Key Header
Header Name: X-API-Key
Header Value: your-api-key
```

### 2. Create Space Connection

For scheduled refreshes:

1. Go to **Space Settings**
2. Add **Data Connection**
3. Select your REST connection

---

## Incremental Load

### With Timestamp Field

```qlik
// Store last load time
LET vLastLoad = Peek('LastLoadTime', 0, 'LoadHistory');
IF IsNull(vLastLoad) THEN
    LET vLastLoad = '2020-01-01';
END IF

// Incremental load
IncrementalOrders:
SQL SELECT *
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""orders"",""dimensions"":[""order_id"",""order_date"",""region""],""metrics"":[""revenue""],""filters"":[{""dimension"":""updated_at"",""operator"":""gt"",""value"":""$(vLastLoad)""}],""limit"":100000}"
);

// Concatenate to existing data
Concatenate(Orders)
LOAD * RESIDENT IncrementalOrders;
DROP TABLE IncrementalOrders;

// Update load history
LoadHistory:
LOAD Now() as LastLoadTime AutoGenerate 1;
```

---

## Variables and Parameters

### Dynamic Dataset Selection

```qlik
// Variable for dataset
SET vDataset = 'orders';

RestConnectorMasterTable:
SQL SELECT *
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""$(vDataset)"",""dimensions"":[""region""],""metrics"":[""revenue""],""limit"":10000}"
);
```

### User-Based Filtering

```qlik
// Get Qlik user for RLS
LET vUser = OSUser();

// SetuPranali handles RLS via API key
// Each tenant should have their own API key
```

---

## Performance Optimization

### 1. Limit Data Volume

```qlik
// Only load necessary fields
BODY "{""dataset"":""orders"",""dimensions"":[""region""],""metrics"":[""revenue""],""limit"":10000}"
```

### 2. Use Filters

```qlik
// Filter at source
""filters"":[{""dimension"":""order_date"",""operator"":""gte"",""value"":""2024-01-01""}]
```

### 3. Enable Caching

SetuPranali caches query results - subsequent loads are faster.

### 4. Schedule Off-Peak

Use Qlik's scheduling for off-peak data refresh.

### 5. Incremental Loads

Only load new/changed data:

```qlik
WHERE updated_at > '$(vLastLoad)'
```

---

## Error Handling

### Check Connection Status

```qlik
// Test connection first
LET vTestUrl = '$(vBaseUrl)/v1/health';

TestConnection:
LOAD
    status
FROM [$(vTestUrl)]
(txt, codepage is 28591, embedded labels, delimiter is ',', msq);

LET vStatus = Peek('status', 0, 'TestConnection');
IF '$(vStatus)' <> 'healthy' THEN
    TRACE 'SetuPranali connection failed!';
    EXIT Script;
END IF
```

### Retry Logic

```qlik
// Simple retry with error handling
FOR vRetry = 1 to 3
    SET ErrorMode = 0;
    
    Orders:
    SQL SELECT *
    FROM JSON (wrap on) "root"
    WITH CONNECTION (...);
    
    IF ScriptError = 0 THEN
        EXIT FOR;
    END IF
    
    SLEEP 5000;
NEXT
SET ErrorMode = 1;
```

---

## Troubleshooting

### Connection Failed

**Error:** `Unable to connect to REST endpoint`

**Solutions:**
1. Verify SetuPranali server is running
2. Check URL is accessible from Qlik server
3. Verify firewall allows connection
4. Check API key is correct

### Authentication Error

**Error:** `401 Unauthorized`

**Solutions:**
1. Verify API key is valid
2. Check header name is `X-API-Key`
3. Ensure API key has dataset access

### JSON Parse Error

**Error:** `Unable to parse JSON response`

**Solutions:**
1. Use `JSON (wrap on)` option
2. Check response format matches expected schema
3. Verify dataset exists

### Timeout Error

**Error:** `Connection timeout`

**Solutions:**
1. Reduce `limit` parameter
2. Add filters to reduce data volume
3. Increase Qlik timeout settings
4. Check SetuPranali server performance

### No Data Returned

**Solutions:**
1. Verify dataset name is correct
2. Check dimensions and metrics exist
3. Review filter conditions
4. Test query in SetuPranali directly

---

## Security

### API Key Management

Store API keys securely:

```qlik
// Use data connection for credentials
// Or environment variables
LET vApiKey = GetEnvironmentVariable('SETUPRANALI_API_KEY');
```

### Row-Level Security

SetuPranali enforces RLS automatically based on API key:

```yaml
# catalog.yaml
datasets:
  - id: orders
    rls:
      mode: tenant_column
      field: tenant_id
```

Each tenant's API key only returns their data.

---

## Example Dashboard

### Sales Analysis App

```qlik
// Load Script
SET ThousandSep=',';
SET DecimalSep='.';

LET vApiKey = 'your-api-key';
LET vBaseUrl = 'http://localhost:8080';

// Sales Data
Sales:
LOAD
    order_date,
    region,
    product_category,
    revenue,
    order_count
;
SQL SELECT *
FROM JSON (wrap on) "root"
WITH CONNECTION (
    URL "$(vBaseUrl)/v1/query",
    HTTPHEADER "Content-Type" "application/json",
    HTTPHEADER "X-API-Key" "$(vApiKey)",
    BODY "{""dataset"":""orders"",""dimensions"":[""order_date"",""region"",""product_category""],""metrics"":[""revenue"",""order_count""],""limit"":100000}"
);

// Create calculated fields
SalesEnriched:
LOAD
    *,
    Year(order_date) as Year,
    Month(order_date) as Month,
    revenue / order_count as AvgOrderValue
RESIDENT Sales;
DROP TABLE Sales;
```

---

## Qlik Application Automation

### Automated Data Pipeline

```yaml
# qlik-automation.yaml
name: SetuPranali Daily Refresh
trigger:
  schedule: "0 6 * * *"  # 6 AM daily

actions:
  - type: reload_app
    app_id: "your-app-id"
    
  - type: notify
    channel: slack
    message: "SetuPranali data refreshed successfully"
```

---

## Resources

- [Qlik REST Connector Documentation](https://help.qlik.com/en-US/connectors/Subsystems/REST_connector_help/Content/Connectors_REST/REST-connector.htm)
- [SetuPranali API Reference](../../api-reference/query.md)
- [Qlik Script Syntax](https://help.qlik.com/en-US/sense/Subsystems/Hub/Content/Sense_Hub/Scripting/script-syntax.htm)

