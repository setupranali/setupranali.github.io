# Customer Onboarding Guide

Get from "account created" to "seeing data in BI" in 15 minutes.

---

## 1. Onboarding Overview

### What You Need Before Starting

| Requirement | Details |
|-------------|---------|
| **API Base URL** | Your connector endpoint (e.g., `https://api.yourcompany.com`) |
| **API Key** | Provided by your admin or generated in the platform |
| **Data Source Credentials** | Connection string for PostgreSQL or path for DuckDB |
| **BI Tool** | Power BI Desktop, Tableau Desktop, or any REST client |

### What You Will Achieve in 15 Minutes

1. ✅ Register a data source (your database)
2. ✅ Create a semantic dataset (dimensions + metrics)
3. ✅ Run your first query via API
4. ✅ Connect Power BI or Tableau to live data
5. ✅ Verify row-level security is working

### What You Do NOT Need

| You Don't Need | Why |
|----------------|-----|
| Database credentials in BI tools | Credentials stay in the connector, never exposed to BI |
| SQL knowledge for BI users | Semantic layer handles query generation |
| Agents or desktop software | Everything works via standard HTTP APIs |
| Complex configuration files | Simple REST API calls and YAML catalog |
| VPN or network changes | Works over standard HTTPS |

---

## 2. Step-by-Step Onboarding Flow

### Step 1 — Get Your API Key

**Goal:** Obtain the API key that authenticates all your requests.

**Action:**
Your API key is provisioned by your platform admin. It looks like this:

```
tenantA-key-abc123xyz
```

**Verify it works:**

```bash
curl -s https://your-api-url/v1/health \
  -H "X-API-Key: YOUR_API_KEY"
```

**Expected response:**

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

**Common Mistakes:**

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Missing header | `401 Unauthorized` | Add `-H "X-API-Key: YOUR_KEY"` |
| Wrong key | `403 Forbidden` | Check for typos, request new key |
| Key revoked | `403 Key revoked` | Contact admin for new key |

---

### Step 2 — Register Your Data Source

**Goal:** Connect the platform to your database.

**API Call:**

```bash
curl -X POST https://your-api-url/v1/sources \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "analytics_db",
    "type": "postgres",
    "config": {
      "host": "db.example.com",
      "port": 5432,
      "database": "analytics",
      "user": "readonly_user",
      "password": "secure_password"
    }
  }'
```

**For DuckDB (local file):**

```bash
curl -X POST https://your-api-url/v1/sources \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "local_duckdb",
    "type": "duckdb",
    "config": {
      "path": "/data/analytics.duckdb"
    }
  }'
```

**Expected response:**

```json
{
  "id": "src_abc123",
  "name": "analytics_db",
  "type": "postgres",
  "status": "active",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Test the connection:**

```bash
curl -X POST https://your-api-url/v1/sources/src_abc123/test \
  -H "X-API-Key: YOUR_API_KEY"
```

**Common Mistakes:**

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Wrong credentials | `Connection failed` | Verify host, port, user, password |
| Firewall blocking | `Timeout` | Allow connector IP in DB firewall |
| Invalid JSON | `422 Validation error` | Check JSON syntax, all fields present |

---

### Step 3 — Define Your Dataset (Semantic Model)

**Goal:** Create a semantic layer that maps database tables to business concepts.

Datasets are defined in `catalog.yaml`. Here's a minimal example:

```yaml
datasets:
  - id: orders
    name: Orders Analytics
    description: Order metrics by customer and region
    source: analytics_db
    table: public.orders
    
    dimensions:
      - name: customer_id
        type: string
        column: customer_id
      - name: region
        type: string
        column: region
      - name: order_date
        type: date
        column: created_at
    
    metrics:
      - name: total_revenue
        type: number
        expression: "SUM(amount)"
      - name: order_count
        type: number
        expression: "COUNT(*)"
```

**Verify dataset is loaded:**

```bash
curl -s https://your-api-url/v1/datasets \
  -H "X-API-Key: YOUR_API_KEY"
```

**Expected response:**

```json
{
  "datasets": [
    {
      "id": "orders",
      "name": "Orders Analytics",
      "dimensions": ["customer_id", "region", "order_date"],
      "metrics": ["total_revenue", "order_count"]
    }
  ]
}
```

**Common Mistakes:**

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Invalid YAML | Server won't start | Validate YAML syntax |
| Wrong source name | `Source not found` | Match `source:` to registered source name |
| Missing table | `Table does not exist` | Check schema and table name |
| Invalid SQL in expression | Query fails | Test expression directly in DB |

---

### Step 4 — Test Your First Query

**Goal:** Verify the semantic layer returns data correctly.

**API Call:**

```bash
curl -X POST https://your-api-url/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "dataset": "orders",
    "dimensions": [
      {"name": "region"}
    ],
    "metrics": [
      {"name": "total_revenue"},
      {"name": "order_count"}
    ],
    "limit": 10
  }'
