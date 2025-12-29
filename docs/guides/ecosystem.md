# Ecosystem Integrations

SetuPranali integrates with popular analytics tools to import and export semantic models.

## Overview

| Integration | Description | Status |
|-------------|-------------|--------|
| **dbt** | Import metrics from dbt Semantic Layer | ✅ Available |
| **Cube.js** | Interoperability with Cube schemas | ✅ Available |
| **LookML** | Import Looker/LookML models | ✅ Available |
| **Power BI Service** | Sync semantic model to Power BI | ✅ Available |
| **VS Code Extension** | Catalog editing with IntelliSense | ✅ Available |
| **Web UI** | Admin dashboard for configuration | ✅ Available |

---

## dbt Integration

Import metrics, dimensions, and models from dbt projects.

### From Local Manifest

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/dbt/import/local" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "manifest_path": "/path/to/target/manifest.json",
    "output_path": "catalog.yaml",
    "include_tags": ["production"]
  }'
```

### From dbt Cloud

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/dbt/import/cloud" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "account_id": "12345",
    "api_token": "dbtc_xxxxx",
    "job_id": 67890,
    "output_path": "catalog.yaml"
  }'
```

### CLI Usage

```bash
# Import from local manifest
setupranali dbt import --manifest ./target/manifest.json --output catalog.yaml

# Import from dbt Cloud
setupranali dbt import-cloud \
  --account-id 12345 \
  --token dbtc_xxxxx \
  --job-id 67890
```

### What Gets Imported

| dbt Artifact | SetuPranali Equivalent |
|--------------|----------------------|
| Models | Datasets |
| Columns | Dimensions |
| Metrics (MetricFlow) | Metrics + Calculated Metrics |
| Tests | Validation rules (planned) |
| Documentation | Descriptions |

### Example Conversion

**dbt model:**
```yaml
# models/orders.yml
version: 2
models:
  - name: orders
    description: Order transactions
    columns:
      - name: order_id
        description: Primary key
      - name: customer_id
        description: Customer foreign key
      - name: amount
        description: Order amount
        meta:
          is_metric: true
          aggregation: SUM
```

**Generated SetuPranali catalog:**
```yaml
datasets:
  - id: orders
    name: Orders
    description: Order transactions
    sql: SELECT * FROM analytics.orders
    dimensions:
      - name: order_id
        sql: order_id
        description: Primary key
      - name: customer_id
        sql: customer_id
        description: Customer foreign key
    metrics:
      - name: amount
        sql: SUM(amount)
        description: Order amount
```

---

## Cube.js Compatibility

Import and export Cube.js schemas for interoperability.

### Import Cube.js Schema

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/cube/import" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "schema_path": "/path/to/cube/schema",
    "output_path": "catalog.yaml"
  }'
```

### Export to Cube.js

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/cube/export" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "catalog_path": "catalog.yaml",
    "output_dir": "./cube_schema"
  }'
```

### Cube.js Meta API

SetuPranali can emulate the Cube.js Meta API for tools expecting Cube.js:

```bash
curl "http://localhost:8080/v1/ecosystem/cube/meta" \
  -H "Authorization: Bearer sk_demo_123"
```

Response:
```json
{
  "cubes": [
    {
      "name": "Orders",
      "title": "Orders",
      "measures": [
        {
          "name": "Orders.revenue",
          "title": "Revenue",
          "type": "number",
          "aggType": "sum"
        }
      ],
      "dimensions": [
        {
          "name": "Orders.region",
          "title": "Region",
          "type": "string"
        }
      ]
    }
  ]
}
```

### Mapping

| Cube.js | SetuPranali |
|---------|-------------|
| Cube | Dataset |
| Dimension | Dimension |
| Measure | Metric |
| Join | Semantic Join |
| Pre-aggregation | Cache configuration |

---

## LookML Import

Import Looker/LookML models into SetuPranali.

### Import LookML Project

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/lookml/import" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "project_path": "/path/to/lookml/project",
    "output_path": "catalog.yaml"
  }'
