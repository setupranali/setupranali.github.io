# Integrations

Connect SetuPranali to your data sources and BI tools.

---

## Data Sources

Connect to your data warehouse or database.

<div class="grid cards" markdown>

-   :material-elephant:{ .lg .middle } **PostgreSQL**

    ---

    Connect to PostgreSQL databases.

    [:octicons-arrow-right-24: PostgreSQL](sources/postgresql.md)

-   :material-database:{ .lg .middle } **MySQL**

    ---

    Connect to MySQL and MariaDB.

    [:octicons-arrow-right-24: MySQL](sources/mysql.md)

-   :material-snowflake:{ .lg .middle } **Snowflake**

    ---

    Connect to Snowflake data warehouse.

    [:octicons-arrow-right-24: Snowflake](sources/snowflake.md)

-   :material-google-cloud:{ .lg .middle } **BigQuery**

    ---

    Connect to Google BigQuery.

    [:octicons-arrow-right-24: BigQuery](sources/bigquery.md)

-   :material-cube-outline:{ .lg .middle } **Databricks**

    ---

    Connect to Databricks SQL.

    [:octicons-arrow-right-24: Databricks](sources/databricks.md)

-   :material-cloud:{ .lg .middle } **Redshift**

    ---

    Connect to Amazon Redshift.

    [:octicons-arrow-right-24: Redshift](sources/redshift.md)

-   :material-database-search:{ .lg .middle } **ClickHouse**

    ---

    Connect to ClickHouse OLAP.

    [:octicons-arrow-right-24: ClickHouse](sources/clickhouse.md)

</div>

---

## BI Tools

Connect your visualization tools.

<div class="grid cards" markdown>

-   :material-microsoft:{ .lg .middle } **Power BI**

    ---

    Native OData integration.

    [:octicons-arrow-right-24: Power BI](bi-tools/powerbi.md)

-   :material-chart-box:{ .lg .middle } **Tableau**

    ---

    Web Data Connector.

    [:octicons-arrow-right-24: Tableau](bi-tools/tableau.md)

-   :material-api:{ .lg .middle } **REST API**

    ---

    Any tool via REST.

    [:octicons-arrow-right-24: REST API](bi-tools/rest-api.md)

</div>

---

## Modeling Layers

Integrate with existing semantic layers.

<div class="grid cards" markdown>

-   :material-source-branch:{ .lg .middle } **dbt**

    ---

    Use dbt models as datasets.

    [:octicons-arrow-right-24: dbt](modeling/dbt.md)

-   :material-view-grid:{ .lg .middle } **SQL Views**

    ---

    Use existing database views.

    [:octicons-arrow-right-24: Views](modeling/views.md)

</div>

---

## Quick Reference

### Data Source Support

| Source | Adapter | Status |
|--------|---------|--------|
| PostgreSQL | `postgres` | ✅ GA |
| MySQL | `mysql` | ✅ GA |
| Snowflake | `snowflake` | ✅ GA |
| BigQuery | `bigquery` | ✅ GA |
| Databricks | `databricks` | ✅ GA |
| Redshift | `redshift` | ✅ GA |
| ClickHouse | `clickhouse` | ✅ GA |
| DuckDB | `duckdb` | ✅ GA |

### BI Tool Protocols

| Tool | Protocol | Authentication |
|------|----------|----------------|
| Power BI | OData | X-API-Key header |
| Tableau | WDC | API Key in form |
| Excel | OData | X-API-Key header |
| Looker Studio | REST | X-API-Key header |
| Metabase | REST | X-API-Key header |