```

**Expected response:**

```json
{
  "rows": [
    {"region": "North", "total_revenue": 125000.00, "order_count": 342},
    {"region": "South", "total_revenue": 98000.00, "order_count": 278},
    {"region": "East", "total_revenue": 112000.00, "order_count": 315}
  ],
  "stats": {
    "rowCount": 3,
    "executionTimeMs": 45,
    "cacheHit": false,
    "tenant": "tenantA",
    "rlsApplied": true
  }
}
```

**Add a filter:**

```bash
curl -X POST https://your-api-url/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "dataset": "orders",
    "dimensions": [{"name": "region"}],
    "metrics": [{"name": "total_revenue"}],
    "filters": {
      "field": "order_date",
      "operator": "gte",
      "value": "2025-01-01"
    },
    "limit": 10
  }'
```

**Common Mistakes:**

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Wrong dataset ID | `Dataset not found` | Check exact ID in catalog.yaml |
| Misspelled dimension | `Field not found` | Match names exactly (case-sensitive) |
| Invalid filter operator | `422 error` | Use: eq, neq, gt, gte, lt, lte, in, like |
| Empty results | `rows: []` | Check RLS — you may not have access to data |

---

### Step 5 — Connect Your BI Tool

**Goal:** See live data in Power BI or Tableau.

Choose your path:
- **Power BI** → Go to Section 3A
- **Tableau** → Go to Section 3B

---

## 3. Quickstart Paths

### 3A. Power BI Quickstart (OData)

Power BI connects via the native OData Feed connector.

**Step 1: Open Power BI Desktop**

Go to: `Get Data` → `OData Feed`

**Step 2: Enter the OData URL**

```
https://your-api-url/v1/odata/orders
```

Replace `orders` with your dataset ID.

**Step 3: Configure Authentication**

1. Click `Advanced`
2. Add HTTP header:
   - Header name: `X-API-Key`
   - Header value: `YOUR_API_KEY`

Or use Basic Authentication:
- Username: `apikey`
- Password: `YOUR_API_KEY`

**Step 4: Load Data**

Click `Load` or `Transform Data` to preview.

**What You Should See:**

| Column | Type | Description |
|--------|------|-------------|
| region | Text | Dimension from catalog |
| total_revenue | Decimal | Metric (aggregated) |
| order_count | Whole Number | Metric (aggregated) |

**Success Indicators:**
- ✅ Data loads without errors
- ✅ Columns match your dimensions + metrics
- ✅ Row count matches expected data (considering RLS)

**Incremental Refresh Setup:**

1. Go to `Transform Data` → `Manage Parameters`
2. Create `RangeStart` and `RangeEnd` parameters (DateTime)
3. Filter `order_date` between these parameters
4. In Power BI Service, configure incremental refresh policy

---

### 3B. Tableau Quickstart (Web Data Connector)

Tableau connects via the Web Data Connector (WDC).

**Step 1: Open Tableau Desktop**

Go to: `Connect` → `Web Data Connector`

**Step 2: Enter WDC URL**

```
https://your-api-url/wdc/
```

**Step 3: Configure Connection**

In the WDC interface:
1. **API Base URL:** `https://your-api-url`
2. **API Key:** `YOUR_API_KEY`
3. **Select Dataset:** Choose from dropdown

Click `Connect`.

**Step 4: Verify Schema**

Tableau will show the schema:

| Field | Type | Role |
|-------|------|------|
| region | String | Dimension |
| order_date | Date | Dimension |
| total_revenue | Float | Measure |
| order_count | Integer | Measure |

**Step 5: Load Data**

Click `Update Now` or drag fields to build viz.

**Success Indicators:**
- ✅ Schema loads correctly
- ✅ Dimensions show as blue pills
- ✅ Measures show as green pills
- ✅ Data preview shows expected rows

**Incremental Extract Setup:**

1. Create an Extract (not Live)
2. Edit Extract settings
3. Enable `Incremental Refresh`
4. Select the date column (e.g., `order_date`)
5. Tableau will only fetch new rows on refresh

---

## 4. First Success Definition

### What Counts as "Onboarded"

You are successfully onboarded when:

| Checkpoint | How to Verify |
|------------|---------------|
| ✅ API responds | `GET /v1/health` returns `200 OK` |
| ✅ Source connected | `POST /v1/sources/{id}/test` succeeds |
| ✅ Dataset accessible | `GET /v1/datasets` lists your dataset |
| ✅ Query returns data | `POST /v1/query` returns rows |
| ✅ BI tool connected | Power BI or Tableau shows data |
| ✅ RLS is working | Different API keys see different data |

### Verify Row-Level Security (RLS)

If RLS is enabled, verify it's working correctly.

