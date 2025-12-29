# SetuPranali Examples

Welcome to the examples directory! Find ready-to-use configurations for your specific data source and BI tool combination.

## 📁 Directory Structure

```
examples/
├── by-source/           # Examples organized by data source
│   ├── postgresql/
│   ├── mysql/
│   ├── snowflake/
│   ├── bigquery/
│   └── ...
├── by-bi-tool/          # Examples organized by BI tool
│   ├── powerbi/
│   ├── tableau/
│   ├── metabase/
│   └── ...
├── use-cases/           # Real-world scenarios
│   ├── e-commerce/
│   ├── saas-metrics/
│   ├── financial/
│   └── ...
└── quick-start/         # Minimal examples to get started
```

## 🚀 Quick Start

### 1. Choose Your Data Source

| Source | Difficulty | Example |
|--------|------------|---------|
| [PostgreSQL](by-source/postgresql/) | Easy | Most common, great for starting |
| [MySQL](by-source/mysql/) | Easy | Popular alternative |
| [SQLite](by-source/sqlite/) | Easiest | No setup required |
| [DuckDB](by-source/duckdb/) | Easy | In-memory analytics |
| [Snowflake](by-source/snowflake/) | Medium | Cloud data warehouse |
| [BigQuery](by-source/bigquery/) | Medium | Google Cloud |
| [Databricks](by-source/databricks/) | Medium | Lakehouse platform |
| [Redshift](by-source/redshift/) | Medium | AWS data warehouse |
| [ClickHouse](by-source/clickhouse/) | Medium | Real-time analytics |
| [SQL Server](by-source/sqlserver/) | Medium | Microsoft SQL |
| [Oracle](by-source/oracle/) | Medium | Enterprise database |
| [TimescaleDB](by-source/timescaledb/) | Easy | Time-series data |
| [CockroachDB](by-source/cockroachdb/) | Easy | Distributed SQL |
| [Trino](by-source/trino/) | Advanced | Query federation |

### 2. Choose Your BI Tool

| BI Tool | Integration Type | Example |
|---------|-----------------|---------|
| [Power BI](by-bi-tool/powerbi/) | OData (Native) | Best for Microsoft shops |
| [Tableau](by-bi-tool/tableau/) | WDC (Native) | Visual analytics |
| [Metabase](by-bi-tool/metabase/) | Native Driver | Open-source BI |
| [Apache Superset](by-bi-tool/superset/) | SQLAlchemy | Modern data exploration |
| [Looker Studio](by-bi-tool/looker-studio/) | Community Connector | Google ecosystem |
| [Grafana](by-bi-tool/grafana/) | Data Source Plugin | Monitoring dashboards |
| [Qlik Sense](by-bi-tool/qlik/) | REST Connector | Enterprise BI |
| [Mode Analytics](by-bi-tool/mode/) | Python/REST | Collaborative analytics |
| [Excel](by-bi-tool/excel/) | Add-in | Spreadsheet users |
| [Google Sheets](by-bi-tool/google-sheets/) | Apps Script | Cloud spreadsheets |
| [Jupyter](by-bi-tool/jupyter/) | Widget/SDK | Data science |

### 3. Or Pick a Use Case

| Use Case | Description |
|----------|-------------|
| [E-Commerce](use-cases/e-commerce/) | Orders, customers, products |
| [SaaS Metrics](use-cases/saas-metrics/) | MRR, churn, LTV |
| [Financial](use-cases/financial/) | Revenue, expenses, P&L |
| [IoT/Sensor](use-cases/iot/) | Time-series sensor data |
| [Marketing](use-cases/marketing/) | Campaigns, conversions |
| [HR Analytics](use-cases/hr/) | Employee metrics |

## 🎯 Finding the Right Example

### By Experience Level

**Beginners:**
1. Start with [quick-start/minimal/](quick-start/minimal/)
2. Try [SQLite + REST API](by-source/sqlite/)
3. Progress to [PostgreSQL + Power BI](by-source/postgresql/)

**Intermediate:**
1. [Snowflake + Tableau](by-source/snowflake/)
2. [BigQuery + Superset](by-source/bigquery/)
3. [Multi-source federation](use-cases/multi-source/)

**Advanced:**
1. [Enterprise setup](use-cases/enterprise/)
2. [Multi-tenant SaaS](use-cases/multi-tenant/)
3. [Embedded analytics](use-cases/embedded/)

## 📋 What Each Example Includes

Every example contains:

```
example-name/
├── README.md           # Step-by-step instructions
├── catalog.yaml        # SetuPranali configuration
├── docker-compose.yml  # One-command setup
├── sample-data/        # Demo data (if applicable)
├── queries/            # Example queries
└── screenshots/        # Visual results
```

## 🏃 Running an Example

```bash
# 1. Navigate to example
cd examples/by-source/postgresql

# 2. Start with Docker Compose
docker-compose up -d

# 3. Test the connection
curl http://localhost:8080/v1/health

# 4. Run a sample query
curl -X POST http://localhost:8080/v1/query \
  -H "Authorization: Bearer demo_key" \
  -H "Content-Type: application/json" \
  -d @queries/sample.json
```

## 🔗 Quick Links

- [Documentation](https://setupranali.github.io)
- [GitHub](https://github.com/setupranali/setupranali.github.io)
- [Discord](https://discord.gg/setupranali)
- [Report Issues](https://github.com/setupranali/setupranali.github.io/issues)

## 🤝 Contributing Examples

We welcome community examples! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

```bash
# Create a new example
cp -r templates/example-template examples/by-source/my-database
# Edit and submit a PR
```
