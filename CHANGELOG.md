# Changelog

All notable changes to SetuPranali will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Web UI Enhancements**
  - Real-time analytics dashboard with query volume and latency charts
  - Contract Editor with Pull/Push to Model functionality
  - Automatic `sourceTable` mapping in YAML contracts
  - Pre-query validation for table assignments
  - Settings page with dark mode and preferences
  - Bulk export/import for contracts
- **State Storage**
  - DuckDB-based persistent state storage for analytics, API keys, and system metrics
  - Automatic migration from in-memory to persistent storage
  - Query analytics retention and cleanup
- **Modeling Studio Improvements**
  - Enhanced ERD builder with table validation
  - Improved semantic model editor with source table management
  - Better error messages for column/table mismatches
  - YAML contract export/import with sourceTable preservation
- **SDLC Compliance**
  - Standardized folder structure following Clean Architecture principles
  - Separated concerns: API, Core, Domain, Infrastructure, Shared layers
  - Improved code organization and maintainability
- Community governance files (CONTRIBUTING.md, CODE_OF_CONDUCT.md, etc.)
- GitHub issue and PR templates
- CI/CD workflows with webui build support

### Changed
- **Architecture**
  - Migrated to SDLC-compliant folder structure
  - Separated domain logic from infrastructure concerns
  - Improved import paths and module organization
- **Web UI**
  - Contract Editor now uses backend API for YAML generation
  - Dashboard shows real-time analytics from DuckDB storage
  - All settings persisted to localStorage
- **Docker**
  - Multi-stage build includes React webui
  - Web UI served as static files from backend
  - Reduced image size with optimized build process
- Project transitioned to fully open-source community model

### Fixed
- **Query Analytics**
  - Fixed query recording for all endpoints (semantic, SQL, source queries)
  - Corrected timezone handling in hourly stats
  - Fixed merge logic for DuckDB and in-memory stats
  - Ensured all 24 hours are populated in query volume charts
- **Contract Editor**
  - Fixed missing `sourceTable` in YAML generation
  - Corrected field extraction (removes aggregation wrappers)
  - Added validation for source table existence in ERD
  - Improved error messages for incorrect table mappings
- **API Keys**
  - Fixed API key list not refreshing after creation/deletion
  - Ensured keys are saved to both DuckDB and in-memory registry
  - Fixed authentication in frontend API client
- **Source Management**
  - Fixed adapter imports after folder structure migration
  - Improved error handling for decryption failures
  - Consistent `UBI_SECRET_KEY` loading from `.env` file
- **TypeScript**
  - Fixed all compilation errors for Docker build
  - Added proper type definitions for Vite environment variables

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

