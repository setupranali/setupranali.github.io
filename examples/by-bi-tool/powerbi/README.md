# Power BI Integration Examples

Connect Power BI to SetuPranali using OData.

## Overview

Power BI connects to SetuPranali via the **OData** protocol, providing:
- Native DirectQuery support
- Scheduled refresh
- Incremental refresh
- Row-level security

## Quick Start

### 1. Get OData Feed URL

```
http://localhost:8080/odata/orders
```

### 2. Connect in Power BI Desktop

1. Open Power BI Desktop
2. Click **Get Data** → **OData Feed**
3. Enter the URL: `http://your-server:8080/odata/orders`
4. Select **Basic** authentication
5. Enter your API key as the password (leave username blank)
6. Click **Connect**

## Connection Methods

### Method 1: OData Feed (Recommended)

Best for:
- DirectQuery
- Large datasets
- Real-time data

```
URL: http://your-server:8080/odata/{dataset}
Authentication: Basic (API key as password)
```

### Method 2: Web API (Advanced)

Best for:
- Custom transformations
- Multiple queries
- Power Query M code

```m
let
    Source = Json.Document(Web.Contents(
        "http://your-server:8080/v1/query",
        [
            Headers = [
                #"Authorization" = "Bearer YOUR_API_KEY",
                #"Content-Type" = "application/json"
            ],
            Content = Text.ToBinary("{
                ""dataset"": ""orders"",
                ""dimensions"": [""order_date"", ""region""],
                ""metrics"": [""revenue"", ""order_count""]
            }")
        ]
    )),
    data = Source[data]
in
    data
```

## Sample Power Query Code

### Basic Query

```m
let
    Source = OData.Feed(
        "http://localhost:8080/odata/orders",
        null,
        [
            Headers = [Authorization = "Bearer demo_api_key"]
        ]
    )
in
    Source
```

### With Filters

```m
let
    Source = OData.Feed(
        "http://localhost:8080/odata/orders?$filter=order_date ge 2024-01-01",
        null,
        [
            Headers = [Authorization = "Bearer demo_api_key"]
        ]
    )
in
    Source
```

### Multiple Datasets

```m
// Orders
let
    Orders = OData.Feed("http://localhost:8080/odata/orders", null, [Headers = [Authorization = "Bearer demo_api_key"]])
in
    Orders

// Customers  
let
    Customers = OData.Feed("http://localhost:8080/odata/customers", null, [Headers = [Authorization = "Bearer demo_api_key"]])
in
    Customers
```

## DirectQuery vs Import Mode

### DirectQuery
- Real-time data
- No data stored in Power BI
- Slower for complex visuals
- Best for: Live dashboards

### Import Mode
- Data refreshed on schedule
- Fast visual rendering
- Data stored in Power BI
- Best for: Historical analysis

## Scheduled Refresh

### Power BI Service Setup

1. Publish report to Power BI Service
2. Go to Dataset Settings
3. Configure Gateway (if on-premises)
4. Set up refresh schedule
5. Enter credentials (API key)

### Incremental Refresh

```m
// Enable incremental refresh with date range parameters
let
    Source = OData.Feed(
        "http://localhost:8080/odata/orders?$filter=order_date ge " & Date.ToText(RangeStart, "yyyy-MM-dd") & " and order_date lt " & Date.ToText(RangeEnd, "yyyy-MM-dd"),
        null,
        [Headers = [Authorization = "Bearer demo_api_key"]]
    )
in
    Source
```

## Row-Level Security

SetuPranali automatically applies RLS based on API keys:

```yaml
# catalog.yaml
api_keys:
  north_team_key:
    tenant_id: "north"
  south_team_key:
    tenant_id: "south"

rls:
  orders:
    field: region
    operator: "="
```

In Power BI, use different API keys per user/role.

## Troubleshooting

### Cannot Connect

1. Verify SetuPranali is running
2. Check network connectivity
3. Verify API key is correct
4. Check firewall rules

### Data Not Refreshing

1. Check Gateway status
2. Verify credentials in Power BI Service
3. Check SetuPranali logs

### Performance Issues

1. Use DirectQuery for large datasets
2. Add filters to reduce data volume
3. Enable query caching in SetuPranali

## Files in This Example

```
powerbi/
├── README.md
├── SetuPranali-Template.pbit     # Power BI template
├── queries/
│   ├── orders.m                  # Power Query for orders
│   └── customers.m               # Power Query for customers
└── screenshots/
    ├── connect-odata.png
    └── sample-dashboard.png
```

## Best Practices

1. **Use Parameters** - Store API endpoint and key as parameters
2. **Enable Caching** - Set appropriate TTL in SetuPranali
3. **Use DirectQuery** - For real-time requirements
4. **Filter Early** - Add filters in OData URL, not Power Query
5. **Test Refresh** - Always test scheduled refresh before going live

