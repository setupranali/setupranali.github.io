# Connect BI Tool

Connect your favorite BI tool to SetuPranali.

---

## Power BI (OData)

Power BI connects natively using OData—no custom connector needed.

### Step-by-Step

1. **Open Power BI Desktop**

2. **Get Data → OData Feed**

    Navigate to: **Get Data** → **More...** → **OData Feed**

3. **Enter the OData URL**

    ```
    http://localhost:8080/odata/sales
    ```

4. **Configure Authentication**

    - Select **Advanced**
    - Add HTTP header:
      - Name: `X-API-Key`
      - Value: `your-api-key`

5. **Load Data**

    Click **OK** → **Load**

### OData URL Format

```
http://your-server:8080/odata/{dataset}
```

| Dataset | OData URL |
|---------|-----------|
| `sales` | `/odata/sales` |
| `customers` | `/odata/customers` |
| `products` | `/odata/products` |

### Incremental Refresh

Power BI can use incremental refresh with date parameters:

1. **Create Parameters**
   - `RangeStart` (Date/Time)
   - `RangeEnd` (Date/Time)

2. **Configure Refresh**

    The OData endpoint supports `$filter` with date ranges:

    ```
    /odata/sales?$filter=order_date ge 2024-01-01 and order_date lt 2024-02-01
    ```

3. **Set Refresh Policy**

    Configure in Power BI Service to load only new data.

See [Incremental Refresh Guide](../guides/incremental-refresh.md) for details.

---

## Tableau (Web Data Connector)

Tableau connects using a Web Data Connector (WDC).

### Step-by-Step

1. **Open Tableau Desktop**

2. **Connect → Web Data Connector**

3. **Enter the WDC URL**

    ```
    http://localhost:8080/wdc/
    ```

4. **Configure Connection**

    - Enter your **API Key**
    - Select a **Dataset**
    - Click **Connect**

5. **Use the Data**

    Drag dimensions and metrics to your visualization.

### WDC Interface

The Web Data Connector provides a simple interface:

- **API Key**: Your authentication key
- **Server URL**: Auto-detected
- **Dataset**: Select from available datasets
- **Preview**: See sample data before loading

### Tableau Server/Online

To use on Tableau Server:

1. Allowlist the connector URL
2. Configure SSL if using HTTPS
3. Users enter their own API keys

---

## Excel (OData)

Excel supports OData connections for self-service analytics.

### Step-by-Step

1. **Open Excel**

2. **Data → Get Data → From Other Sources → From OData Feed**

3. **Enter the OData URL**

    ```
    http://localhost:8080/odata/sales
    ```

4. **Configure Authentication**

    - Select **Advanced**
    - Add HTTP header:
      - `X-API-Key`: `your-api-key`

5. **Load to Excel**

    Choose to load as Table or PivotTable.

---

## REST API (Any Tool)

Any tool that supports REST APIs can connect.

### cURL

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue"]
  }'
```

### Python

```python
import requests
import pandas as pd

response = requests.post(
    "http://localhost:8080/v1/query",
    headers={"X-API-Key": "your-api-key"},
    json={
        "dataset": "sales",
        "dimensions": ["region", "product"],
        "metrics": ["revenue", "orders"]
    }
)

data = response.json()
df = pd.DataFrame(data["rows"], columns=[c["name"] for c in data["columns"]])
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8080/v1/query', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    dataset: 'sales',
    dimensions: ['region'],
    metrics: ['revenue']
  })
});

const data = await response.json();
```

---

## Looker Studio

Connect using the REST API as a data source.

### Using Community Connector

1. Create a Google Apps Script connector
2. Use the `/v1/query` endpoint
3. Map fields to Looker Studio schema

### Direct API

1. **Add Data Source → Build Your Own**
2. Configure with REST endpoint
3. Set authentication headers

---

## Metabase

Metabase can query via REST API.

### Native Query

```sql
-- Use Metabase's HTTP action or custom driver
POST /v1/query
{
  "dataset": "sales",
  "dimensions": ["region"],
  "metrics": ["revenue"]
}
```

---

## Connection Checklist

Before connecting any BI tool:

- [ ] Connector is running and healthy
- [ ] API key is created and valid
- [ ] Dataset is defined in catalog
- [ ] Network allows connection (firewall, VPN)
- [ ] SSL configured if using HTTPS

---

## Troubleshooting

### "Connection Refused"

```
Cause: Server not running or wrong port
Fix: Verify server is running on the expected port
```

### "401 Unauthorized"

```
Cause: Invalid or missing API key
Fix: Check the X-API-Key header value
```

### "Dataset Not Found"

```
Cause: Dataset not in catalog or wrong name
Fix: Verify dataset name in catalog.yaml
```

### "No Data Returned"

```
Cause: RLS filtering out all rows
Fix: Verify API key tenant has matching data
```

---

## Next Steps

<div class="grid cards" markdown>

-   **Power BI Guide**

    ---

    Complete Power BI integration guide.

    [:octicons-arrow-right-24: Power BI](../integrations/bi-tools/powerbi.md)

-   **Tableau Guide**

    ---

    Complete Tableau integration guide.

    [:octicons-arrow-right-24: Tableau](../integrations/bi-tools/tableau.md)

-   **API Reference**

    ---

    Complete API documentation.

    [:octicons-arrow-right-24: API Reference](../api-reference/index.md)

</div>

