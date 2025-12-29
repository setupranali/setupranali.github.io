# Changelog

All notable changes to SetuPranali will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Community governance files (CONTRIBUTING.md, CODE_OF_CONDUCT.md, etc.)
- GitHub issue and PR templates
- CI/CD workflows

### Changed
- Project transitioned to fully open-source community model

---

## [1.0.0] - 2024-12-24

### Added

#### Core Features
- **Semantic Query API** (`/v1/query`) — Execute analytical queries against datasets
- **Power BI OData Interface** (`/v1/odata/*`) — Native OData v4 support
- **Tableau Web Data Connector** — Client-side connector in `/wdc/`
- **Row-Level Security (RLS)** — Automatic tenant isolation based on API key
- **Query Caching** — Redis-based caching with tenant isolation
- **Incremental Refresh** — Efficient date-partitioned data loading
- **Rate Limiting** — Protect data warehouse from runaway queries

#### Data Source Adapters
- PostgreSQL adapter
- MySQL adapter
- DuckDB adapter (in-memory analytics)
- Snowflake adapter
- BigQuery adapter
- Databricks adapter
- Redshift adapter
- ClickHouse adapter

#### Security
- API key authentication with tenant context
- Encrypted credential storage (Fernet/AES)
- Role-based access control (admin/viewer)
- Credentials never exposed in API responses

#### Deployment
- Docker support with docker-compose
- Kubernetes manifests and Helm-ready
- Environment-based configuration

### Documentation
- Complete API reference
- Getting started guides
- BI tool integration guides
- Deployment documentation

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 1.0.0 | 2024-12-24 | Initial open-source release |

---

## Upgrade Guide

### Upgrading to 1.x

This is the initial release. No upgrade steps required.

---

## Links

- [GitHub Releases](https://github.com/setupranali/setupranali.github.io/releases)
- [Documentation](https://setupranali.github.io)
- [Migration Guides](https://setupranali.github.io/guides/migration)

