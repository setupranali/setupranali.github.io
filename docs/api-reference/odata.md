# OData API

OData endpoints for Power BI and Excel integration.

---

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/odata` | Service document (list datasets) |
| `/odata/{dataset}` | Query dataset |
| `/odata/{dataset}/$metadata` | Schema metadata |

---

## Service Document

List available datasets.

### Request

```bash
curl http://localhost:8080/odata \
  -H "X-API-Key: your-key"
```

### Response

```json
{
  "@odata.context": "$metadata",
  "value": [
    {
      "name": "sales",
      "url": "sales"
    },
    {
      "name": "customers",
      "url": "customers"
    }
  ]
}
```

---

## Query Dataset

Retrieve data from a dataset.

### Request

```bash
curl "http://localhost:8080/odata/sales" \
  -H "X-API-Key: your-key"
```

### Response

```json
{
  "@odata.context": "$metadata#sales",
  "value": [
    {
      "region": "North",
      "product": "Electronics",
      "revenue": 125000.00,
      "orders": 342
    },
    {
      "region": "South",
      "product": "Furniture",
      "revenue": 89000.00,
      "orders": 156
    }
  ]
}
```

---

## Query Options

### $select

Select specific fields:

```
/odata/sales?$select=region,revenue
```

### $filter

Filter data:

```
/odata/sales?$filter=region eq 'North'
/odata/sales?$filter=revenue gt 10000
/odata/sales?$filter=order_date ge 2024-01-01
```

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `region eq 'North'` |
| `ne` | Not equals | `status ne 'cancelled'` |
| `gt` | Greater than | `revenue gt 10000` |
| `ge` | Greater or equal | `date ge 2024-01-01` |
| `lt` | Less than | `quantity lt 100` |
| `le` | Less or equal | `date le 2024-12-31` |
| `and` | Logical AND | `region eq 'North' and revenue gt 10000` |
| `or` | Logical OR | `region eq 'North' or region eq 'South'` |

### $orderby

Sort results:

```
/odata/sales?$orderby=revenue desc
/odata/sales?$orderby=region asc,revenue desc
```

### $top

Limit rows:

```
/odata/sales?$top=100
```

### $skip

Skip rows (pagination):

```
/odata/sales?$skip=100&$top=100
```

### $count

Include count:

```
/odata/sales?$count=true
```

Response includes:

```json
{
  "@odata.count": 1523,
  "value": [...]
}
```

### Combined

```
/odata/sales?$select=region,revenue&$filter=revenue gt 10000&$orderby=revenue desc&$top=10
```

---

## Metadata

Get schema information.

### Request

```bash
curl "http://localhost:8080/odata/sales/\$metadata" \
  -H "X-API-Key: your-key"
```

### Response (XML)

```xml
<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0">
  <edmx:DataServices>
    <Schema Namespace="UBI">
      <EntityType Name="sales">
        <Property Name="region" Type="Edm.String"/>
        <Property Name="product" Type="Edm.String"/>
        <Property Name="revenue" Type="Edm.Decimal"/>
        <Property Name="orders" Type="Edm.Int64"/>
      </EntityType>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>
```

---

## Date Filtering

For incremental refresh:

### Date Range

```
/odata/sales?$filter=order_date ge 2024-01-01 and order_date lt 2024-02-01
```

### Date/Time Format

```
order_date ge 2024-01-01T00:00:00Z
```

---

## Power BI Usage

### Connection URL

```
http://localhost:8080/odata/sales
```

### Authentication

Add HTTP header:
- Name: `X-API-Key`
- Value: `your-api-key`

### Incremental Refresh

1. Create `RangeStart` and `RangeEnd` parameters
2. Filter by date column using parameters
3. Configure refresh policy in Power BI Service

---

## Error Responses

### 400 Bad Request

```json
{
  "error": {
    "code": "BadRequest",
    "message": "Invalid filter syntax"
  }
}
```

### 401 Unauthorized

```json
{
  "error": {
    "code": "Unauthorized",
    "message": "Invalid API key"
  }
}
```

### 404 Not Found

```json
{
  "error": {
    "code": "NotFound",
    "message": "Dataset 'unknown' not found"
  }
}
```