**Test with Tenant A key:**

```bash
curl -X POST https://your-api-url/v1/query \
  -H "X-API-Key: tenantA-key" \
  -d '{"dataset": "orders", "metrics": [{"name": "order_count"}]}'
```

Response: `{"rows": [{"order_count": 150}]}`

**Test with Tenant B key:**

```bash
curl -X POST https://your-api-url/v1/query \
  -H "X-API-Key: tenantB-key" \
  -d '{"dataset": "orders", "metrics": [{"name": "order_count"}]}'
```

Response: `{"rows": [{"order_count": 87}]}`

**What to look for:**
- Different tenants see different row counts
- `stats.rlsApplied: true` in response
- `stats.tenant` matches your API key's tenant

---

## 5. Troubleshooting (Top 10 Issues)

### Issue 1: Invalid API Key

**Symptom:**
```json
{"detail": "Missing API key"}
```
or
```json
{"detail": "Invalid API key"}
```

**Cause:** API key missing, incorrect, or revoked.

**Fix:**
1. Verify header: `X-API-Key: YOUR_KEY` (not `Authorization`)
2. Check for extra spaces or quotes
3. Request new key from admin if revoked

---

### Issue 2: No Data Showing (Empty Results)

**Symptom:**
```json
{"rows": [], "stats": {"rowCount": 0, "rlsApplied": true}}
```

**Cause:** RLS is filtering out all rows for your tenant.

**Fix:**
1. Check `stats.tenant` — is it correct?
2. Verify data exists for your tenant in the database
3. Test with admin key (if available) to see unfiltered data
4. Check RLS column value matches your tenant ID

---

### Issue 3: Dataset Not Found

**Symptom:**
```json
{"detail": "Dataset 'ordres' not found"}
```

**Cause:** Typo in dataset ID or catalog not loaded.

**Fix:**
1. List datasets: `GET /v1/datasets`
2. Use exact ID from catalog.yaml (case-sensitive)
3. Check server logs for catalog load errors

---

### Issue 4: Power BI Authentication Error

**Symptom:**
Power BI shows "Access denied" or "Credentials required"

**Cause:** API key not passed correctly.

**Fix:**
1. Use `OData Feed` (not `OData`)
2. Click `Advanced` before connecting
3. Add header manually:
   - Name: `X-API-Key`
   - Value: `YOUR_KEY`
4. Or use Basic Auth: username=`apikey`, password=`YOUR_KEY`

---

### Issue 5: Tableau WDC Not Loading

**Symptom:**
WDC page shows blank or error

**Cause:** CORS issue or wrong URL.

**Fix:**
1. Verify WDC URL: `https://your-api-url/wdc/` (with trailing slash)
2. Check browser console for errors
3. Ensure CORS is enabled for your domain
4. Try incognito mode (cache issue)

---

### Issue 6: Field Not Found

**Symptom:**
```json
{"detail": "Field 'revenue' not found in dataset"}
```

**Cause:** Field name doesn't match catalog definition.

**Fix:**
1. Get schema: `GET /v1/datasets/orders/schema`
2. Use exact field name from schema
3. Check for `total_revenue` vs `revenue` naming

---

### Issue 7: Rate Limit Exceeded

**Symptom:**
```json
{"detail": "Rate limit exceeded", "retry_after": 42}
```
HTTP 429

**Cause:** Too many requests in short time.

**Fix:**
1. Wait for `retry_after` seconds
2. Reduce refresh frequency in BI tool
3. Enable caching to reduce redundant queries
4. Request limit increase from admin

---

### Issue 8: Query Timeout

**Symptom:**
```json
{"detail": "Query execution timeout"}
```

**Cause:** Query too complex or database slow.

**Fix:**
1. Reduce dimensions/metrics in query
2. Add filters to reduce data scanned
3. Check database performance
4. Request timeout increase if needed

---

### Issue 9: Incremental Refresh Not Working

**Symptom:**
Full data refreshed every time, not incremental.

**Cause:** Incremental not configured correctly.

**Fix (Power BI):**
1. Verify `RangeStart`/`RangeEnd` parameters exist
2. Filter must use the incremental column
3. Publish to Power BI Service (not Desktop)
4. Configure incremental policy in Service

**Fix (Tableau):**
1. Must use Extract (not Live connection)
2. Select correct date column for incremental
3. Ensure column is in the schema

---

### Issue 10: Source Connection Failed

**Symptom:**
```json
{"status": "error", "message": "Connection refused"}
```

**Cause:** Database unreachable from connector.

**Fix:**
1. Verify database host/port from connector server
2. Check firewall allows connector IP
3. Verify credentials are correct
4. Test: `psql -h HOST -p PORT -U USER -d DATABASE`

---

## 6. Onboarding Checklist (Printable)

Print this checklist and tick off each step.

