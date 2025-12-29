# Power BI

Connect Power BI to SetuPranali using OData.

---

## Overview

Power BI connects natively via OData—no custom connector required.

```
Power BI → OData → SetuPranali → Your Data
```

---

## Quick Start

### Step 1: Get Data

1. Open **Power BI Desktop**
2. Click **Get Data** → **OData Feed**

### Step 2: Enter URL

```
http://localhost:8080/odata/sales
```

Replace `sales` with your dataset name.

### Step 3: Configure Authentication

1. Select **Advanced**
2. Add HTTP header:
   - **Name**: `X-API-Key`
   - **Value**: `your-api-key`
3. Click **OK**

### Step 4: Load Data

Select tables and click **Load**.

---

## OData URLs

### Service Document

Lists all available datasets:

```
http://localhost:8080/odata
```

### Dataset Data

Query a specific dataset:

```
http://localhost:8080/odata/{dataset}
```

### Metadata

Get schema information:

```
http://localhost:8080/odata/{dataset}/$metadata
```

---

## Query Options

### Select Columns

```
/odata/sales?$select=region,revenue,orders
```

### Filter Data

```
/odata/sales?$filter=region eq 'North'
/odata/sales?$filter=revenue gt 10000
/odata/sales?$filter=order_date ge 2024-01-01
```

### Order Results

```
/odata/sales?$orderby=revenue desc
```

### Limit Rows

```
/odata/sales?$top=100
```

### Combined

```
/odata/sales?$select=region,revenue&$filter=revenue gt 10000&$orderby=revenue desc&$top=10
```

---

## Incremental Refresh

Power BI can load only new data using incremental refresh.

### Step 1: Create Parameters

In Power Query, create:

1. **RangeStart** (Date/Time)
2. **RangeEnd** (Date/Time)

### Step 2: Filter by Parameters

```m
let
    Source = OData.Feed("http://localhost:8080/odata/sales"),
    Filtered = Table.SelectRows(Source, each 
        [order_date] >= RangeStart and 
        [order_date] < RangeEnd
    )
in
    Filtered
```

### Step 3: Configure Policy

1. Right-click dataset
2. Select **Incremental refresh**
3. Configure:
   - Archive data: 3 years
   - Incrementally refresh: 7 days

### Step 4: Publish

Publish to Power BI Service. Incremental refresh only works in the service.

---

## Row-Level Security

RLS is handled by SetuPranali, not Power BI.

### How It Works

1. User connects with their API key
2. API key has tenant context
3. Connector filters data automatically

### Example

API key `pk_acme_abc123` belongs to tenant `acme_corp`:

```
User queries /odata/sales
→ Connector adds: WHERE tenant_id = 'acme_corp'
→ User only sees their data
```

---

## Power BI Service

### Gateway Not Required

For cloud-accessible deployments, no gateway needed:

```
Power BI Service → Internet → Your Connector
```

### With On-Premises Gateway

If connector is behind firewall:

1. Install On-Premises Data Gateway
2. Configure OData source
3. Add API key to gateway configuration

---

## Troubleshooting

### "Unable to connect"

**Causes**:
- Wrong URL
- Server not running
- Network issues

**Solutions**:
```bash
# Test from terminal
curl http://localhost:8080/odata/sales \
  -H "X-API-Key: your-api-key"
```

### "Access denied"

**Causes**:
- Invalid API key
- Missing X-API-Key header

**Solutions**:
1. Verify API key is correct
2. Ensure header is configured properly
3. Test with curl first

### "No data"

**Causes**:
- RLS filtering all rows
- Empty dataset
- Wrong dataset name

**Solutions**:
1. Check API key tenant has data
2. Verify dataset name
3. Test without filters

### "Refresh failed"

**Causes**:
- Credentials expired
- Server unavailable
- Rate limited

**Solutions**:
1. Check connector logs
2. Verify server is running
3. Check rate limit settings

---

## Best Practices

### 1. Use Incremental Refresh

For large datasets, always use incremental refresh:
- Faster refresh times
- Lower database load
- Reduced costs

### 2. Select Needed Columns

Don't load all columns:

```m
// Good: Select specific columns
Source = OData.Feed("http://server/odata/sales?$select=region,revenue")

// Avoid: Loading everything
Source = OData.Feed("http://server/odata/sales")
```

### 3. Schedule Off-Peak

Schedule refreshes during off-peak hours:
- Less contention
- Better performance
- Lower costs

### 4. Monitor Refresh History

Regularly check:
- Refresh duration
- Row counts
- Error messages