```

### CLI Usage

```bash
setupranali lookml import --project ./my_lookml_project --output catalog.yaml
```

### What Gets Imported

| LookML Artifact | SetuPranali Equivalent |
|-----------------|----------------------|
| View | Dataset |
| Dimension | Dimension |
| Dimension Group | Multiple time dimensions |
| Measure | Metric |
| Explore | (base view reference) |
| Join | Semantic Join |

### Example Conversion

**LookML view:**
```lookml
view: orders {
  sql_table_name: analytics.orders ;;

  dimension: order_id {
    type: number
    sql: ${TABLE}.order_id ;;
    primary_key: yes
  }

  dimension_group: created {
    type: time
    timeframes: [date, week, month, year]
    sql: ${TABLE}.created_at ;;
  }

  measure: total_revenue {
    type: sum
    sql: ${TABLE}.amount ;;
    value_format: "$#,##0"
  }
}
```

**Generated catalog:**
```yaml
datasets:
  - id: orders
    name: Orders
    sql: SELECT * FROM analytics.orders
    dimensions:
      - name: order_id
        sql: order_id
        type: number
      - name: created_date
        sql: DATE(created_at)
        type: date
      - name: created_month
        sql: DATE_TRUNC('month', created_at)
        type: date
    metrics:
      - name: total_revenue
        sql: SUM(amount)
```

---

## Power BI Service Sync

Sync your SetuPranali semantic model directly to Power BI Service.

### Configure Connection

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/powerbi/configure" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "client_id": "your-azure-app-client-id",
    "client_secret": "your-client-secret",
    "tenant_id": "your-azure-tenant-id",
    "workspace_id": "optional-workspace-id"
  }'
```

### Sync Catalog to Power BI

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/powerbi/sync" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "catalog_path": "catalog.yaml",
    "dataset_name": "SetuPranali Dataset",
    "replace_existing": true
  }'
```

### Push Data

```bash
curl -X POST "http://localhost:8080/v1/ecosystem/powerbi/push" \
  -H "Authorization: Bearer sk_demo_123" \
  -d '{
    "dataset_id": "dataset-guid",
    "table_name": "orders",
    "data": [
      {"order_id": "1", "region": "US", "revenue": 1000},
      {"order_id": "2", "region": "EU", "revenue": 2000}
    ]
  }'
```

### Azure AD Setup

1. Register an application in Azure AD
2. Grant Power BI Service permissions:
   - `Dataset.ReadWrite.All`
   - `Workspace.ReadWrite.All`
3. Create a client secret
4. Configure the app in Power BI admin portal

---

## VS Code Extension

The SetuPranali VS Code extension provides rich editing support for `catalog.yaml`.

### Features

- **IntelliSense** - Auto-completion for datasets, dimensions, metrics
- **Validation** - Real-time syntax and schema validation
- **Hover Information** - Documentation on hover
- **Go to Definition** - Navigate to definitions
- **Snippets** - Quick templates for common patterns
- **Import** - Import from dbt, LookML, Cube.js

### Installation

Search for "SetuPranali" in VS Code Extensions or:

```bash
code --install-extension setupranali.setupranali-vscode
```

### Snippets

| Prefix | Description |
|--------|-------------|
| `setu-catalog` | Complete catalog template |
| `setu-dataset` | New dataset |
| `setu-dim` | New dimension |
| `setu-metric-sum` | Sum metric |
| `setu-join` | Semantic join |

---

## Web UI

SetuPranali includes a web-based admin dashboard.

### Features

- **Dashboard** - System overview and metrics
- **Datasets** - Browse and manage semantic datasets
- **Data Sources** - Configure database connections
- **API Keys** - Manage authentication
- **Query Playground** - Test queries interactively
- **Catalog Editor** - Visual YAML editor
- **Analytics** - Query patterns and performance

### Running the Web UI

```bash
# Using Docker
docker run -p 3000:80 setupranali/webui

# Or build from source
cd webui
npm install
npm run dev
```

### Screenshots

*Dashboard showing query metrics, cache stats, and system health.*

---

## API Reference

### dbt Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/ecosystem/dbt/import/local` | Import from local manifest |
| POST | `/v1/ecosystem/dbt/import/cloud` | Import from dbt Cloud |
| GET | `/v1/ecosystem/dbt/models` | List imported models |
| GET | `/v1/ecosystem/dbt/metrics` | List imported metrics |

### Cube.js Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/ecosystem/cube/import` | Import Cube.js schema |
| POST | `/v1/ecosystem/cube/export` | Export to Cube.js |
| GET | `/v1/ecosystem/cube/meta` | Cube.js Meta API |

### LookML Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/ecosystem/lookml/import` | Import LookML project |
| GET | `/v1/ecosystem/lookml/views` | List imported views |
| GET | `/v1/ecosystem/lookml/explores` | List imported explores |

### Power BI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/ecosystem/powerbi/configure` | Configure connection |
| GET | `/v1/ecosystem/powerbi/workspaces` | List workspaces |
| GET | `/v1/ecosystem/powerbi/datasets` | List datasets |
| POST | `/v1/ecosystem/powerbi/sync` | Sync catalog |
| POST | `/v1/ecosystem/powerbi/push` | Push data |
| POST | `/v1/ecosystem/powerbi/refresh/{id}` | Trigger refresh |

