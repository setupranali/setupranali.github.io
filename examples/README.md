# Integration Examples

This folder contains examples of integrating SetuPranali with existing data infrastructure.

## Examples Overview

| Folder | Use Case | Description |
|--------|----------|-------------|
| `dbt/` | dbt models | Connect to dbt-transformed tables |
| `looker/` | Looker | Expose Looker derived tables via API |
| `cube/` | Cube.js | Add RLS layer on top of Cube |
| `warehouse-views/` | SQL Views | Use existing warehouse views |
| `multi-source/` | Multiple DBs | Combine data from multiple sources |

## Key Principle

The connector is a **thin security + connectivity layer** on top of your existing models.

```
Your Modeling Layer (dbt/Looker/Cube)
        ↓
    [Your Tables/Views]
        ↓
SetuPranali (API Keys, RLS, Caching)
        ↓
    BI Tools (Power BI, Tableau)
```

## Quick Start

1. Copy the relevant `catalog.yaml` from an example folder
2. Update connection details in `.env`
3. Register your data source via API
4. Connect your BI tool

## Performance Note

For TB-scale data, the connector passes queries to your existing database engine:
- Snowflake, BigQuery, Databricks → Handle TB+ natively
- The connector adds ~5-10ms overhead for auth/RLS injection
- Redis caching eliminates repeated queries entirely

