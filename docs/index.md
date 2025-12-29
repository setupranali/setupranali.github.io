---
title: SetuPranali
description: The Bridge System for BI — Connect Power BI & Tableau securely.
---

# SetuPranali

<div class="hero" markdown>

## The Bridge System for BI

Connect Power BI and Tableau to your data warehouse in 5 minutes. 
No credential sprawl. No complex setup. No vendor lock-in.

**⚡ 5-Minute Setup** · **🔒 Automatic Security** · **📊 BI-Native Protocols**

[Get Started](getting-started/quickstart.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/setupranali/setupranali.github.io){ .md-button }

</div>

---

## The Problem

Modern data teams face a painful reality:

<div class="grid cards" markdown>

-   :material-key-chain:{ .lg .middle } __Credential Sprawl__

    ---

    Every BI user gets database credentials. Every tool has its own connection.
    Security reviews become a nightmare.

-   :material-chart-scatter-plot:{ .lg .middle } __Metric Drift__

    ---

    "Revenue" means three different things in three different dashboards.
    No single source of truth.

-   :material-lock:{ .lg .middle } __BI Lock-In__

    ---

    Your semantic model lives inside your BI tool. Switching means 
    rebuilding everything.

-   :material-speedometer:{ .lg .middle } __Performance Issues__

    ---

    Every dashboard hits the database directly. No caching.
    Slow queries. Frustrated users.

</div>

---

## The Solution

SetuPranali is a **semantic bridge** that sits between your 
data warehouse and your BI tools.

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────┐
│   Power BI   │────▶│                     │     │  Snowflake   │
├──────────────┤     │    SetuPranali      │────▶├──────────────┤
│   Tableau    │────▶│    (Bridge System)  │     │  BigQuery    │
├──────────────┤     │                     │     ├──────────────┤
│  REST API    │────▶│   - Authentication  │     │  PostgreSQL  │
└──────────────┘     │   - Authorization   │     ├──────────────┤
                     │   - Semantic Layer  │     │  Databricks  │
                     │   - Caching         │     └──────────────┘
                     └─────────────────────┘
```

---

## How It Works

<div class="grid cards" markdown>

-   :material-numeric-1-circle:{ .lg .middle } __Define Once__

    ---

    Create your semantic model with datasets, dimensions, metrics, 
    and relationships in a simple YAML catalog.

    ```yaml
    datasets:
      - name: orders
        dimensions:
          - name: region
          - name: product
        metrics:
          - name: revenue
            expr: "SUM(amount)"
    ```

-   :material-numeric-2-circle:{ .lg .middle } __Secure Centrally__

    ---

    Configure API keys with tenant context. Row-level security 
    is automatic—no database grants needed.

    ```yaml
    api_keys:
      - key: "pk_acme_..."
        tenant: acme_corp
        role: analyst
    ```

-   :material-numeric-3-circle:{ .lg .middle } __Connect Any BI__

    ---

    Power BI via OData. Tableau via Web Data Connector. 
    Any tool via REST API. Your choice.

    ```bash
    GET /odata/orders?$select=region,revenue
    Authorization: X-API-Key pk_acme_...
    ```

</div>

---

## Key Features

<div class="grid" markdown>

:material-shield-check:{ .feature-icon } **Enterprise Security**
:   API-key authentication, row-level security, tenant isolation.
    No database credentials in BI tools.

:material-sync:{ .feature-icon } **BI Agnostic**
:   Native Power BI (OData), Tableau (WDC), and REST API support.
    Switch tools without rebuilding your semantic layer.

:material-lightning-bolt:{ .feature-icon } **High Performance**
:   Intelligent caching with Redis. Query deduplication.
    Rate limiting to protect your warehouse.

:material-refresh:{ .feature-icon } **Incremental Refresh**
:   Date-partitioned loading for Power BI. Load only what's new.
    Faster refreshes, lower costs.

:material-database-multiple:{ .feature-icon } **Multi-Source**
:   Connect to Snowflake, BigQuery, Databricks, PostgreSQL, 
    MySQL, ClickHouse, Redshift—all through one API.

:material-code-tags:{ .feature-icon } **Model-Agnostic**
:   Use with dbt, existing views, or standalone.
    Your modeling layer, your rules.

</div>

---

## Supported Integrations

### Data Sources

| Database | Status | Adapter |
|----------|--------|---------|
| PostgreSQL | ✅ GA | `postgres` |
| MySQL | ✅ GA | `mysql` |
| Snowflake | ✅ GA | `snowflake` |
| BigQuery | ✅ GA | `bigquery` |
| Databricks | ✅ GA | `databricks` |
| Redshift | ✅ GA | `redshift` |
| ClickHouse | ✅ GA | `clickhouse` |
| DuckDB | ✅ GA | `duckdb` |

### BI Tools

| Tool | Protocol | Status |
|------|----------|--------|
| Power BI | OData | ✅ Native |
| Tableau | Web Data Connector | ✅ Native |
| Excel | OData | ✅ Native |
| Looker Studio | REST API | ✅ Supported |
| Metabase | REST API | ✅ Supported |
| Any REST Client | REST API | ✅ Supported |

---

## Quick Example

### 1. Start the Server

```bash
docker run -p 8080:8080 setupranali/connector:latest
```

### 2. Register a Data Source

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-warehouse",
    "type": "snowflake",
    "connection": {
      "account": "xxx.snowflakecomputing.com",
      "user": "svc_bi",
      "password": "***",
      "warehouse": "ANALYTICS_WH",
      "database": "PROD",
      "schema": "PUBLIC"
    }
  }'
```

