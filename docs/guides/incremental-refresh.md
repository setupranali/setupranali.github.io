# Incremental Refresh

Enable efficient data loading for BI tools.

---

## Overview

Incremental refresh loads only new or changed data:

```
Full Refresh:  Load 3 years of data  →  Slow, expensive
Incremental:   Load last 7 days       →  Fast, efficient
```

Power BI native support via OData date filtering.

---

## How It Works

### Configuration

```yaml
# catalog.yaml
datasets:
  - name: orders
    source: postgres-prod
    table: orders
    
    incremental:
      date_column: order_date
      min_date: "2020-01-01"
```

### Power BI Request

Power BI sends date range parameters:

```
GET /odata/orders?$filter=order_date ge 2024-01-01 and order_date lt 2024-02-01
```

### Query Translation

```sql
SELECT ... FROM orders 
WHERE order_date >= '2024-01-01' 
  AND order_date < '2024-02-01'
```

---

## Configuration Options

### Basic Configuration

```yaml
incremental:
  date_column: order_date
```

### With Minimum Date

Prevent loading very old data:

```yaml
incremental:
  date_column: order_date
  min_date: "2020-01-01"
```

### With Granularity

Specify date granularity:

```yaml
incremental:
  date_column: order_date
  granularity: day  # day, month, year
```

---

## Power BI Setup

### Step 1: Create Parameters

In Power BI, create two parameters:

1. **RangeStart**
   - Type: Date/Time
   - Current Value: (leave empty)

2. **RangeEnd**
   - Type: Date/Time
   - Current Value: (leave empty)

### Step 2: Filter Query

In Power Query, filter by these parameters:

```m
let
    Source = OData.Feed("http://localhost:8080/odata/orders"),
    Filtered = Table.SelectRows(Source, each 
        [order_date] >= RangeStart and 
        [order_date] < RangeEnd
    )
in
    Filtered
```

### Step 3: Configure Refresh Policy

1. Right-click dataset → **Incremental refresh**
2. Configure:
   - Archive: 3 years
   - Incrementally refresh: 7 days
   - Detect data changes: (optional)

### Step 4: Publish to Service

Publish to Power BI Service. Incremental refresh only works in the service.

---

## OData Filter Syntax

### Standard Operators

| Operator | OData | Example |
|----------|-------|---------|
| Greater than or equal | `ge` | `date ge 2024-01-01` |
| Less than | `lt` | `date lt 2024-02-01` |
| Equal | `eq` | `status eq 'active'` |
| Not equal | `ne` | `status ne 'cancelled'` |
| And | `and` | `date ge 2024-01-01 and date lt 2024-02-01` |

### Date Formats

```
# ISO 8601 format
order_date ge 2024-01-01

# With time
created_at ge 2024-01-01T00:00:00Z
```

---

## Optimization

### Partition Size

| Granularity | Best For |
|-------------|----------|
| Day | High-volume transactional data |
| Month | Standard reporting |
| Year | Historical archives |

### Index the Date Column

```sql
-- Essential for incremental refresh
CREATE INDEX idx_orders_date ON orders(order_date);
```

### Composite Indexes

If using RLS + incremental:

```sql
CREATE INDEX idx_orders_tenant_date 
  ON orders(tenant_id, order_date);
```

---

## Testing

### Verify OData Filtering

```bash
# Test date range filter
curl "http://localhost:8080/odata/orders?\$filter=order_date%20ge%202024-01-01%20and%20order_date%20lt%202024-02-01" \
  -H "X-API-Key: your-api-key"
```

### Check Query Performance

```bash
# Time the request
time curl "http://localhost:8080/odata/orders?..." \
  -H "X-API-Key: your-api-key" -o /dev/null
```

### Verify Correct Rows

```bash
# Count rows in date range
curl "http://localhost:8080/odata/orders?\$filter=order_date%20ge%202024-01-01&\$count=true" \
  -H "X-API-Key: your-api-key"
```

---

## Combining with RLS

Incremental refresh works with row-level security:

```yaml
datasets:
  - name: orders
    table: orders
    
    rls:
      tenant_column: tenant_id
    
    incremental:
      date_column: order_date
```

Generated query:

```sql
SELECT ... FROM orders 
WHERE tenant_id = 'acme_corp'           -- RLS
  AND order_date >= '2024-01-01'        -- Incremental
  AND order_date < '2024-02-01'
```

---

## Troubleshooting

### Full Refresh Still Happening

**Symptoms**: Power BI loading all data

**Causes**:
- Parameters not created correctly
- Filter not using parameters
- Policy not configured

**Solutions**:
- Verify RangeStart and RangeEnd parameters exist
- Check Power Query filter references parameters
- Confirm policy is set in Power BI Service

### Date Filter Not Working

**Symptoms**: OData filter returns all rows

**Causes**:
- `incremental` not configured
- Wrong column name
- Date format mismatch

**Solutions**:
```yaml
# Verify configuration
incremental:
  date_column: order_date  # Must match actual column
```

### Slow Incremental Loads

**Symptoms**: Incremental still slow

**Causes**:
- Missing index
- Large date ranges
- Complex dataset

**Solutions**:
```sql
-- Add index
CREATE INDEX idx_orders_date ON orders(order_date);

-- Check partition size (smaller = faster)
```

---

## Best Practices

### Choose Right Date Column

| Column Type | Use For |
|-------------|---------|
| `created_at` | New records only |
| `updated_at` | Modified records |
| `event_date` | Business date |

### Set Realistic Ranges

```yaml
# Don't load ancient data
incremental:
  date_column: order_date
  min_date: "2020-01-01"  # Reasonable start
```

### Monitor Partition Size

Keep partitions manageable:

| Data Volume | Suggested Granularity |
|-------------|----------------------|
| < 1M rows/day | Day |
| 1-10M rows/day | Day with smaller range |
| > 10M rows/day | Consider pre-aggregation |

### Test in Development

Before production:

1. Test with small date ranges
2. Verify row counts match expectations
3. Time the refresh duration
4. Monitor database load

