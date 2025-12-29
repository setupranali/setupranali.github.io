# Microsoft SQL Server

Connect SetuPranali to Microsoft SQL Server, Azure SQL Database, and Azure Synapse Analytics.

---

## Overview

**Microsoft SQL Server** is ideal for:

- Enterprise Windows environments
- Azure SQL Database and Azure Synapse
- Power BI integration (native)
- Existing Microsoft data warehouses

!!! info "Azure SQL Support"
    SetuPranali automatically detects Azure SQL connections and configures encryption.

---

## Prerequisites

Install the SQL Server Python driver:

```bash
# Recommended (simpler, no ODBC config)
pip install pymssql

# Alternative (requires ODBC driver)
pip install pyodbc
```

### ODBC Driver (for pyodbc)

If using `pyodbc`, install the ODBC driver:

=== "Windows"

    Download from [Microsoft](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

=== "macOS"

    ```bash
    brew install microsoft/mssql-release/msodbcsql18
    ```

=== "Ubuntu/Debian"

    ```bash
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
    curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list
    apt-get update
    ACCEPT_EULA=Y apt-get install -y msodbcsql18
    ```

---

## Configuration

### Register via API

```bash
curl -X POST http://localhost:8080/v1/sources \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-sqlserver",
    "type": "sqlserver",
    "connection": {
      "host": "sqlserver.company.com",
      "port": 1433,
      "database": "analytics",
      "user": "bi_user",
      "password": "secret"
    }
  }'
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `host` | ✅ | - | Server hostname or IP |
| `port` | | `1433` | Server port |
| `database` | ✅ | - | Database name |
| `user` | ✅* | - | Username (not needed for Windows auth) |
| `password` | ✅* | - | Password (not needed for Windows auth) |
| `trusted_connection` | | `false` | Use Windows Authentication |
| `encrypt` | | Auto | Encrypt connection |
| `trust_server_certificate` | | `false` | Trust self-signed certificates |
| `connection_timeout` | | `30` | Connection timeout (seconds) |
| `query_timeout` | | `0` | Query timeout (0 = no limit) |
| `application_name` | | `SetuPranali` | App name in SQL Server logs |
| `read_only` | | `true` | Connect with read-only intent |
| `azure` | | Auto | Azure SQL mode |
| `use_pyodbc` | | `false` | Force pyodbc driver |
| `driver` | | Auto | ODBC driver name |

---

## Examples

### On-Premises SQL Server

```json
{
  "name": "sql-analytics",
  "type": "sqlserver",
  "connection": {
    "host": "sqlserver.company.com",
    "port": 1433,
    "database": "analytics",
    "user": "bi_user",
    "password": "secure_password"
  }
}
```

### Azure SQL Database

```json
{
  "name": "azure-analytics",
  "type": "azuresql",
  "connection": {
    "host": "myserver.database.windows.net",
    "database": "analytics",
    "user": "bi_user@myserver",
    "password": "secure_password",
    "azure": true
  }
}
```

### Windows Authentication

```json
{
  "name": "sql-windows",
  "type": "sqlserver",
  "connection": {
    "host": "sqlserver.company.com",
    "database": "analytics",
    "trusted_connection": true
  }
}
```

### Read Replica (AlwaysOn)

```json
{
  "name": "sql-replica",
  "type": "sqlserver",
  "connection": {
    "host": "sqlserver-listener.company.com",
    "database": "analytics",
    "user": "bi_user",
    "password": "secure_password",
    "read_only": true
  }
}
```

### With SSL Encryption

```json
{
  "name": "sql-encrypted",
  "type": "sqlserver",
  "connection": {
    "host": "sqlserver.company.com",
    "database": "analytics",
    "user": "bi_user",
    "password": "secure_password",
    "encrypt": true,
    "trust_server_certificate": false
  }
}
```

---

## Dataset Configuration

### catalog.yaml Example

```yaml
datasets:
  - id: sales
    name: Sales Analytics
    description: Sales data from SQL Server
    source: my-sqlserver
    table: dbo.fact_sales
    dimensions:
      - name: region
        expr: region_name
      - name: product
        expr: product_category
      - name: date
        expr: sale_date
        type: date
    metrics:
      - name: revenue
        expr: "SUM(amount)"
      - name: orders
        expr: "COUNT(*)"
      - name: avg_order_value
        expr: "AVG(amount)"
    rls:
      mode: tenant_column
      field: tenant_id
```

### Using Schema Prefix

```yaml
datasets:
  - id: customers
    source: my-sqlserver
    table: analytics.dim_customers  # schema.table format
    dimensions:
      - name: customer_id
      - name: name
      - name: segment
```

---

## Azure SQL Specific

### Azure Active Directory

For AAD authentication, use the `pyodbc` driver with the appropriate connection string:

```json
{
  "name": "azure-aad",
  "type": "sqlserver",
  "connection": {
    "host": "myserver.database.windows.net",
    "database": "analytics",
    "user": "user@domain.com",
    "password": "password",
    "azure": true,
    "use_pyodbc": true,
    "driver": "ODBC Driver 18 for SQL Server"
  }
}
```

### Azure Synapse Analytics

```json
{
  "name": "synapse",
  "type": "sqlserver",
  "connection": {
    "host": "mysynapse.sql.azuresynapse.net",
    "port": 1433,
    "database": "sqlpool",
    "user": "sqladmin",
    "password": "secure_password",
    "azure": true
  }
}
```

---

## Performance Tips

### 1. Use Read-Only Intent

For analytics workloads, use read-only connections:

```json
{
  "read_only": true
}
```

This routes queries to read replicas in AlwaysOn configurations.

### 2. Enable Query Caching

```yaml
# values.yaml (Helm)
config:
  cache:
    enabled: true
    ttl: 300
```

### 3. Use Appropriate Indexes

Ensure your tables have indexes on:
- Dimension columns used in GROUP BY
- Tenant columns for RLS
- Date columns for incremental refresh

### 4. Connection Pooling

The adapter maintains connections efficiently. For high-load scenarios:

```json
{
  "connection_timeout": 60,
  "query_timeout": 120
}
```

---

## Troubleshooting

### Connection Refused

```
ConnectionError: Failed to connect to SQL Server
```

**Solutions:**
1. Verify SQL Server is running and accessible
2. Check firewall allows port 1433
3. For Azure, ensure firewall rule includes your IP
4. Verify SQL Server Browser service is running

### Login Failed

```
Login failed for user 'bi_user'
```

**Solutions:**
1. Verify username and password
2. Check user has access to the database
3. For Azure, use `user@server` format
4. Verify SQL Server authentication is enabled

### SSL/Encryption Errors

```
SSL Provider: error:1416F086
```

**Solutions:**
1. Set `trust_server_certificate: true` for self-signed certs
2. Update ODBC driver to version 17+
3. For Azure, ensure `encrypt: true`

### Timeout Errors

```
Query timeout expired
```

**Solutions:**
1. Increase `query_timeout` setting
2. Add filters to reduce data volume
3. Check query execution plan
4. Verify network latency

### ODBC Driver Not Found

```
Can't open lib 'ODBC Driver 17 for SQL Server'
```

**Solutions:**
1. Install ODBC driver (see Prerequisites)
2. Use `pymssql` instead: `use_pyodbc: false`
3. Specify driver name: `driver: "SQL Server Native Client 11.0"`

---

## Security

### Row-Level Security

SetuPranali automatically applies RLS:

```yaml
datasets:
  - id: sales
    rls:
      mode: tenant_column
      field: tenant_id
```

### Minimal Permissions

Grant only necessary permissions:

```sql
-- Create a read-only user
CREATE LOGIN bi_user WITH PASSWORD = 'secure_password';
CREATE USER bi_user FOR LOGIN bi_user;

-- Grant read access to specific tables
GRANT SELECT ON schema_name.table_name TO bi_user;

-- Or grant db_datareader role
ALTER ROLE db_datareader ADD MEMBER bi_user;
```

### Encrypted Connections

For production, always use encryption:

```json
{
  "encrypt": true,
  "trust_server_certificate": false
}
```

---

## CLI Usage

```bash
# Add SQL Server source
setupranali sources add \
  --name my-sqlserver \
  --type sqlserver \
  --config '{"host":"sqlserver.example.com","database":"analytics","user":"bi_user","password":"secret"}'

# Test connection
setupranali sources test my-sqlserver

# Query
setupranali query sales -d region -m revenue
```

---

## API Examples

### Query via REST

```bash
curl -X POST http://localhost:8080/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales",
    "dimensions": ["region"],
    "metrics": ["revenue", "orders"],
    "limit": 100
  }'
```

### SQL with RLS

```bash
curl -X POST http://localhost:8080/v1/sql \
  -H "X-API-Key: tenant-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT region, SUM(amount) as revenue FROM dbo.fact_sales GROUP BY region",
    "dataset": "sales"
  }'
```