### 3. Define a Dataset

```yaml
# catalog.yaml
datasets:
  - name: sales
    source: my-warehouse
    table: fact_sales
    dimensions:
      - name: region
        expr: region_name
      - name: product
        expr: product_category
    metrics:
      - name: revenue
        expr: "SUM(sale_amount)"
      - name: orders
        expr: "COUNT(*)"
    rls:
      tenant_column: tenant_id
```

### 4. Query via API

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: pk_tenant_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue", "orders"]
  }'
```

### 5. Connect Power BI

```
Data Source: OData
URL: http://localhost:8080/odata/sales
Header: X-API-Key = pk_tenant_abc123
```

---

## Why Not Just Use...?

### vs. Direct Database Connections

| Direct Connection | SetuPranali |
|-------------------|-------------|
| Credentials in every BI tool | API keys only—revocable, auditable |
| Build RLS per tool | RLS automatic via API key |
| No caching | Redis-based query caching |
| Metric definitions scattered | Single source of truth |

### vs. Cube.dev

| Cube.dev | SetuPranali |
|----------|-------------|
| Complex Cube schema language | Simple YAML config |
| REST API for BI tools | **Native OData + WDC** |
| Powerful but steep learning curve | Get started in 5 minutes |
| Best for API-first products | Best for BI teams |

### vs. dbt Semantic Layer

| dbt Semantic Layer | SetuPranali |
|--------------------|-------------|
| Requires dbt Cloud | Fully standalone |
| Part of larger ecosystem | Single-purpose bridge |
| MetricFlow learning curve | YAML you already know |
| Great for dbt shops | Great for everyone |

> **Bottom line:** SetuPranali is the simplest bridge from "BI tool" to "secure data access."

---

## Who Uses SetuPranali?

<div class="grid cards" markdown>

-   :material-office-building:{ .lg .middle } __Data Platform Teams__

    ---

    Centralize data access. Eliminate credential management.
    Enforce governance at scale.

-   :material-chart-bar:{ .lg .middle } __BI Engineers__

    ---

    Build once, deploy everywhere. Same metrics in every tool.
    No more copy-paste SQL.

-   :material-account-group:{ .lg .middle } __Multi-Tenant Platforms__

    ---

    Automatic tenant isolation. Self-service analytics for customers.
    No custom security code.

</div>

---

## Getting Started

Ready to bridge your BI tools?

<div class="grid cards" markdown>

-   [**Quick Start →**](getting-started/quickstart.md)

    Get up and running in 5 minutes with our tutorial.

-   [**Installation →**](getting-started/installation.md)

    Deploy with Docker, Kubernetes, or from source.

-   [**Concepts →**](concepts/index.md)

    Understand the architecture and security model.

-   [**API Reference →**](api-reference/index.md)

    Complete API documentation with examples.

</div>

---

<div class="footer-cta" markdown>

## Ready to Start?

[Get Started](getting-started/quickstart.md){ .md-button .md-button--primary }
[Join the Community](https://discord.gg/setupranali){ .md-button }

</div>
