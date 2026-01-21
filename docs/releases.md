# Release Notes

This page contains release notes for SetuPranali. For the complete changelog, see [CHANGELOG.md](../../CHANGELOG.md).

---

## Latest Release

### Version 1.1.0 (In Development)

**Release Date**: TBD

#### Major Features

##### Web UI Enhancements
- **Real-time Analytics Dashboard**
  - Query volume charts showing hourly trends
  - Query latency visualization
  - Recent queries with full execution details
  - System statistics and performance metrics
  - Auto-refreshes every minute

- **Contract Editor Improvements**
  - Pull from Model: Generate YAML from semantic model with correct `sourceTable` mappings
  - Push to Model: Update semantic model from edited YAML
  - Bulk export/import for all contracts
  - Pre-query validation ensures all `sourceTable` values exist in ERD
  - Clear error messages guide users to fix table mappings

- **Settings Page**
  - Dark mode toggle with persistent preference
  - Query alerts notification settings
  - Session timeout configuration
  - All settings saved to localStorage

##### State Storage
- **DuckDB Integration**
  - Persistent storage for query analytics
  - API key management with DuckDB backend
  - System metrics and historical data
  - Automatic cleanup of old records
  - Seamless fallback to in-memory storage

##### Modeling Studio
- **Enhanced ERD Builder**
  - Visual table relationship management
  - Pre-query validation for table assignments
  - Better error messages for column/table mismatches

- **Semantic Model Editor**
  - Improved source table management
  - Automatic `sourceTable` inclusion in YAML
  - Case-insensitive dimension/measure matching

#### Improvements

- **Architecture**
  - Migrated to SDLC-compliant folder structure
  - Clean Architecture principles (API, Core, Domain, Infrastructure, Shared)
  - Improved code organization and maintainability
  - Better separation of concerns

- **Docker**
  - Multi-stage build includes React webui
  - Web UI served as static files from backend
  - Optimized build process

- **Documentation**
  - Updated web UI documentation with latest features
  - Enhanced modeling studio guides
  - Comprehensive API reference updates

#### Bug Fixes

- Fixed query analytics recording for all endpoints
- Corrected timezone handling in hourly stats
- Fixed API key list refresh issues
- Resolved source table mapping in contracts
- Fixed TypeScript compilation errors
- Improved error messages for better debugging

---

## Previous Releases

### Version 1.0.0 - 2024-12-24

**Initial Open-Source Release**

#### Core Features
- Semantic Query API (`/v1/query`)
- Power BI OData Interface (`/v1/odata/*`)
- Tableau Web Data Connector
- Row-Level Security (RLS)
- Query Caching (Redis-based)
- Incremental Refresh
- Rate Limiting

#### Data Source Adapters
- PostgreSQL, MySQL, DuckDB, Snowflake, BigQuery, Databricks, Redshift, ClickHouse

#### Security
- API key authentication with tenant context
- Encrypted credential storage (Fernet/AES)
- Role-based access control (admin/viewer)

#### Deployment
- Docker support with docker-compose
- Kubernetes manifests and Helm-ready
- Environment-based configuration

---

## Upgrade Guide

### Upgrading to 1.1.0

1. **Backup your data**
   ```bash
   # Backup SQLite databases
   cp app/db/*.db app/db/*.db.backup
   ```

2. **Update Docker image**
   ```bash
   docker pull adeygifting/connector:latest
   docker-compose down
   docker-compose up -d
   ```

3. **Verify state storage migration**
   - Check that DuckDB state storage is initialized
   - Verify API keys are migrated
   - Confirm analytics data is being recorded

4. **Update semantic models**
   - Use Contract Editor to Pull from Model
   - Verify `sourceTable` is included for all fields
   - Push to Model to update with correct mappings

### Breaking Changes

None in this release. All changes are backward compatible.

---

## Links

- [GitHub Releases](https://github.com/setupranali/setupranali.github.io/releases)
- [Full Changelog](../../CHANGELOG.md)
- [Documentation](https://setupranali.github.io)
