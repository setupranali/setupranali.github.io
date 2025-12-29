# Roadmap

This document outlines the planned features and direction for SetuPranali. 

**This is a living document** — priorities may shift based on community feedback and contributions.

---

## 🎯 Vision

**Be the simplest open-source semantic bridge for BI teams.**

While Cube.dev targets developers building analytics products and dbt Semantic Layer serves dbt-native teams, we focus on:

- **BI teams** who want security without complexity
- **Power BI and Tableau users** who need native protocols
- **Organizations** who want standalone, self-hosted solutions

### Our Design Principles

1. **Simple > Powerful** — YAML config, not a new language
2. **BI-Native** — OData and WDC are first-class, not afterthoughts
3. **Standalone** — No cloud dependencies, no ecosystem lock-in
4. **Security by Default** — RLS automatic, not optional

---

## 📊 Current Status: v1.1 (Stable)

### ✅ What's Working Today

| Feature | Status |
|---------|--------|
| Semantic Query API | ✅ Stable |
| GraphQL API | ✅ Stable |
| SQL API with RLS | ✅ Stable |
| NLQ (Natural Language Query) API | ✅ Beta |
| Schema Introspection API | ✅ Stable |
| Power BI OData Integration | ✅ Stable |
| Tableau Web Data Connector | ✅ Stable |
| Metabase Native Driver | ✅ Stable |
| Row-Level Security | ✅ Stable |
| Query Caching (Redis) | ✅ Stable |
| Incremental Refresh | ✅ Stable |
| Rate Limiting | ✅ Stable |
| Encrypted Credentials | ✅ Stable |
| Python SDK | ✅ Stable |
| JavaScript SDK | ✅ Stable |
| Jupyter Widget | ✅ Stable |

### ✅ Supported Data Sources

| Database | Status |
|----------|--------|
| PostgreSQL | ✅ Stable |
| MySQL | ✅ Stable |
| DuckDB | ✅ Stable |
| Snowflake | ✅ Stable |
| BigQuery | ✅ Stable |
| Databricks | ✅ Stable |
| Redshift | ✅ Stable |
| ClickHouse | ✅ Stable |

---

## 🚀 Short-Term (Next 3 Months)

### Priority 1: Developer Experience

| Feature | Description | Status |
|---------|-------------|--------|
| Better error messages | Clearer error responses for debugging | ✅ Completed |
| OpenAPI documentation | Interactive API docs with examples | ✅ Available at /docs |
| CLI tool | Command-line interface for management | ✅ Completed |
| Helm chart | Official Kubernetes Helm chart | ✅ Completed |

### Priority 2: New Adapters

| Database | Contributor Needed | Difficulty |
|----------|-------------------|------------|
| Trino/Presto | ✅ Completed | Medium |
| SQL Server | ✅ Completed | Medium |
| Oracle | ✅ Completed | Medium |
| SQLite | ✅ Completed | Easy |
| TimescaleDB | ✅ Completed | Easy |
| CockroachDB | ✅ Completed | Easy |

### Priority 3: BI Tool Integrations

| Tool | Description | Status |
|------|-------------|--------|
| Apache Superset | REST API integration | ✅ Completed |
| Looker Studio | Community Connector | ✅ Completed |
| Metabase | HTTP driver support | ✅ Completed |
| Grafana | Data source plugin | ✅ Completed |
| Qlik Sense | REST connector | ✅ Completed |
| Mode Analytics | REST integration | 📋 Planned |

### Priority 4: Published Connectors & SDKs

| Package | Description | Status |
|---------|-------------|--------|
| `@setupranali/looker-studio` | NPM package for Looker Studio connector | 📋 Planned |
| `setupranali-python` | Python SDK for programmatic access | ✅ Completed |
| `setupranali-js` | JavaScript/TypeScript SDK | ✅ Completed |
| Superset Database Driver | Official SQLAlchemy dialect | 📋 Planned |
| **Metabase Driver Plugin** | Official Metabase driver JAR | ✅ Completed |

---

## 🔮 Medium-Term (3-6 Months)

### Authentication & Authorization

| Feature | Description |
|---------|-------------|
| OAuth 2.0 / OIDC | Support for OAuth-based authentication |
| SSO/SAML | Enterprise identity provider integration |
| Fine-grained permissions | Column-level and dataset-level access control |

### Observability

| Feature | Description |
|---------|-------------|
| Query analytics | Dashboard for query patterns and performance |
| Prometheus metrics | Export metrics for monitoring |
| OpenTelemetry | Distributed tracing support |
| Audit logs | Full audit trail of all queries |