```
┌─────────────────────────────────────────────────────────────┐
│                 SETUPRANALI ONBOARDING                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PREREQUISITES                                              │
│  □ I have my API Base URL: _____________________________    │
│  □ I have my API Key: __________________________________    │
│  □ I have database credentials ready                        │
│  □ BI tool installed (Power BI / Tableau)                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 1: VERIFY API ACCESS                                  │
│  □ Health check returns 200 OK                              │
│  □ API key accepted (no 401/403)                            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 2: REGISTER DATA SOURCE                               │
│  □ Source created via POST /v1/sources                      │
│  □ Source ID saved: ____________________________________    │
│  □ Connection test passed                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 3: DEFINE DATASET                                     │
│  □ catalog.yaml updated with dataset                        │
│  □ Dataset visible in GET /v1/datasets                      │
│  □ Schema looks correct                                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 4: TEST QUERY                                         │
│  □ POST /v1/query returns data                              │
│  □ Dimensions and metrics correct                           │
│  □ Filters work as expected                                 │
│  □ RLS applied (check stats.rlsApplied)                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STEP 5: CONNECT BI TOOL                                    │
│                                                             │
│  Power BI:                                                  │
│  □ OData Feed connected                                     │
│  □ API key header configured                                │
│  □ Data loads successfully                                  │
│  □ Columns match expectations                               │
│                                                             │
│  Tableau:                                                   │
│  □ WDC opened                                               │
│  □ API URL and key entered                                  │
│  □ Dataset selected                                         │
│  □ Schema imported correctly                                │
│  □ Data preview shows rows                                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  VERIFICATION                                               │
│  □ Different API keys show different data (RLS)             │
│  □ Cache working (check stats.cacheHit on 2nd query)        │
│  □ Saved report/dashboard created                           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✓ ONBOARDING COMPLETE                                      │
│                                                             │
│  Completed by: ___________________ Date: ________________   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. What's Next (Post-Onboarding)

Now that you're connected, here are recommended next steps:

### Immediate (This Week)

| Task | Why | How |
|------|-----|-----|
| **Enable Incremental Refresh** | Faster refreshes, less DB load | Add `incremental` config to dataset in catalog.yaml |
| **Configure Cache TTL** | Balance freshness vs performance | Set `CACHE_TTL_SECONDS` (default: 60) |
| **Test with real users** | Verify RLS works in production | Issue API keys for each tenant |

### Short-Term (This Month)

| Task | Why | How |
|------|-----|-----|
| **Add more datasets** | Expand analytics coverage | Add entries to catalog.yaml |
| **Connect additional sources** | Centralize data access | `POST /v1/sources` for each DB |
| **Set up monitoring** | Catch issues early | Monitor `/v1/health` and `/internal/status` |
| **Configure rate limits** | Protect infrastructure | Adjust limits per API key tier |

### Production Readiness

| Task | Why | How |
|------|-----|-----|
| **Deploy to production** | High availability | Use Docker Compose or Kubernetes |
| **Set up Redis cluster** | Cache reliability | See DEPLOYMENT.md |
| **Configure backups** | Disaster recovery | Backup sources.db and encryption key |
| **Enable audit logging** | Compliance | Review structured logs |
| **Distribute to BI users** | Scale adoption | Share OData URLs and WDC link |

### Advanced Features

| Feature | Use Case | Documentation |
|---------|----------|---------------|
| **Custom RLS rules** | Complex tenant isolation | catalog.yaml `rls` section |
| **Multiple tenants per key** | Partner access | Security configuration |
| **Incremental by ID** | Non-date based refresh | Set `type: integer` in incremental config |
| **Admin bypass** | Debugging, auditing | Use admin role API key |

---

## Quick Reference Card

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/health` | GET | Health check (no auth) |
| `/v1/datasets` | GET | List available datasets |
| `/v1/datasets/{id}/schema` | GET | Get dataset schema |
| `/v1/query` | POST | Execute semantic query |
| `/v1/odata/{dataset}` | GET | OData feed for Power BI |
| `/v1/sources` | POST | Register data source |
| `/v1/sources/{id}/test` | POST | Test source connection |

### Headers

```http
X-API-Key: YOUR_API_KEY
Content-Type: application/json
```

### OData URL Pattern

```
https://your-api-url/v1/odata/{datasetId}?$select=dim1,metric1&$top=100
```

### WDC URL

```
https://your-api-url/wdc/
```

---

## Support

| Resource | Link |
|----------|------|
| API Documentation | `https://your-api-url/docs` |
| OpenAPI Spec | `https://your-api-url/openapi.json` |
| Deployment Guide | `DEPLOYMENT.md` |
| Production Checklist | `PRODUCTION_READINESS.md` |

---

*You're in control. The semantic layer handles the complexity — you focus on insights.*

