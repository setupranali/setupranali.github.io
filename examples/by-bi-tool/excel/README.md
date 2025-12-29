# Excel Integration Examples

Connect Microsoft Excel to SetuPranali.

## Overview

Excel connects via:
- **Excel Add-in** - Native integration with query builder
- **Power Query** - For advanced transformations
- **Web Query** - Simple REST API calls

## Quick Start

### Method 1: Excel Add-in (Recommended)

1. Download the add-in from SetuPranali releases
2. In Excel: **File** → **Options** → **Add-ins**
3. Click **Manage: COM Add-ins** → **Go**
4. Click **Browse** and select the add-in
5. The SetuPranali tab appears in the ribbon

### Method 2: Power Query

1. **Data** → **Get Data** → **From Web**
2. Enter URL: `http://localhost:8080/v1/query`
3. Select **Advanced** and configure headers

## Excel Add-in Usage

### Connect to SetuPranali

1. Click **SetuPranali** tab
2. Click **Connect**
3. Enter:
   - Server: `http://localhost:8080`
   - API Key: `your_api_key`
4. Click **Test Connection**
5. Click **Save**

### Build a Query

1. Click **New Query**
2. Select **Dataset**: `orders`
3. Choose **Dimensions**: order_date, region
4. Choose **Metrics**: revenue, order_count
5. Add **Filters** (optional)
6. Click **Run Query**

Data appears in your worksheet!

### Refresh Data

- Click **Refresh** to update with latest data
- Or right-click query → **Refresh**

### Scheduled Refresh

1. Save workbook to OneDrive/SharePoint
2. Open in Excel Online
3. **Data** → **Queries & Connections**
4. Configure refresh schedule

## Power Query Examples

### Basic Query

```m
let
    url = "http://localhost:8080/v1/query",
    headers = [
        Authorization = "Bearer demo_api_key",
        #"Content-Type" = "application/json"
    ],
    body = "{
        ""dataset"": ""orders"",
        ""dimensions"": [""order_date"", ""region""],
        ""metrics"": [""revenue"", ""order_count""]
    }",
    response = Web.Contents(url, [
        Headers = headers,
        Content = Text.ToBinary(body)
    ]),
    json = Json.Document(response),
    data = json[data],
    table = Table.FromList(data, Splitter.SplitByNothing(), null, null, ExtraValues.Error)
in
    table
```

### With Parameters

Create Excel parameters for dynamic queries:

```m
let
    // Parameters (create in Power Query)
    StartDate = Excel.CurrentWorkbook(){[Name="StartDate"]}[Content]{0}[Column1],
    EndDate = Excel.CurrentWorkbook(){[Name="EndDate"]}[Content]{0}[Column1],
    
    body = "{
        ""dataset"": ""orders"",
        ""dimensions"": [""order_date""],
        ""metrics"": [""revenue""],
        ""filters"": [
            {""dimension"": ""order_date"", ""operator"": "">="", ""value"": """ & StartDate & """},
            {""dimension"": ""order_date"", ""operator"": ""<="", ""value"": """ & EndDate & """}
        ]
    }",
    
    // ... rest of query
in
    result
```

### Natural Language Query

```m
let
    url = "http://localhost:8080/v1/nlq",
    headers = [
        Authorization = "Bearer demo_api_key",
        #"Content-Type" = "application/json"
    ],
    question = Excel.CurrentWorkbook(){[Name="Question"]}[Content]{0}[Column1],
    body = "{""question"": """ & question & """}",
    response = Web.Contents(url, [
        Headers = headers,
        Content = Text.ToBinary(body)
    ]),
    json = Json.Document(response),
    data = json[data]
in
    data
```

## Excel Functions (VBA)

### Custom Function for Queries

```vba
Function SetuPranaliQuery(dataset As String, dimensions As String, metrics As String) As Variant
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")
    
    Dim url As String
    url = "http://localhost:8080/v1/query"
    
    Dim body As String
    body = "{""dataset"": """ & dataset & """, ""dimensions"": [" & dimensions & "], ""metrics"": [" & metrics & "]}"
    
    http.Open "POST", url, False
    http.setRequestHeader "Content-Type", "application/json"
    http.setRequestHeader "Authorization", "Bearer demo_api_key"
    http.send body
    
    ' Parse JSON response and return as array
    ' ... (implementation depends on JSON parser)
End Function
```

## Use Cases

### Sales Dashboard

1. Create queries for different metrics
2. Build PivotTables from query results
3. Create charts
4. Add slicers for filtering

### Automated Reports

1. Set up queries with parameters
2. Create report template
3. Schedule refresh via Power Automate
4. Email report automatically

### Data Entry + Analysis

1. Enter data in Excel
2. Upload to database via SetuPranali
3. Query aggregated results back

## Troubleshooting

### Connection Failed

1. Check SetuPranali server is running
2. Verify URL and API key
3. Check firewall allows connection

### Refresh Errors

1. Check credentials are saved
2. Verify data source is accessible
3. Check for timeout issues (increase timeout)

### Data Not Updating

1. Clear Excel cache
2. Force refresh: Ctrl+Alt+F5
3. Check query is configured correctly

## Files in This Example

```
excel/
├── README.md
├── SetuPranali-Template.xlsx
├── power-query/
│   ├── basic-query.m
│   └── parameterized-query.m
└── screenshots/
    ├── add-in-connect.png
    └── query-builder.png
```

## Best Practices

1. **Use Named Ranges** - For dynamic parameters
2. **Create Data Connections** - Reuse queries
3. **Enable Background Refresh** - Don't block Excel
4. **Cache Results** - Reduce API calls
5. **Use Tables** - Structured references work better