### API Enhancements

| Feature | Description | Status |
|---------|-------------|--------|
| GraphQL API | Alternative query interface for modern tools | ✅ Completed |
| Schema introspection API | Enhanced metadata for auto-discovery | ✅ Completed |
| SQL endpoint | Direct SQL pass-through with RLS | ✅ Completed |
| Streaming responses | Large result set streaming via SSE/WebSocket | 📋 Planned |
| Batch queries | Execute multiple queries in one request | 📋 Planned |
| JSON:API compliance | Standardized REST response format | 📋 Planned |

### BI Tool Deep Integrations

| Feature | Description | Status |
|---------|-------------|--------|
| Metabase Native Driver | Official Metabase driver plugin | ✅ Completed |
| Jupyter Widget | Interactive widget for notebooks | ✅ Completed |
| Superset Database Plugin | Native SQLAlchemy dialect `superset://` | 📋 Planned |
| Metabase Marketplace Listing | Certified driver listing | 📋 Planned |
| Looker Studio Published Connector | Listed in Google connector gallery | 📋 Planned |
| Excel Add-in | Native Excel add-in for direct queries | 📋 Planned |
| Google Sheets Connector | Apps Script add-on for Sheets | 📋 Planned |

---

## 🌟 Long-Term (6-12 Months)

### Advanced Features

| Feature | Description |
|---------|-------------|
| Semantic joins | Join across datasets in the semantic layer |
| Calculated metrics | Define metrics based on other metrics |
| Caching strategies | Smart cache invalidation, pre-warming |
| Query federation | Query across multiple data sources |

### Ecosystem

| Feature | Description |
|---------|-------------|
| dbt integration | Import metrics from dbt Semantic Layer |
| Cube.js compatibility | Interoperability with Cube schemas |
| VS Code extension | Catalog editing with IntelliSense |
| Web UI | Admin dashboard for configuration |
| LookML import | Import Looker/LookML models |
| Power BI Dataset sync | Sync semantic model to Power BI Service |

### Enterprise BI Features

| Feature | Description |
|---------|-------------|
| Tableau Hyper export | Export datasets as Hyper files |
| Power BI Push datasets | Push data directly to Power BI |
| Embedded analytics | Embed-ready endpoints with tokens |
| White-label support | Custom branding for OEM deployments |
| Multi-region deployment | Geo-distributed caching and routing |

### AI/ML Integration

| Feature | Description | Status |
|---------|-------------|--------|
| Natural language queries | Ask questions in plain English | ✅ Completed (NLQ API) |
| Auto-generated descriptions | AI-powered metric documentation | 📋 Planned |
| Anomaly detection | Automatic alerts on metric anomalies | 📋 Planned |
| Query suggestions | Smart autocomplete for dimensions/metrics | 📋 Planned |

---

## 🗳️ How to Influence the Roadmap

### 1. Vote on Features

- 👍 React to issues/discussions you want prioritized
- Most upvoted features get higher priority

### 2. Start a Discussion

- [Open a discussion](https://github.com/setupranali/setupranali.github.io/discussions/new) for new ideas
- Describe the use case and why it matters

### 3. Contribute

- Features move faster when community members contribute
- Check issues labeled `help wanted` or `good first issue`
- See [CONTRIBUTING.md](CONTRIBUTING.md)

### 4. Sponsor Development

- Sponsor specific features you need
- Contact: sponsors@setupranali.io

---

## 📝 RFC Process

For major features, we use an RFC (Request for Comments) process:

1. **Proposal** — Open a Discussion with `[RFC]` prefix
2. **Feedback** — Community discusses for 2+ weeks
3. **Decision** — Maintainers approve/modify/reject
4. **Implementation** — Work begins, tracked in Issues

---

## 🏷️ Issue Labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Great for newcomers |
| `help wanted` | Community contributions welcome |
| `priority: high` | On the near-term roadmap |
| `priority: medium` | Planned but not immediate |
| `priority: low` | Nice to have, not prioritized |
| `needs-rfc` | Requires RFC process |

---

## 📅 Release Cadence

| Release Type | Frequency | Content |
|--------------|-----------|---------|
| Patch (x.x.1) | As needed | Bug fixes, security patches |
| Minor (x.1.0) | Monthly | New features, non-breaking changes |
| Major (2.0.0) | ~Yearly | Breaking changes (with migration guide) |

---

## 🙏 Thank You

This roadmap exists because of community feedback and contributions. 

**Have ideas?** [Start a discussion](https://github.com/setupranali/setupranali.github.io/discussions/new)!

---

*Last updated: December 2024*

